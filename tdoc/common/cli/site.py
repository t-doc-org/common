# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import contextlib
import errno
from http import HTTPMethod, HTTPStatus
import itertools
import mimetypes
import os
import pathlib
import posixpath
import re
import shutil
import signal
import socket
import socketserver
import stat
import sys
import tempfile
import threading
import time
from urllib import parse
import webbrowser
from wsgiref import simple_server

from .. import __project__, api, cli, deps, logs, util, wsgi

_log = logs.logger(__name__)
rc_build_failure = 1
rc_source_change = 123


def add_commands(parser):
    p = parser.add_parser('site', help="Site-related commands.")
    sp = p.add_subparsers(title="Sub-commands")
    sp.required = True

    p = sp.add_parser('build', help="Build a site.")
    p.set_defaults(handler=cmd_build)
    arg = p.add_argument
    arg('target', metavar='TARGET', nargs='+', help="The build targets to run.")
    add_sphinx_options(p)
    cli.add_common_options(p)

    p = sp.add_parser('clean', help="Clean the build products of a site.")
    p.set_defaults(handler=cmd_clean)
    add_sphinx_options(p)
    cli.add_common_options(p)

    p = sp.add_parser('serve', help="Serve a site locally.")
    p.set_defaults(handler=cmd_serve)
    p.set_defaults(default_port=int(os.environ.get('TDOC_DEFAULT_PORT', 8000)))
    arg = p.add_argument
    arg('--bind', metavar='ADDRESS', dest='bind',
        default='ALL' if 'TDOC_SANDBOX' in os.environ else 'localhost',
        help="The address to bind the server to (default: %(default)s). "
             "Specify ALL to bind to all interfaces.")
    arg('--cache', metavar='PATH', dest='cache', type='path', default='_cache',
        help="The path to the cache directory (default: %(default)s).")
    arg('--delay', metavar='DURATION', dest='delay', type=float, default=1.0,
        help="The delay in seconds between detecting a source change and "
             "triggering a build (default: %(default)s).")
    arg('--exit-on-change', action='store_true', dest='exit_on_change',
        help="Terminate the server on changes.")
    arg('--exit-on-failure', action='store_true', dest='exit_on_failure',
        help="Terminate the server on build failure.")
    arg('--exit-on-idle', metavar='DURATION', dest='exit_on_idle', type=float,
        default=0.0,
        help="The time in seconds after the last watch connection closes when "
             "the server terminates (default: %(default)s).")
    arg('--ignore', metavar='REGEXP', dest='ignore', type='regexp',
        default=f'(^|{re.escape(os.sep)})__pycache__$',
        help="A regexp matching files and directories to ignore from watching "
             "(default: %(default)s).")
    arg('--full-builds', action='store_true', dest='full_builds',
        help="Perform full builds on source changes.")
    arg('--interval', metavar='DURATION', dest='interval', type=float,
        default=1.0,
        help="The interval in seconds at which to check for source changes "
             "(default: %(default)s).")
    arg('--open', action='store_true', dest='open',
        help="Open the site in a browser tab after the first build completes.")
    arg('--port', metavar='PORT', dest='port', type=int, default=0,
        help="The port to bind the server to (default: first unused port "
             f"starting at {p.get_default('default_port')}).")
    arg('--restart-on-change', action='store_true', dest='restart_on_change',
        help="Restart the server on changes.")
    arg('--watch', metavar='PATH', dest='watch', type='path', action='append',
        default=[],
        help="Additional directories to watch for changes.")
    add_sphinx_options(p)
    cli.add_common_options(p)


def add_sphinx_options(parser):
    arg = parser.add_argument_group("Sphinx options").add_argument
    arg('--build', metavar='PATH', dest='build', type='path', default='_build',
        help="The path to the build directory (default: %(default)s).")
    arg('--source', metavar='PATH', dest='source', type='path', default='docs',
        help="The path to the source files (default: %(default)s).")
    arg('--sphinx-opt', metavar='OPT', action='append', dest='sphinx_opts',
        default=[], help="Additional options to pass to sphinx-build.")


def cmd_build(opts):
    for target in opts.target:
        res = sphinx_build(opts, target, build=opts.build)
        if res.returncode != 0: return res.returncode


def cmd_clean(opts):
    return sphinx_build(opts, 'clean', build=opts.build).returncode


