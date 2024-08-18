# Copyright 2024 Caroline Blank <caro@c-space.org>
# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import argparse
import contextlib
from http import server
import itertools
import pathlib
import shutil
import socket
import stat
import subprocess
import threading
import time

from . import util


@util.main
def main(argv, stdin, stdout, stderr):
    """Run the command."""
    parser = util.get_arg_parser(stderr)(
        prog=pathlib.Path(argv[0]).name, add_help=False,
        description="Manage a t-doc book.")
    subparsers = parser.add_subparsers(title='Subcommands', dest='subcommand')
    subparsers.required = True

    arg = parser.add_argument_group("Options").add_argument
    arg('--build', metavar='PATH', dest='build', default='_build',
        help="The path to the build directory (default: %(default)s).")
    arg('--color', action='store_true', dest='color',
        default=util.want_colors(stdout),
        help="Use colors in output (default: %(default)s).")
    arg('--no-color', action='store_false', dest='color',
        help="Don't use colors in output (default: %(default)s).")
    arg('--debug', action='store_true', dest='debug',
        help="Enable debug functionality.")
    arg('--help', action='help', help="Show this help message and exit.")
    arg('--source', metavar='PATH', dest='source', default='docs',
        help="The path to the source files (default: %(default)s).")
    arg('--sphinx-build', metavar='PATH', dest='sphinx_build',
        default='sphinx-build',
        help="The path to the sphinx-build binary (default: %(default)s.")
    arg('--sphinx-opt', metavar='OPT', action='append', dest='sphinx_opts',
        default=[], help="Additional options to pass to sphinx-build.")

    p = subparsers.add_parser('build', add_help=False,
                              help="Build a book.")
    p.set_defaults(handler=cmd_build)
    arg = p.add_argument_group("Options").add_argument
    arg('--help', action='help', help="Show this help message and exit.")
    arg('target', metavar='TARGET', nargs='+', help="The build targets to run.")

    p = subparsers.add_parser('clean', add_help=False,
                              help="Clean the build products of a book.")
    p.set_defaults(handler=cmd_clean)
    arg = p.add_argument_group("Options").add_argument
    arg('--help', action='help', help="Show this help message and exit.")

    p = subparsers.add_parser('serve', add_help=False,
                              help="Serve a book locally.")
    p.set_defaults(handler=cmd_serve)
    arg = p.add_argument_group("Options").add_argument
    arg('--bind', metavar='ADDRESS', dest='bind', default='localhost',
        help="The address to bind the server to (default: %(default)s). "
             "Specify ALL to bind to all interfaces.")
    arg('--delay', metavar='DURATION', dest='delay', default=1,
        type=float,
        help="The delay in seconds between detecting a source change and "
             "triggering a build (default: %(default)s).")
    arg('--help', action='help', help="Show this help message and exit.")
    arg('--interval', metavar='DURATION', dest='interval', default=1,
        type=float,
        help="The interval in seconds at which to check for source changes "
             "(default: %(default)s).")
    arg('--port', metavar='PORT', dest='port', default=8000, type=int,
        help="The port to bind the server to (default: %(default)s).")
    arg('--protocol', metavar='VERSION', dest='protocol', default='HTTP/1.0',
        help="The HTTP protocol version to conform to (default: %(default)s).")
    arg('--watch', metavar='PATH', action='append', dest='watch', default=[],
        help="Additional directories to watch for changes.")

    cfg = parser.parse_args(argv[1:])
    cfg.stdin, cfg.stdout, cfg.stderr = stdin, stdout, stderr
    cfg.ansi = util.ansi if cfg.color else util.no_ansi
    cfg.build = pathlib.Path(cfg.build).absolute()
    cfg.source = pathlib.Path(cfg.source).absolute()
    return cfg.handler(cfg)


def cmd_build(cfg):
    for target in cfg.target:
        res = sphinx_build(cfg, target, build=cfg.build)
        if res.returncode != 0: return res.returncode


def sphinx_build(cfg, target, *, build, **kwargs):
    argv = [cfg.sphinx_build, '-M', target, cfg.source, build,
            '--jobs=auto', '--fail-on-warning']
    if cfg.debug: argv += ['--show-traceback']
    argv += cfg.sphinx_opts
    return subprocess.run(argv, stdin=cfg.stdin, stdout=cfg.stdout,
                          stderr=cfg.stderr, **kwargs)


