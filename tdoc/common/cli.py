# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import argparse
import contextlib
import datetime
from http import HTTPMethod, HTTPStatus
import itertools
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
import webbrowser
from wsgiref import simple_server, util as wsgiutil

from . import __project__, __version__, api, store, util, wsgi

# TODO: Split groups of sub-commands into separate modules
# TODO: Implement incremental builds, by copying previous build output


@util.main
def main(argv, stdin, stdout, stderr):
    """Run the command."""
    parser = util.get_arg_parser(stdin, stdout, stderr)(
        prog=pathlib.Path(argv[0]).name, description="Manage a t-doc book.")
    root = parser.add_subparsers(title='Sub-commands')
    root.required = True

    p = root.add_parser('build', help="Build a book.")
    p.set_defaults(handler=cmd_build)
    arg = p.add_argument
    arg('target', metavar='TARGET', nargs='+', help="The build targets to run.")
    add_options(p, sphinx=True)

    p = root.add_parser('clean', help="Clean the build products of a book.")
    p.set_defaults(handler=cmd_clean)
    add_options(p, sphinx=True)

    add_group_commands(root)

    p = root.add_parser('serve', help="Serve a book locally.")
    p.set_defaults(handler=cmd_serve)
    arg = p.add_argument
    arg('--bind', metavar='ADDRESS', dest='bind', default='localhost',
        help="The address to bind the server to (default: %(default)s). "
             "Specify ALL to bind to all interfaces.")
    arg('--delay', metavar='DURATION', type=float, dest='delay', default=1.0,
        help="The delay in seconds between detecting a source change and "
             "triggering a build (default: %(default)s).")
    arg('--exit-on-failure', action='store_true', dest='exit_on_failure',
        help="Terminate the server on build failure.")
    arg('--exit-on-idle', metavar='DURATION', type=float, dest='exit_on_idle',
        default=0.0,
        help="The time in seconds after the last connection closes when the "
             "server terminates (default: %(default)s).")
    arg('--ignore', metavar='REGEXP', type='regexp', dest='ignore',
        default=f'(^|{re.escape(os.sep)})__pycache__$',
        help="A regexp matching files and directories to ignore from watching "
             "(default: %(default)s).")
    arg('--interval', metavar='DURATION', type=float, dest='interval',
        default=1.0,
        help="The interval in seconds at which to check for source changes "
             "(default: %(default)s).")
    arg('--open', action='store_true', dest='open',
        help="Open the site in a browser tab after the first build completes.")
    arg('--port', metavar='PORT', type=int, dest='port', default=8000,
        help="The port to bind the server to (default: %(default)s).")
    arg('--restart-on-change', action='store_true', dest='restart_on_change',
        help="Restart the server on changes.")
    add_store_option(arg)
    arg('--watch', metavar='PATH', type='path', action='append', dest='watch',
        default=[],
        help="Additional directories to watch for changes.")
    add_options(p, sphinx=True)

    add_store_commands(root)
    add_token_commands(root)
    add_user_commands(root)

    p = root.add_parser('version', help="Display version information.")
    p.set_defaults(handler=cmd_version)
    add_options(p)

    cfg = parser.parse_args(argv[1:])
    return cfg.handler(cfg)


def add_options(parser, sphinx=False):
    if sphinx: add_sphinx_options(parser)
    arg = parser.add_argument_group("Common options").add_argument
    arg('--color', dest='color', choices=['auto', 'false', 'true'],
        default='auto',
        help="Control the use of colors in output (default: %(default)s).")
    arg('--debug', action='store_true', dest='debug',
        help="Enable debug functionality.")


def add_sphinx_options(parser):
    arg = parser.add_argument_group("Sphinx options").add_argument
    arg('--build', metavar='PATH', type='path', dest='build', default='_build',
        help="The path to the build directory (default: %(default)s).")
    arg('--source', metavar='PATH', type='path', dest='source', default='docs',
        help="The path to the source files (default: %(default)s).")
    arg('--sphinx-opt', metavar='OPT', action='append', dest='sphinx_opts',
        default=[], help="Additional options to pass to sphinx-build.")


def comma_separated(s):
    if s is None: return []
    return s.split(',')


def cmd_build(cfg):
    for target in cfg.target:
        res = sphinx_build(cfg, target, build=cfg.build)
        if res.returncode != 0: return res.returncode


def cmd_clean(cfg):
    return sphinx_build(cfg, 'clean', build=cfg.build).returncode