def pre_serve(opts):
    if not opts.restart_on_change: return
    argv = ['--exit-on-change' if a == '--restart-on-change' else a
            for a in sys.orig_argv]
    while True:
        opts.stderr.write("Starting server as a subprocess\n")
        p = util.run(*argv, stdin=opts.stdin, success=None,
                     monitor=util.terminate_on(signal.SIGTERM))
        if p.returncode != rc_source_change: return p.returncode
        time.sleep(0.1)


@cli.pre_run(pre_serve)
def cmd_serve(opts):
    opts.local = True
    addr = (opts.bind if opts.bind != 'ALL' else '', opts.port)
    families = {info[0] for info in socket.getaddrinfo(
                    addr[0] or None, opts.port, type=socket.SOCK_STREAM,
                    flags=socket.AI_PASSIVE)}

    class Server(ServerBase):
        address_family = socket.AF_INET6 if socket.AF_INET6 in families \
                         else socket.AF_INET
        default_port = opts.default_port

    with Server(addr, RequestHandler) as srv, \
            cli.get_store(opts, allow_mem=True) as st, \
            api.Api(config=opts.cfg, store=st) as api_, \
            Application(opts, srv, api_) as app:
        srv.set_app(app)
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            opts.stderr.write("Interrupted, exiting\n")
    return app.returncode


def sphinx_build(opts, target, *, build, tags=(), **kwargs):
    # Prevent building untrusted sites outside of a sandbox.
    if 'TDOC_SANDBOX' not in os.environ \
            and not opts.cfg.get('site.trusted', False) \
            and ((base := os.environ.get('TDOC_RUN_BASE')) is None
                 or not opts.source.is_relative_to(base)):
        raise Exception(
            "Refusing to build an untrusted site outside of a sandbox")

    # Run sphinx.
    argv = [sys.executable, '-P', '-m', 'sphinx', 'build', '-M', target,
            opts.source, build, '--fail-on-warning', '--jobs=auto']
    argv += [f'--tag={tag}' for tag in tags]
    if opts.debug: argv += ['--show-traceback']
    argv += opts.sphinx_opts
    return util.run(*argv, success=None, **kwargs)


class ServerBase(socketserver.ThreadingMixIn, simple_server.WSGIServer):
    daemon_threads = True

    # SO_REUSEADDR is enabled on POSIX platforms to work around the TIME_WAIT
    # issue after the process terminates. On these platforms, the option still
    # doesn't allow multiple processes to listen on the exact same address
    # simultaneously. Windows does, though, and this interferes with automatic
    # port selection. But Windows doesn't have the TIME_WAIT issue, so
    # SO_REUSEADDR is disabled there.
    # https://stackoverflow.com/questions/14388706/how-do-so-reuseaddr-and-so-reuseport-differ/14388707#14388707
    allow_reuse_address = os.name not in ('nt', 'cygwin')

    @property
    def host_port(self): return self.bind_address[:2]

    def server_bind(self):
        with contextlib.suppress(Exception):
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        addr = self.server_address
        port = addr[1]
        if auto_port := port == 0: port = self.default_port
        while True:
            # server_bind() sets server_address to the socket's name.
            self.server_address = self.bind_address = addr = \
                addr[:1] + (port,) + addr[2:]
            try:
                return super().server_bind()
            except OSError as e:
                if not auto_port or e.errno != errno.EADDRINUSE: raise
                if (port := port + 1) > 65535: raise


class RequestHandler(simple_server.WSGIRequestHandler):
    def log_request(self, code='-', size='-'): pass

    def log_message(self, format, *args):
        _log.debug((format % args).translate(self._control_char_table))


def try_stat(path):
    with contextlib.suppress(OSError):
        return path.stat()


def prefix_read(fname):
    return (pathlib.Path(sys.prefix) / fname).read_text('utf-8')


version_re = re.compile(f'(?m)^{re.escape(__project__)}==([^\\s;]+)(?:\\s|$)')

def project_version(reqs):
    if (m := version_re.search(reqs)) is not None: return m.group(1)
    return 'unknown'


