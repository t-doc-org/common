# Copyright 2024 Caroline Blank <caro@c-space.org>
# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import argparse
import contextlib
from http import server
import pathlib
import socket
import subprocess

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

    p = subparsers.add_parser('serve', add_help=False,
                              help="Serve a book locally.")
    p.set_defaults(handler=cmd_serve)
    arg = p.add_argument_group("Options").add_argument
    arg('--bind', metavar='ADDRESS', dest='bind', default='localhost',
        help="The address to bind the server to (default: all interfaces).")
    arg('--clean', action='store_true', dest='clean', default=False,
        help="Do a clean build before serving.")
    arg('--help', action='help', help="Show this help message and exit.")
    arg('--port', metavar='PORT', dest='port', default=8000, type=int,
        help="The port to bind the server to (default: %(default)s).")
    arg('--protocol', metavar='VERSION', dest='protocol', default='HTTP/1.0',
        help="The HTTP protocol version to conform to (default: %(default)s).")

    cfg = parser.parse_args(argv[1:])
    cfg.stdin, cfg.stdout, cfg.stderr = stdin, stdout, stderr
    cfg.ansi = util.ansi if cfg.color else util.no_ansi
    return cfg.handler(cfg)


def cmd_build(cfg):
    for target in cfg.target:
        sphinx_build(cfg, target)


def sphinx_build(cfg, target):
    argv = [cfg.sphinx_build, '-M', target, cfg.source, cfg.build,
            '--jobs=auto', '--fail-on-warning']
    if cfg.debug: argv += ['--show-traceback']
    argv += cfg.sphinx_opts
    subprocess.run(argv, stdin=cfg.stdin, stdout=cfg.stdout, stderr=cfg.stderr,
                   check=True)


def cmd_serve(cfg):
    # Build the book.
    if cfg.clean: sphinx_build(cfg, 'clean')
    sphinx_build(cfg, 'html')

    # Start a server to serve the resulting HTML.
    for family, _, _, _, addr in socket.getaddrinfo(
            cfg.bind if cfg.bind != 'ALL' else None, cfg.port,
            type=socket.SOCK_STREAM, flags=socket.AI_PASSIVE):
        break

    class Server(ServerBase):
        address_family = family
    class Handler(HandlerBase):
        protocol = cfg.protocol
        config = cfg

    directory = pathlib.Path(cfg.build) / 'html'
    with Server(addr, Handler, directory=directory) as srv:
        host, port = srv.socket.getsockname()[:2]
        if ':' in host: host = f'[{host}]'
        print(cfg.ansi("Serving on <@{LBLUE}%s@{NORM}>")
              % f"http://{host}:{port}/",
              file=cfg.stdout)
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            print("Interrupted, exiting", file=cfg.stdout)
            return


class ServerBase(server.ThreadingHTTPServer):

    def __init__(self, *args, directory, **kwargs):
        self.directory = directory
        super().__init__(*args, **kwargs)

    def server_bind(self):
        with contextlib.suppress(Exception):
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        return super().server_bind()

    def finish_request(self, request, client_addr):
        self.RequestHandlerClass(request, client_addr, self,
                                 directory=self.directory)


class HandlerBase(server.SimpleHTTPRequestHandler):

    def log_request(self, code='-', size='-'):
        pass

    def log_message(self, format, *args):
        self.config.stderr.write("%s - - [%s] %s\n" % (
            self.address_string(), self.log_date_time_string(),
            (format % args).translate(self._control_char_table)))


if __name__ == '__main__':
    main()
