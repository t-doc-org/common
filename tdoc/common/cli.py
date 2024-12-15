# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import argparse
import contextlib
from http import HTTPMethod, HTTPStatus
import itertools
from importlib import metadata
import json
import mimetypes
import os
import pathlib
import posixpath
import re
import shutil
import socket
import socketserver
import stat
import subprocess
import sys
import threading
import time
from urllib import parse
from wsgiref import simple_server, util as wsgiutil

from . import __project__, __version__, store, util, wsgi

# TODO: Implement incremental builds, by copying previous build output


@util.main
def main(argv, stdin, stdout, stderr):
    """Run the command."""
    parser = util.get_arg_parser(stderr)(
        prog=pathlib.Path(argv[0]).name, add_help=False,
        description="Manage a t-doc book.")
    root = parser.add_subparsers(title='Subcommands', dest='subcommand')
    root.required = True

    arg = parser.add_argument_group("Options").add_argument
    arg('--build', metavar='PATH', dest='build', default='_build',
        help="The path to the build directory (default: %(default)s).")
    arg('--color', dest='color', choices=['auto', 'false', 'true'],
        default='auto',
        help="Control the use of colors in output (default: %(default)s).")
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

    p = root.add_parser('build', add_help=False, help="Build a book.")
    p.set_defaults(handler=cmd_build)
    arg = p.add_argument_group("Options").add_argument
    arg('--help', action='help', help="Show this help message and exit.")
    arg('target', metavar='TARGET', nargs='+', help="The build targets to run.")

    p = root.add_parser('clean', add_help=False,
                        help="Clean the build products of a book.")
    p.set_defaults(handler=cmd_clean)
    arg = p.add_argument_group("Options").add_argument
    arg('--help', action='help', help="Show this help message and exit.")

    p = root.add_parser('serve', add_help=False, help="Serve a book locally.")
    p.set_defaults(handler=cmd_serve)
    arg = p.add_argument_group("Options").add_argument
    arg('--bind', metavar='ADDRESS', dest='bind', default='localhost',
        help="The address to bind the server to (default: %(default)s). "
             "Specify ALL to bind to all interfaces.")
    arg('--delay', metavar='DURATION', dest='delay', default=1, type=float,
        help="The delay in seconds between detecting a source change and "
             "triggering a build (default: %(default)s).")
    arg('--help', action='help', help="Show this help message and exit.")
    arg('--ignore', metavar='REGEXP', dest='ignore',
        default=f'(^|{re.escape(os.sep)})__pycache__$',
        help="A regexp matching files and directories to ignore from watching "
             "(default: %(default)s).")
    arg('--interval', metavar='DURATION', dest='interval', default=1,
        type=float,
        help="The interval in seconds at which to check for source changes "
             "(default: %(default)s).")
    arg('--port', metavar='PORT', dest='port', default=8000, type=int,
        help="The port to bind the server to (default: %(default)s).")
    arg('--restart-on-change', action='store_true', dest='restart_on_change',
        help="Restart the server on changes.")
    arg('--store', metavar='PATH', dest='store', default='',
        help="The path to the store database.")
    arg('--watch', metavar='PATH', action='append', dest='watch', default=[],
        help="Additional directories to watch for changes.")

    p = root.add_parser('store', help="Store-related commands.")
    store = p.add_subparsers()
    store.required = True

    p = store.add_parser('create', add_help=False,
                         help="Create the store database.")
    p.set_defaults(handler=cmd_store_create)
    arg = p.add_argument_group("Options").add_argument
    arg('--store', metavar='PATH', dest='store', default='tmp/store.sqlite',
        help="The path to the store database.")

    p = root.add_parser('version', add_help=False,
                        help="Display version information.")
    p.set_defaults(handler=cmd_version)

    cfg = parser.parse_args(argv[1:])
    cfg.stdin, cfg.stdout, cfg.stderr = stdin, stdout, stderr
    cfg.ansi = (util.ansi if cfg.color == 'true' or
                             (cfg.color == 'auto' and util.want_colors(stdout))
                          else util.no_ansi)
    cfg.build = pathlib.Path(cfg.build).absolute()
    cfg.source = pathlib.Path(cfg.source).absolute()
    if hasattr(cfg, 'ignore'): cfg.ignore = re.compile(cfg.ignore)
    return cfg.handler(cfg)


def cmd_build(cfg):
    for target in cfg.target:
        res = sphinx_build(cfg, target, build=cfg.build)
        if res.returncode != 0: return res.returncode


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

    with Application(cfg, addr) as app, Server(addr, RequestHandler) as srv:
        app.server = srv
        srv.set_app(app)
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            cfg.restart_on_change = False
            cfg.stderr.write("Interrupted, exiting\n")

    if cfg.restart_on_change:
        cfg.stdout.flush()
        cfg.stderr.flush()
        os.execv(sys.argv[0], sys.argv)


def cmd_store_create(cfg):
    store.Store(cfg.store).create()