def add_group_commands(parser):
    p = parser.add_parser('group', help="Group-related commands.")
    sp = p.add_subparsers(title="Sub-commands")
    sp.required = True

    def add_groups(arg):
        for name in ('group', 'groups'):
            arg(f'--{name}', metavar="GROUP,...", dest='groups',
                help="A comma-separated list of groups.")

    def add_users(arg):
        for name in ('user', 'users'):
            arg(f'--{name}', metavar="USER,...", dest='users',
                help="A comma-separated list of users.")

    def add_groups_re(arg):
        arg('groups', metavar='REGEXP', nargs='?', default='',
            help="A regexp to limit the groups to consider.")

    p = sp.add_parser('add', help="Add members to one or more groups.")
    p.set_defaults(handler=cmd_group_add)
    arg = p.add_argument
    add_groups(arg)
    add_origin_option(arg)
    add_store_option(arg)
    add_users(arg)
    arg('group', metavar='GROUP', nargs='+', help="The group to add to.")
    add_options(p)

    p = sp.add_parser('list', help="List groups.")
    p.set_defaults(handler=cmd_group_list)
    arg = p.add_argument
    add_store_option(arg)
    add_groups_re(arg)
    add_options(p)

    p = sp.add_parser('members', help="List members of a group.")
    p.set_defaults(handler=cmd_group_members)
    arg = p.add_argument
    add_origin_option(arg)
    add_store_option(arg)
    arg('--transitive', action='store_true', dest='transitive',
        help="Include transitive memberships.")
    add_groups_re(arg)
    add_options(p)

    p = sp.add_parser('memberships', help="List group memberships for a group.")
    p.set_defaults(handler=cmd_group_memberships)
    arg = p.add_argument
    add_origin_option(arg)
    add_store_option(arg)
    add_groups_re(arg)
    add_options(p)

    p = sp.add_parser('remove', help="Remove members from one or more groups.")
    p.set_defaults(handler=cmd_group_remove)
    arg = p.add_argument
    add_groups(arg)
    add_origin_option(arg)
    add_store_option(arg)
    add_users(arg)
    arg('group', metavar='GROUP', nargs='+', help="The group to remove from.")
    add_options(p)


def cmd_group_add(cfg):
    store = get_store(cfg)
    with contextlib.closing(store.connect()) as db, db:
        store.modify_groups(db, cfg.origin, cfg.group,
                            add_users=comma_separated(cfg.users),
                            add_groups=comma_separated(cfg.groups))


def cmd_group_list(cfg):
    store = get_store(cfg)
    with contextlib.closing(store.connect()) as db, db:
        groups = store.groups(db, cfg.groups)
    groups.sort()
    o = cfg.stdout
    for group in groups: cfg.stdout.write(f"{o.CYAN}{group}{o.NORM}\n")


def cmd_group_members(cfg):
    store = get_store(cfg)
    with contextlib.closing(store.connect()) as db, db:
        members = store.group_members(db, cfg.origin, cfg.groups,
                                      transitive=cfg.transitive)
    members.sort()
    wgroup = max((len(m[0]) for m in members), default=0)
    wname = max((len(m[2]) for m in members), default=0)
    o = cfg.stdout
    prev = None
    for group, typ, name, transitive in members:
        prefix = f"{o.CYAN}{group:{wgroup}}{o.NORM}" if group != prev \
                 else f"{'':{wgroup}}"
        if transitive:
            cfg.stdout.write(
                f"{prefix}  {typ:5} {o.LWHITE}{name:{wname}}{o.NORM}  "
                "(transitive)\n")
        else:
            cfg.stdout.write(f"{prefix}  {typ:5} {o.LWHITE}{name}{o.NORM}\n")
        prev = group


def cmd_group_memberships(cfg):
    store = get_store(cfg)
    with contextlib.closing(store.connect()) as db, db:
        memberships = store.group_memberships(db, cfg.origin, cfg.groups)
    memberships.sort()
    wmember = max((len(m[0]) for m in memberships), default=0)
    o = cfg.stdout
    prev = None
    for member, group in memberships:
        prefix = f"{o.CYAN}{member:{wmember}}{o.NORM}" if member != prev \
                 else f"{'':{wmember}}"
        cfg.stdout.write(f"{prefix}  {o.LWHITE}{group}{o.NORM}\n")
        prev = member


def cmd_group_remove(cfg):
    store = get_store(cfg)
    with contextlib.closing(store.connect()) as db, db:
        store.modify_groups(db, cfg.origin, cfg.group,
                            remove_users=comma_separated(cfg.users),
                            remove_groups=comma_separated(cfg.groups))