def cmd_clean(cfg):
    return sphinx_build(cfg, 'clean', build=cfg.build).returncode


def cmd_serve(cfg):
    for i, p in enumerate(cfg.watch):
        cfg.watch[i] = pathlib.Path(p).absolute()

    for family, _, _, _, addr in socket.getaddrinfo(
            cfg.bind if cfg.bind != 'ALL' else None, cfg.port,
            type=socket.SOCK_STREAM, flags=socket.AI_PASSIVE):
        break

    class Server(ServerBase):
        address_family = family
    class Handler(HandlerBase):
        protocol = cfg.protocol

    with Server(addr, Handler, cfg=cfg) as srv:
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            cfg.stderr.write("Interrupted, exiting\n")


class ServerBase(server.ThreadingHTTPServer):

    def __init__(self, *args, cfg, **kwargs):
        self.cfg = cfg
        self.lock = threading.Lock()
        self.directory = self.cfg.build / 'html'
        self.stop = False
        self.builder = threading.Thread(target=self.watch_and_build)
        self.builder.start()
        super().__init__(*args, **kwargs)

    def server_bind(self):
        with contextlib.suppress(Exception):
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        return super().server_bind()

    def finish_request(self, request, client_addr):
        with self.lock:
            directory = self.directory
        self.RequestHandlerClass(request, client_addr, self,
                                 directory=directory)

    def server_close(self):
        with self.lock:
            self.stop = True
        self.builder.join()
        return super().server_close()

    def watch_and_build(self):
        interval = self.cfg.interval * 1_000_000_000
        delay = self.cfg.delay * 1_000_000_000
        prev, prev_mtime, build_mtime = 0, 0, None
        while True:
            if prev != 0: time.sleep(0.1)
            with self.lock:
                if self.stop: break
            now = time.time_ns()
            if now < prev + interval: continue
            mtime = self.latest_mtime()
            if mtime <= prev_mtime:
                prev = now
                continue
            if now < mtime + delay:
                prev = mtime + delay - interval
                continue
            if prev_mtime != 0:
                self.cfg.stdout.write(
                    "\nSource change detected, rebuilding\n")
            prev_mtime = mtime
            if build := self.build(mtime):
                with self.lock:
                    self.directory = build / 'html'
                self.print_serving()
                if build_mtime is not None: self.remove_build_dir(build_mtime)
                build_mtime = mtime
            else:
                self.remove_build_dir(mtime)
            prev = time.time_ns()
        if build_mtime is not None: self.remove_build_dir(build_mtime)

    def latest_mtime(self):
        def on_error(e):
            self.cfg.stderr.write(f"Scan: {e}\n")
        mtime = 0
        for path in itertools.chain([self.cfg.source], self.cfg.watch):
            for base, dirs, files in path.walk(on_error=on_error):
                for file in files:
                    try:
                        st = (base / file).stat()
                        if stat.S_ISREG(st.st_mode):
                            mtime = max(mtime, st.st_mtime_ns)
                    except Exception as e:
                        on_error(e)
        return mtime

    def build_dir(self, mtime):
        return self.cfg.build / f'serve-{mtime}'

    def build(self, mtime):
        build = self.build_dir(mtime)
        try:
            res = sphinx_build(self.cfg, 'html', build=build)
            if res.returncode == 0: return build
        except Exception as e:
            self.cfg.stderr.write(f"Build: {e}\n")

    def remove_build_dir(self, mtime):
        build = self.build_dir(mtime)
        build.relative_to(self.cfg.build)  # Ensure we're below the build dir
        def on_error(fn, path, e):
            self.cfg.stderr.write(f"Removal: {fn}: {path}: {e}\n")
        shutil.rmtree(build, onexc=on_error)

    def print_serving(self):
        host, port = self.socket.getsockname()[:2]
        if ':' in host: host = f'[{host}]'
        self.cfg.stdout.write(self.cfg.ansi("Serving at <@{LBLUE}%s@{NORM}>\n")
                              % f"http://{host}:{port}/")


class HandlerBase(server.SimpleHTTPRequestHandler):

    def log_request(self, code='-', size='-'):
        pass

    def log_message(self, format, *args):
        self.server.cfg.stderr.write("%s - - [%s] %s\n" % (
            self.address_string(), self.log_date_time_string(),
            (format % args).translate(self._control_char_table)))


if __name__ == '__main__':
    main()