class Application(wsgi.Dispatcher):
    def __init__(self, opts, server, api_):
        super().__init__()
        self.opts = opts
        self.server = server
        self.lock = threading.Condition(threading.Lock())
        self.directory = self.build_dir(0) / 'html'
        self.stop = False
        self.min_mtime = time.time_ns()
        self.returncode = 0
        self.api = self.add_endpoint('_api', api_)
        self.api.add_endpoint('terminate', self.handle_terminate)
        self.opened = False

        self.build_mtime = None
        self.build = api.ValueObservable('build', self.build_mtime)
        self.api.events.add_observable(self.build)
        self.builder = threading.Thread(target=self.watch_and_build,
                                        name='builder')
        self.builder.start()

        self.repo_incoming = api.ValueObservable('repo_incoming', {})
        self.api.events.add_observable(self.repo_incoming)
        self.repo_incoming_checker = threading.Thread(
            target=self.check_repo_incoming, name='repo_incoming')
        self.repo_incoming_checker.start()

    def __enter__(self): return self

    def __exit__(self, typ, value, tb):
        with self.lock:
            self.stop = True
            self.lock.notify_all()
        self.builder.join()

    def sleep(self, duration):
        with self.lock:
            if duration >= 0:
                self.lock.wait_for(lambda: self.stop, timeout=duration)
            if self.stop: return True

    def watch_and_build(self):
        self.remove_all()
        interval = self.opts.interval * 1_000_000_000
        delay = self.opts.delay * 1_000_000_000
        idle = self.opts.exit_on_idle * 1_000_000_000
        prev, prev_mtime, build_mtime = 0, 0, None
        build_next = self.build_dir('next')
        # TODO: Use monotonic clock for delays
        # TODO: Avoid looping at 10Hz
        while True:
            if self.sleep(0.1 if prev != 0 else 0): break
            now = time.time_ns()
            if (idle > 0 and (lw := self.api.events.last_watcher) is not None
                    and now > lw + idle):
                self.server.shutdown()
                break
            if now < prev + interval: continue
            mtime = self.latest_mtime()
            if mtime <= prev_mtime:
                prev = now
                continue
            if now < mtime + delay and prev_mtime != 0:
                prev = mtime + delay - interval
                continue
            if prev_mtime != 0:
                if self.opts.exit_on_change:
                    self.opts.stderr.write(
                        "\nSource change detected, exiting\n")
                    self.returncode = rc_source_change
                    self.server.shutdown()
                    break
                self.opts.stderr.write(
                    "\nSource change detected, rebuilding\n")
            prev_mtime = mtime
            if self.build_site(build_next, mtime):
                build = self.build_dir(mtime)
                os.rename(build_next, build)
                with self.lock:
                    self.build_mtime = mtime
                    self.directory = build / 'html'
                self.build.set(str(mtime))
                self.print_serving()
                if build_mtime is not None:
                    self.remove(self.build_dir(build_mtime))
                build_mtime = mtime
            else:
                self.remove(build_next)
            if not self.opts.full_builds and build_mtime is not None:
                shutil.copytree(self.build_dir(build_mtime), build_next,
                                symlinks=True)
            self.print_upgrade()
            prev = time.time_ns()
        if build_mtime is not None: self.remove(self.build_dir(build_mtime))
        self.remove(build_next)

    def latest_mtime(self):
        mtime = self.min_mtime
        pred = lambda path, root: self.opts.ignore.search(str(path)) is None
        for path in itertools.chain([self.opts.source], self.opts.watch):
            for _, t in self.find_files(path, file_pred=pred, dir_pred=pred,
                                        missing_ok=True):
                mtime = max(mtime, t)
        for _, srcs, _, _ in self.list_imports():
            for _, t in srcs: mtime = max(mtime, t)
        return mtime

    def find_files(self, root, *, file_pred=lambda p, r: True, dir_pred=None,
                   missing_ok=False):
        if missing_ok and not root.exists(): return
        def on_error(e): _log.error("Scan: %(exc)s", exc=e)
        for parent, dirs, files in root.walk(on_error=on_error):
            for fn in files:
                path = parent / fn
                if not file_pred(path, root): continue
                try:
                    st = path.stat()
                    if stat.S_ISREG(st.st_mode): yield path, st.st_mtime_ns
                except Exception as e:
                    on_error(e)
            if dir_pred is not None:
                dirs[:] = [d for d in dirs if dir_pred(parent / d, root)]

    def build_dir(self, mtime):
        return self.opts.build / f'serve-{self.server.host_port[1]}-{mtime}'

    def build_site(self, build, mtime):
        try:
            self.update_imports(mtime)
            res = sphinx_build(self.opts, 'html', build=build,
                               tags=['tdoc-local'])
            if res.returncode == 0: return True
        except Exception as e:
            _log.error("Build: %(exc)s", exc=e)
        if self.opts.exit_on_failure:
            self.returncode = rc_build_failure
            self.server.shutdown()
        return False

    _import = '_import'
    _import_glob = f'{_import}/**'

    def list_imports(self):
        import_files = self.opts.cfg.sub('import-files')
        for dst in import_files.keys():
            if isinstance(src := import_files.get(dst), str):
                include = ['**/*.export/**', '**/*.export.*']
                exclude = [self._import_glob]
            else:
                spec = import_files.sub(dst)
                src = spec.get('src')
                include = spec.get('include', [])
                exclude = [self._import_glob] + spec.get('exclude', [])
            src = import_files.as_path(src)
            if not src.exists(): continue
            dst = (self.opts.source / self._import / dst).resolve()
            def pred(path, root):
                path = path.relative_to(root)
                return any(path.full_match(p) for p in include) \
                       and not any(path.full_match(p) for p in exclude)
            srcs = self.find_files(src, file_pred=pred)
            dsts = self.find_files(dst, missing_ok=True)
            yield src, srcs, dst, dsts

    def update_imports(self, mtime):
        for src, srcs, dst, dsts in self.list_imports():
            dsts = set(p for p, _ in dsts)

            # Copy files but don't overwrite if the content hasn't changed.
            for sp, _ in srcs:
                dp = dst / sp.relative_to(src)
                dsts.discard(dp)
                try:
                    cur = dp.read_bytes() if dp.is_file() else None
                    new = util.read_stable(sp)
                    if new != cur:
                        dp.parent.mkdir(parents=True, exist_ok=True)
                        dp.write_bytes(new)
                        os.utime(dp, ns=(dp.stat().st_atime_ns, mtime))
                except Exception as e:
                    _log.error("Copy: %(src)s -> %(dst)s: %(exc)s", src=sp,
                               dst=dp, exc=e)

            # Remove stale files.
            for dp in dsts:
                try:
                    dp.unlink()
                    for p in dp.parents:
                        if p == dst: break
                        try: p.rmdir()
                        except OSError: break
                except Exception as e:
                    _log.error("Remove: %(path)s: %(exc)s", path=dp, exc=e)

    def remove(self, build):
        build.relative_to(self.opts.build)  # Ensure we're below the build dir
        if not build.exists(): return
        def on_error(fn, path, e):
            _log.error("Remove: %(func)s: %(path)s: %(exc)s", func=fn,
                       path=path, exc=e)
        shutil.rmtree(build, onexc=on_error)

    def remove_all(self):
        for build in self.opts.build.glob(
                f'serve-{self.server.host_port[1]}-*'):
            self.remove(build)

    def print_serving(self):
        host, port = self.server.host_port
        if host in ('', '::', '0.0.0.0'):
            host = 'localhost' if 'TDOC_SANDBOX' in os.environ \
                   else socket.getfqdn()
        if ':' in host: host = f'[{host}]'
        o = self.opts.stderr
        o.write(f"Serving at <{o.LBLUE}http://{host}:{port}/{o.NORM}>\n")
        o.flush()
        if self.opts.open and not self.opened:
            self.opened = True
            webbrowser.open_new_tab(f'http://{host}:{port}/')

    def print_upgrade(self):
        if sys.prefix == sys.base_prefix: return  # Not running in a venv
        o = self.opts.stderr
        with contextlib.suppress(Exception):
            reqs = prefix_read('requirements.txt')
            reqs_up = prefix_read('requirements-upgrade.txt')
            if reqs_up == reqs: return
            cur, new = project_version(reqs), project_version(reqs_up)
            o.write(f"""\
{o.LYELLOW}An upgrade is available:{o.NORM} {__project__}\
 {o.CYAN}{cur}{o.NORM} => {o.CYAN}{new}{o.NORM}
Release notes: <{o.LBLUE}https://common.t-doc.org/release-notes.html\
#release-{new.replace('.', '-')}{o.NORM}>
{o.LWHITE}Restart the server to upgrade.{o.NORM}
""")

    def check_repo_incoming(self):
        while True:
            data = {}
            for repo in self.list_repos():
                if (url := self.hg_path(repo, 'default')) is None: continue
                if not url.startswith(('https://', 'file://')): continue
                proc = self.hg(f'--repository={repo}', 'incoming',
                               '--template=@tdoc-incoming\n', success=None)
                if proc.returncode not in (0, 1): continue
                data[url.rsplit('/', 1)[-1]] = \
                    proc.stdout.count('@tdoc-incoming\n')
            self.repo_incoming.set(data)
            if self.sleep(15 * 60): break

    def list_repos(self):
        if (p := self.find_repo(self.opts.source)) is not None: yield p
        for src, *_ in self.list_imports():
            if (p := self.find_repo(src)) is not None: yield p

    def find_repo(self, path):
        if (path / '.hg').is_dir(): return path
        for p in path.parents:
            if (p / '.hg').is_dir(): return p

    def hg(self, *args, **kwargs):
        return util.run('hg', *args, capture_output=True, text=True, **kwargs)

    hg_paths_re = re.compile(r'^paths\.([^=]+)=(.*)$')

    def hg_path(self, repo, name):
        paths = {}
        proc = self.hg(f'--repository={repo}', 'config', 'paths', success=None)
        if proc.returncode != 0: return
        for line in proc.stdout.splitlines():
            if (m := self.hg_paths_re.fullmatch(line)) is None: continue
            paths[m[1]] = m[2]
        while True:
            if (p := paths.get(name)) is None: return
            if (n := p.removeprefix('path://')) == p: return p
            name = n

    def handle_request(self, handler, wr):
        wr.env['wsgi.multithread'] = True
        wr.local = True
        return handler(wr.env, wr.respond, wr)

    @wsgi.endpoint('_cache', methods=(HTTPMethod.GET, HTTPMethod.HEAD),
                   final=False, csrf=False, log_level=logs.DEBUG)
    def handle_cache(self, wr):
        yield from self.handle_file(wr, self.opts.cache,
                                    self.on_cache_not_found)

    def on_cache_not_found(self, path_info, path):
        url = ''
        try:
            parts = path_info.split('/', 3)
            if parts[0] != '' or len(parts) < 4: return
            if (d := deps.info.get(parts[1])) is None: return
            url = f'{d['url'](d['name'], parts[2])}/{parts[3]}'
            _log.debug("Caching: %(url)s", url=url)
            with util.urlopen(url) as f: data = f.read()
            path.parent.mkdir(parents=True, exist_ok=True)
            with util.write_atomic(path, 'wb') as f: f.write(data)
        except Exception as e:
            _log.error("Cache [%(url)s]: %(exc)s", url=url, exc=e)

    @wsgi.endpoint('/', methods=(HTTPMethod.GET, HTTPMethod.HEAD), final=False,
                   csrf=False, log_level=logs.DEBUG)
    def handle_default(self, wr):
        with self.lock: base = self.directory
        yield from self.handle_file(wr, base)

    def handle_file(self, wr, base, on_not_found=None):
        method = wr.method
        path_info = wr.path
        path = self.file_path(path_info, base)
        path.relative_to(base)  # Ensure we're below base
        if (st := try_stat(path)) is None:
            if on_not_found is None: raise wsgi.Error(HTTPStatus.NOT_FOUND)
            on_not_found(path_info, path)
            if (st := try_stat(path)) is None:
                raise wsgi.Error(HTTPStatus.NOT_FOUND)

        if stat.S_ISDIR(st.st_mode):
            parts = parse.urlsplit(path_info)
            if not parts.path.endswith('/'):
                location = parse.urlunsplit(
                    (parts[:2] + (parts[2] + '/',) + parts[3:]))
                wr.redirect(location, HTTPStatus.MOVED_PERMANENTLY)
                return
            path = path / 'index.html'
            if (st := try_stat(path)) is None:
                raise wsgi.Error(HTTPStatus.NOT_FOUND)

        if not stat.S_ISREG(st.st_mode):
            raise wsgi.Error(HTTPStatus.NOT_FOUND)
        mime_type = mimetypes.guess_type(path)[0] or 'application/octet-stream'
        wr.respond(wsgi.http_status(HTTPStatus.OK), [
            # TODO: Document why the Access-Control-* headers are needed
            ('Access-Control-Allow-Origin', '*'),
            ('Access-Control-Expose-Headers', '*'),
            ('Content-Type', mime_type),
            ('Content-Length', str(st.st_size)),
        ])
        if method == HTTPMethod.HEAD: return
        yield from wr.file_wrapper(open(path, 'rb'))

    def file_path(self, path, base):
        trailing = path.rstrip().endswith('/')
        try:
            path = parse.unquote(path, errors='surrogatepass')
        except UnicodeDecodeError:
            path = parse.unquote(path)
        res = base
        for part in filter(None, posixpath.normpath(path).split('/')):
            if pathlib.Path(part).parent.name or part in (os.curdir, os.pardir):
                continue
            res = res / part
        return res / '' if trailing else res

    @wsgi.endpoint(None, methods=(HTTPMethod.POST,), csrf=False)
    def handle_terminate(self, wr):
        rc = wr.json.get('rc', 0)
        yield from wr.respond_json({})
        try:
            self.returncode = int(rc)
        except ValueError:
            self.returncode = 1
        self.server.shutdown()