def cmd_serve(cfg):
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
    return app.returncode


def add_store_commands(parser):
    p = parser.add_parser('store', help="Store-related commands.")
    sp = p.add_subparsers(title="Sub-commands")
    sp.required = True

    p = sp.add_parser('create', help="Create the store database.")
    p.set_defaults(handler=cmd_store_create)
    arg = p.add_argument
    arg('--dev', action='store_true', dest='dev',
        help="Create the store for dev mode.")
    add_store_option(arg)
    arg('--version', metavar='VERSION', type=int, dest='version', default=None,
        help="The version at which to create the store (default: latest).")
    add_options(p)

    p = sp.add_parser('upgrade', help="Upgrade the store database.")
    p.set_defaults(handler=cmd_store_upgrade)
    arg = p.add_argument
    add_store_option(arg)
    arg('--version', metavar='VERSION', type=int, dest='version', default=None,
        help="The version to which to upgrade the store (default: latest).")
    add_options(p)


def add_store_option(arg):
    arg('--store', metavar='PATH', type='path', dest='store',
        default=os.environ.get('TDOC_STORE', 'tmp/store.sqlite'),
        help="The path to the store database (default: %(default)s).")


def get_store(cfg):
    if not cfg.store: raise Exception("--store: Empty path")
    return store.Store(cfg.store)


def cmd_store_create(cfg):
    store = get_store(cfg)
    store.path.parent.mkdir(parents=True, exist_ok=True)
    version = store.create(version=cfg.version, dev=cfg.dev)
    cfg.stdout.write(f"Store created (version: {version})\n")


def cmd_store_upgrade(cfg):
    store = get_store(cfg)
    from_version, to_version = store.upgrade(version=cfg.version)
    if from_version != to_version:
        cfg.stdout.write(
            f"Store upgraded (version: {from_version} => {to_version})\n")
    else:
        cfg.stdout.write(f"Store already up-to-date (version: {to_version})\n")


def add_token_commands(parser):
    p = parser.add_parser('token', help="Token-related commands.")
    sp = p.add_subparsers(title="Sub-commands")
    sp.required = True

    p = sp.add_parser('create', help="Create tokens.")
    p.set_defaults(handler=cmd_token_create)
    arg = p.add_argument
    arg('--expire', metavar='TIME', type='timestamp', dest='expire',
        help="The token expiry timestamp.")
    add_origin_option(arg)
    add_store_option(arg)
    arg('user', metavar='USER', nargs='+',
        help="The users for whom to create tokens.")
    add_options(p)

    p = sp.add_parser('expire', help="Expire tokens.")
    p.set_defaults(handler=cmd_token_expire)
    arg = p.add_argument
    arg('--time', metavar='TIME', type='timestamp', dest='time',
        help="The time when the tokens should expire (default: now).")
    add_store_option(arg)
    arg('token', metavar='TOKEN', nargs='+',
        help="The users and / or tokens to expire.")
    add_options(p)

    p = sp.add_parser('list', help="List tokens.")
    p.set_defaults(handler=cmd_token_list)
    arg = p.add_argument
    arg('--expired', action='store_true', dest='expired',
        help="Include expired tokens.")
    add_origin_option(arg)
    add_store_option(arg)
    arg('users', metavar='REGEXP', nargs='?', default='',
        help="A regexp to limit the users to consider.")
    add_options(p)


def add_origin_option(arg):
    arg('--origin', metavar='URL', dest='origin', default='',
        help="The origin on which to operate.")


def cmd_token_create(cfg):
    store = get_store(cfg)
    with contextlib.closing(store.connect()) as db, db:
        tokens = store.create_tokens(db, cfg.user, cfg.expire)
    width = max((len(u) for u in cfg.user), default=0)
    o = cfg.stdout
    for user, token in zip(cfg.user, tokens):
        cfg.stdout.write(
            f"{o.CYAN}{user:{width}}{o.NORM} "
            f"{o.LBLUE}{cfg.origin}#?login={token}{o.NORM}\n")


def cmd_token_expire(cfg):
    store = get_store(cfg)
    with contextlib.closing(store.connect()) as db, db:
        store.expire_tokens(db, cfg.token, cfg.time)