def cmd_version(cfg):
    cfg.stdout.write(f"{__project__}-{__version__}\n")


def sphinx_build(cfg, target, *, build, tags=(), **kwargs):
    argv = [cfg.sphinx_build, '-M', target, cfg.source, build,
            '--fail-on-warning', '--jobs=auto']
    argv += [f'--tag={tag}' for tag in tags]
    if cfg.debug: argv += ['--show-traceback']
    argv += cfg.sphinx_opts
    return subprocess.run(argv, stdin=cfg.stdin, stdout=cfg.stdout,
                          stderr=cfg.stderr, **kwargs)


class ServerBase(socketserver.ThreadingMixIn, simple_server.WSGIServer):
    daemon_threads = True

    def server_bind(self):
        with contextlib.suppress(Exception):
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        return super().server_bind()


class RequestHandler(simple_server.WSGIRequestHandler):
    def log_request(self, code='-', size='-'):
        pass

    def log_message(self, format, *args):
        self.server.application.cfg.stderr.write("%s - - [%s] %s\n" % (
            self.address_string(), self.log_date_time_string(),
            (format % args).translate(self._control_char_table)))


def try_stat(path):
    try:
        return path.stat()
    except OSError:
        return None


class Application:
    def __init__(self, cfg, addr):
        self.cfg = cfg
        self.addr = addr
        self.lock = threading.Condition(threading.Lock())
        self.directory = self.build_dir(0) / 'html'
        self.upgrade_msg = None
        self.stop = False
        self.min_mtime = time.time_ns()
        self.build_mtime = None
        self.building = False
        self.builder = threading.Thread(target=self.watch_and_build)
        self.builder.start()
        self.checker = threading.Thread(target=self.check_upgrade, daemon=True)
        self.checker.start()
        self.apps = {'*build': self.handle_build}
        if cfg.store:
            st = store.Store(cfg.store)
            if not st.path.exists():
                st.path.parent.mkdir(parents=True, exist_ok=True)
                st.create(open_acl=True)
            self.apps['*store'] = st

    def __enter__(self): return self

    def __exit__(self, typ, value, tb):
        with self.lock: self.stop = True
        self.builder.join()

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
                if self.cfg.restart_on_change:
                    self.cfg.stdout.write(
                        "\nSource change detected, restarting\n")
                    self.server.shutdown()
                    break
                self.cfg.stdout.write(
                    "\nSource change detected, rebuilding\n")
            prev_mtime = mtime
            if build := self.build(mtime):
                with self.lock:
                    self.build_mtime = mtime
                    self.directory = build / 'html'
                    self.lock.notify_all()
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
        mtime = self.min_mtime
        for path in itertools.chain([self.cfg.source], self.cfg.watch):
            for base, dirs, files in path.walk(on_error=on_error):
                for file in files:
                    p = base / file
                    if self.cfg.ignore.search(str(p)) is not None: continue
                    try:
                        st = p.stat()
                        if stat.S_ISREG(st.st_mode):
                            mtime = max(mtime, st.st_mtime_ns)
                    except Exception as e:
                        on_error(e)
                dirs[:] = [d for d in dirs
                           if self.cfg.ignore.search(str(base / d)) is None]
        return mtime

    def build_dir(self, mtime):
        return self.cfg.build / f'serve-{mtime}'

    def build(self, mtime):
        build = self.build_dir(mtime)
        with self.lock: self.building = True
        try:
            res = sphinx_build(self.cfg, 'html', build=build,
                               tags=['tdoc-dev', build_tag(mtime)])
            if res.returncode == 0: return build
        except Exception as e:
            self.cfg.stderr.write(f"Build: {e}\n")
        finally:
            with self.lock: self.building = False

    def remove_build_dir(self, mtime):
        build = self.build_dir(mtime)
        build.relative_to(self.cfg.build)  # Ensure we're below the build dir
        def on_error(fn, path, e):
            self.cfg.stderr.write(f"Removal: {fn}: {path}: {e}\n")
        shutil.rmtree(build, onexc=on_error)

    def print_serving(self):
        host, port = self.addr[:2]
        if ':' in host: host = f'[{host}]'
        self.cfg.stdout.write(self.cfg.ansi("Serving at <@{LBLUE}%s@{NORM}>\n")
                              % f"http://{host}:{port}/")
        with self.lock: msg = self.upgrade_msg
        if msg: self.cfg.stdout.write(msg)

    def check_upgrade(self):
        try:
            upgrades, editable = pip_check_upgrades(self.cfg, __project__)
            if __project__ not in upgrades: return
            msg = self.cfg.ansi(
                "@{LYELLOW}A t-doc upgrade is available:@{NORM} "
                "%s @{CYAN}%s@{NORM} => @{CYAN}%s@{NORM}\n"
                "See <@{LBLUE}https://t-doc.org/common/%s#upgrade@{NORM}>\n"
                % (__project__, metadata.version(__project__),
                    upgrades[__project__],
                   'development' if editable else 'install'))
            with self.lock:
                self.upgrade_msg = msg
                if not self.building: self.cfg.stdout.write(msg)
        except Exception:
            if self.cfg.debug: raise

    def __call__(self, env, respond):
        script_name, path_info = env['SCRIPT_NAME'], env['PATH_INFO']
        name = wsgiutil.shift_path_info(env)
        if (handler := self.apps.get(name)) is not None:
            return handler(env, respond)
        env['SCRIPT_NAME'], env['PATH_INFO'] = script_name, path_info
        return self.handle_default(env, respond)

    def handle_default(self, env, respond):
        env['wsgi.multithread'] = True
        if (method := env['REQUEST_METHOD']) not in (HTTPMethod.HEAD,
                                                     HTTPMethod.GET):
            return wsgi.error(respond, HTTPStatus.NOT_IMPLEMENTED)
        path = self.file_path(env['PATH_INFO'])
        if (st := try_stat(path)) is None:
            return wsgi.error(respond, HTTPStatus.NOT_FOUND)

        if stat.S_ISDIR(st.st_mode):
            parts = parse.urlsplit(env['PATH_INFO'])
            if not parts.path.endswith('/'):
                location = parse.urlunsplit(
                    (parts[:2] + (parts[2] + '/',) + parts[3:]))
                respond(wsgi.http_status(HTTPStatus.MOVED_PERMANENTLY), [
                    ('Location', location),
                    ('Content-Length', '0'),
                ])
                return []
            path = path / 'index.html'
            if (st := try_stat(path)) is None:
                return wsgi.error(respond, HTTPStatus.NOT_FOUND)

        if not stat.S_ISREG(st.st_mode):
            return wsgi.error(respond, HTTPStatus.NOT_FOUND)
        mime_type = mimetypes.guess_type(path)[0]
        if not mime_type: mime_type = 'application/octet-stream'
        respond(wsgi.http_status(HTTPStatus.OK), [
            ('Content-Type', mime_type),
            ('Content-Length', str(st.st_size)),
        ])
        if method == HTTPMethod.HEAD: return []
        wrapper = env.get('wsgi.file_wrapper', wsgiutil.FileWrapper)
        return wrapper(open(path, 'rb'))

    def file_path(self, path):
        trailing = path.rstrip().endswith('/')
        try:
            path = parse.unquote(path, errors='surrogatepass')
        except UnicodeDecodeError:
            path = parse.unquote(path)
        with self.lock: res = self.directory
        for part in filter(None, posixpath.normpath(path).split('/')):
            if pathlib.Path(part).parent.name or part in (os.curdir, os.pardir):
                continue
            res = res / part
        return res / '' if trailing else res

    def handle_build(self, env, respond):
        if (method := env['REQUEST_METHOD']) not in (HTTPMethod.HEAD,
                                                     HTTPMethod.GET):
            yield from wsgi.error(respond, HTTPStatus.NOT_IMPLEMENTED)
        t = None
        for k, v in parse.parse_qsl(env.get('QUERY_STRING', '')):
            if k == 't':
                t = v
                break
        # We send padding back at regular intervals, which allows detecting when
        # the client closes the connection (we get a BrokenPipeError). Since the
        # content length is needed upfront, we return a fixed size, and
        # terminate the request if the padding exceeds the available space.
        size = 600
        respond(wsgi.http_status(HTTPStatus.OK), [
            ('Content-Type', 'text/plain; charset=utf-8'),
            ('Content-Length', str(size)),
        ])
        if method == HTTPMethod.HEAD: return
        with self.lock:
            while ((mtime := self.build_mtime) is None
                   or t == build_tag(mtime)) and size > 0:
                if self.lock.wait(timeout=1): continue
                yield b' '
                size -= 1
        tag = build_tag(mtime).encode('utf-8')
        if len(tag) > size: tag = b''  # Not enough remaining capacity
        yield b' ' * (size - len(tag)) + tag


def build_tag(mtime):
    return f'tdoc_build_{mtime}'


class Namespace(dict):
    def __getattr__(self, name):
        return self[name]


def pip(cfg, *args, json_output=False):
    p = subprocess.run((sys.executable, '-m', 'pip') + args,
        stdin=subprocess.DEVNULL, capture_output=True, text=True)
    if p.returncode != 0: raise Exception(p.stderr)
    if not json_output: return p.stdout
    return json.loads(p.stdout, object_pairs_hook=Namespace)


def pip_check_upgrades(cfg, package):
    data = pip(cfg, 'install', '--dry-run', '--upgrade',
               '--upgrade-strategy=only-if-needed', '--only-binary=:all:',
               '--report=-', '--quiet', package, json_output=True)
    upgrades = {pkg.metadata.name: pkg.metadata.version for pkg in data.install}
    if package not in upgrades: return {}, False
    pkgs = pip(cfg, 'list', '--editable', '--format=json', json_output=True)
    editable = any(pkg.name == package for pkg in pkgs)
    return upgrades, editable


if __name__ == '__main__':
    main()