def cmd_token_list(cfg):
    store = get_store(cfg)
    with contextlib.closing(store.connect()) as db, db:
        tokens = store.tokens(db, cfg.users, expired=cfg.expired)
    epoch = datetime.datetime.fromtimestamp(0)
    tokens.sort(key=lambda r: (r[0], r[3], r[4] or epoch, r[2]))
    wuser = max((len(u) for u, *_ in tokens), default=0)
    o = cfg.stdout
    for user, uid, token, created, expires in tokens:
        if expires: expires = f", expires: {expires.isoformat(' ', 'seconds')}"
        cfg.stdout.write(
            f"{o.CYAN}{user:{wuser}}{o.NORM} "
            f"{o.LBLUE}{cfg.origin}#?login={token}{o.NORM}\n"
            f"  created: {created.isoformat(' ', 'seconds')}{expires or ""}\n")


def add_user_commands(parser):
    p = parser.add_parser('user', help="User-related commands.")
    sp = p.add_subparsers(title="Sub-commands")
    sp.required = True

    def add_users_re(arg):
        arg('users', metavar='REGEXP', nargs='?', default='',
            help="A regexp to limit the users to consider.")

    p = sp.add_parser('create', help="Create users.")
    p.set_defaults(handler=cmd_user_create)
    arg = p.add_argument
    add_origin_option(arg)
    add_store_option(arg)
    arg('--token-expire', metavar='TIME', type='timestamp', dest='token_expire',
        help="The expiry time of the users' token.")
    arg('user', metavar='USER', nargs='+',
        help="The names of the users to create.")
    add_options(p)

    p = sp.add_parser('list', help="List users.")
    p.set_defaults(handler=cmd_user_list)
    arg = p.add_argument
    add_store_option(arg)
    add_users_re(arg)
    add_options(p)

    p = sp.add_parser('memberships', help="List group memberships for a user.")
    p.set_defaults(handler=cmd_user_memberships)
    arg = p.add_argument
    add_origin_option(arg)
    add_store_option(arg)
    arg('--transitive', action='store_true', dest='transitive',
        help="Include transitive memberships.")
    add_users_re(arg)
    add_options(p)


def cmd_user_create(cfg):
    store = get_store(cfg)
    with contextlib.closing(store.connect()) as db, db:
        uids = store.create_users(db, cfg.user)
        tokens = store.create_tokens(db, cfg.user, cfg.token_expire)
    wuser = max((len(u) for u in cfg.user), default=0)
    o = cfg.stdout
    for user, uid, token in zip(cfg.user, uids, tokens):
        cfg.stdout.write(f"{o.CYAN}{user:{wuser}}{o.NORM} ({uid:016x})  "
                         f"{o.LBLUE}{cfg.origin}#?login={token}{o.NORM}\n")


def cmd_user_list(cfg):
    store = get_store(cfg)
    with contextlib.closing(store.connect()) as db, db:
        users = store.users(db, cfg.users)
    users.sort(key=lambda r: r[0])
    wuser = max((len(u[0]) for u in users), default=0)
    o = cfg.stdout
    for user, uid, created in users:
        cfg.stdout.write(
            f"{o.CYAN}{user:{wuser}}{o.NORM} ({uid:016x})  "
            f"created: {created.isoformat(' ', 'seconds')}\n")


def cmd_user_memberships(cfg):
    store = get_store(cfg)
    with contextlib.closing(store.connect()) as db, db:
        memberships = store.user_memberships(db, cfg.origin, cfg.users,
                                             transitive=cfg.transitive)
    memberships.sort()
    wuser = max((len(m[0]) for m in memberships), default=0)
    wgroup = max((len(m[1]) for m in memberships), default=0)
    o = cfg.stdout
    prev = None
    for user, group, transitive in memberships:
        prefix = f"{o.CYAN}{user:{wuser}}{o.NORM}" if user != prev \
                 else f"{'':{wuser}}"
        if transitive:
            cfg.stdout.write(f"{prefix}  {o.LWHITE}{group:{wgroup}}{o.NORM}  "
                             "(transitive)\n")
        else:
            cfg.stdout.write(f"{prefix}  {o.LWHITE}{group}{o.NORM}\n")
        prev = user


def cmd_version(cfg):
    cfg.stdout.write(f"{__project__}-{__version__}\n")


def sphinx_build(cfg, target, *, build, tags=(), **kwargs):
    argv = [sys.executable, '-P', '-m', 'sphinx', 'build', '-M', target,
            cfg.source, build, '--fail-on-warning', '--jobs=auto']
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
    with contextlib.suppress(OSError):
        return path.stat()


class Application:
    def __init__(self, cfg, addr):
        self.cfg = cfg
        self.addr = addr
        self.lock = threading.Lock()
        self.directory = self.build_dir(0) / 'html'
        self.stop = False
        self.min_mtime = time.time_ns()
        self.returncode = 0
        self.conn_count = -1
        self.idle_start = 0
        self.opened = False
        self.build_mtime = None
        self.build_obs = api.ValueObservable('build', self.build_mtime)
        self.builder = threading.Thread(target=self.watch_and_build)
        self.builder.start()
        self.api = api.Api(
            cfg.store if cfg.store and cfg.store.exists() else None,
            stderr=cfg.stderr)
        self.api.event.add_observable(self.build_obs)
        self.api.add_endpoint('terminate', self.handle_terminate)

    def __enter__(self): return self

    def __exit__(self, typ, value, tb):
        with self.lock: self.stop = True
        self.builder.join()

    def watch_and_build(self):
        self.remove_all()
        interval = self.cfg.interval * 1_000_000_000
        delay = self.cfg.delay * 1_000_000_000
        idle = self.cfg.exit_on_idle * 1_000_000_000
        prev, prev_mtime, build_mtime = 0, 0, None
        while True:
            if prev != 0: time.sleep(0.1)
            now = time.time_ns()
            with self.lock:
                if self.stop: break
                if (self.conn_count == 0 and idle > 0
                        and now > self.idle_start + idle):
                    self.server.shutdown()
                    break
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
                self.build_obs.set(str(mtime))
                self.print_serving()
                if build_mtime is not None:
                    self.remove(self.build_dir(build_mtime))
                build_mtime = mtime
            else:
                self.remove(self.build_dir(mtime))
            self.print_upgrade()
            prev = time.time_ns()
        if build_mtime is not None: self.remove(self.build_dir(build_mtime))

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
        try:
            res = sphinx_build(self.cfg, 'html', build=build,
                               tags=['tdoc-dev', f'tdoc-build-{mtime}'])
            if res.returncode == 0: return build
        except Exception as e:
            self.cfg.stderr.write(f"Build: {e}\n")
        if self.cfg.exit_on_failure:
            self.returncode = 1
            self.server.shutdown()

    def remove(self, build):
        build.relative_to(self.cfg.build)  # Ensure we're below the build dir
        def on_error(fn, path, e):
            self.cfg.stderr.write(f"Removal: {fn}: {path}: {e}\n")
        shutil.rmtree(build, onexc=on_error)

    def remove_all(self):
        for build in self.cfg.build.glob('serve-[0-9]*'):
            self.remove(build)

    def print_serving(self):
        host, port = self.addr[:2]
        if ':' in host: host = f'[{host}]'
        o = self.cfg.stdout
        o.write(f"Serving at <{o.LBLUE}http://{host}:{port}/{o.NORM}>\n")
        o.flush()
        if self.cfg.open and not self.opened:
            self.opened = True
            webbrowser.open_new_tab(f'http://{host}:{port}/')

    def print_upgrade(self):
        if sys.prefix == sys.base_prefix: return  # Not running in a venv
        o = self.cfg.stdout
        with contextlib.suppress(Exception):
            marker = pathlib.Path(sys.prefix) / 'upgrade.txt'
            cur, new = marker.read_text('utf-8').split(' ')[:2]
            if cur == new: return
            o.write(f"""\
{o.LYELLOW}An upgrade is available:{o.NORM} {__project__}\
 {o.CYAN}{cur}{o.NORM} => {o.CYAN}{new}{o.NORM}
Release notes: <https://common.t-doc.org/release-notes.html\
#release-{new.replace('.', '-')}>
{o.BOLD}Restart the server to upgrade.{o.NORM}
""")

    def __call__(self, env, respond):
        env['tdoc.dev'] = True

        # Dispatch to API if this is an API call.
        script_name, path_info = env['SCRIPT_NAME'], env['PATH_INFO']
        if wsgiutil.shift_path_info(env) == '*api':
            return self.api(env, respond)
        env['SCRIPT_NAME'], env['PATH_INFO'] = script_name, path_info

        # Handle a file request.
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
        mime_type = mimetypes.guess_type(path)[0] or 'application/octet-stream'
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

    def handle_terminate(self, env, respond):
        wsgi.method(env, HTTPMethod.POST)
        r = parse.parse_qs(env.get('QUERY_STRING', '')).get('r', ['0'])[0]
        respond(wsgi.http_status(HTTPStatus.OK), [
            ('Content-Type', 'text/plain; charset=utf-8'),
            ('Content-Length', '0'),
        ])
        try:
            self.returncode = int(r)
        except ValueError:
            self.returncode = 1
        self.server.shutdown()
        return []


if __name__ == '__main__':
    main()
