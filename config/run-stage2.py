#!/usr/bin/env python
# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import contextlib
import contextvars
import functools
import json
import os
import pathlib
import re
import signal
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import threading
import time
import tomllib
from urllib import request
import venv

# The URL of the config directory.
CONFIG = 'https://github.com/t-doc-org/common/raw/refs/heads/main/config'


def main(**kwargs):
    try:
        sys.exit(run(**kwargs))
    except SystemExit:
        raise
    except KeyboardInterrupt:
        sys.exit(1)
    except BaseException as e:
        if '--debug' in sys.argv: raise
        sys.stderr.write(f'\nERROR: {e}\n')
        maybe_wait_on_exit(sys.stderr)
        sys.exit(1)


def run(argv, stdin, stdout, stderr, base, ssl_ctx=None, **kwargs):
    # Parse command-line options.
    config = None
    debug = False
    hermetic = None
    print_key = None
    version = os.environ.get('TDOC_VERSION')
    i = 1
    while True:
        if i >= len(argv) or not (arg := argv[i]).startswith('--'):
            argv = argv[:1] + argv[i:]
            break
        elif arg == '--':
            argv = argv[:1] + argv[i + 1:]
            break
        elif arg.startswith('--config='):
            config = arg[9:]
        elif arg == '--debug':
            debug = True
        elif arg == '--hermetic':
            hermetic = True
        elif arg == '--no-hermetic':
            hermetic = False
        elif arg.startswith('--print='):
            print_key = arg[8:]
        elif arg.startswith('--version='):
            version = arg[10:]
        else:
            raise Exception(f"Unknown option: {arg}")
        i += 1

    # Create a environment builder.
    with EnvBuilder(base, config, version, hermetic, ssl_ctx, stderr,
                    debug or '--debug' in argv) as builder:
        if print_key is not None:
            v = builder.config
            try:
                for k in print_key.split('.'): v = v[k]
            except KeyError:
                return 1
            stdout.write(str(v))
            return 0

        # Check the Python version.
        check_python(builder, stderr)

        # Find a matching venv, or create one if there is none.
        envs, matching = builder.find()
        if not matching:
            stderr.write("Installing...\n")
            env = builder.new()
            env.create()
            stderr.write("\n")
        else:
            env = matching[0]

        # Remove old venvs.
        for e in envs:
            if e is not env: e.remove()

        # Handle pending upgrades.
        env = handle_upgrades(builder, env, stderr)

        # Check for upgrades in the background and run the command.
        with env.check_upgrade():
            args = argv[1:] if len(argv) > 1 else builder.default_command
            args[0] = env.bin_path(args[0])
            with subprocess.Popen(args) as p:
                signal.signal(signal.SIGTERM, lambda *args: p.terminate())
                try:  # Do the same as subprocess.run()
                    p.communicate()
                except BaseException:
                    p.kill()
                    raise
            return p.poll()


def check_python(builder, stderr):
    py = builder.config.get('python', {})
    if (v := version_tuple(py.get('minimum'))) and sys.version_info < v:
        raise Exception(f"""\
Python >={version_str(v)} is required \
(currently used: {version_str(sys.version_info[:3])}).
See <https://common.t-doc.org/install.html>.""")
    if (v := version_tuple(py.get('recommend'))) and sys.version_info < v:
        stderr.write(f"""\
Python >={version_str(v)} is recommended \
(currently used: {version_str(sys.version_info[:3])}).
Please abort (Ctrl+C) and install or select a more recent version (see
<https://common.t-doc.org/install.html>), or press ENTER to continue with the
current version.
""")
        input()


def handle_upgrades(builder, env, stderr):
    upgrades = []
    reqs, reqs_up = env.requirements, env.requirements_upgrade
    if reqs_up is not None and reqs_up != reqs:
        cur, new = builder.version_from(reqs), builder.version_from(reqs_up)
        if new != cur:
            upgrades.append(f" - {builder.package} {cur} => {new}\n")
        else:
            upgrades.append(f" - {builder.package} {new}\n")
        upgrades.append(f"""\
   Release notes: <https://common.t-doc.org/release-notes.html\
#release-{new.replace('.', '-')}>
""")
    cur_py, new_py = env.py_version_info[:3], sys.version_info[:3]
    if new_py != cur_py:
        upgrades.append(f"""\
 - Python {version_str(cur_py)} => {version_str(new_py)}
""")
    if not upgrades: return env
    stderr.write("An upgrade is available:\n")
    stderr.write("".join(upgrades))
    stderr.write("Would you like to upgrade (y/n)? ")
    stderr.flush()
    resp = input().lower()
    stderr.write("\n")
    if resp not in ('y', 'yes', 'o', 'oui', 'j', 'ja'): return env
    stderr.write("Upgrading...\n")
    try:
        new_env = builder.new()
        new_env.create(reqs_up)
        env = new_env
    except Exception as e:
        if builder.debug: raise
        stderr.write(f"\nThe upgrade failed: {e}\n"
                     "Continuing with the previous version.\n")
    stderr.write("\n")
    return env


class Namespace(dict):
    def __getattr__(self, name):
        return self[name]


def merge_dict(dst, src):
    for k, sv in src.items():
        if isinstance(sv, dict) and isinstance(dv := dst.get(k), dict):
            merge_dict(dv, sv)
        else:
            dst[k] = sv


def version_str(info):
    return '.'.join(str(v) for v in info)


def version_tuple(version):
    if not version: return None
    return tuple(try_int(v) for v in version.split('.'))


def try_int(v):
    try: return int(v)
    except ValueError: return v


version_re = re.compile(r'[0-9][0-9a-z.!+]*')
tag_re = re.compile(r'[a-z][a-z0-9-]*')

def is_version(version): return version_re.match(version)
def is_tag(version): return tag_re.match(version)
def is_dev(version): return version == 'dev'
def is_wheel(version): return pathlib.Path(version).resolve().is_file()


def thread(fn):
    t = threading.Thread(target=fn, daemon=True)
    t.start()
    return t


@contextlib.contextmanager
def write_atomic(path, *args, **kwargs):
    with tempfile.NamedTemporaryFile(*args, dir=path.parent,
                                     prefix=path.name + '.',
                                     delete_on_close=False, **kwargs) as f:
        yield f
        f.close()
        pathlib.Path(f.name).replace(path)


class Env:
    requirements_txt = 'requirements.txt'
    requirements_deps_txt = 'requirements-deps.txt'
    requirements_upgrade_txt = 'requirements-upgrade.txt'

    env = contextvars.ContextVar('env')

    def __init__(self, path, builder):
        self.path, self.builder = path, builder

    @functools.cached_property
    def requirements(self):
        try:
            return (self.path / self.requirements_txt).read_text()
        except OSError:
            return None

    @functools.cached_property
    def requirements_upgrade(self):
        try:
            return (self.path / self.requirements_upgrade_txt).read_text()
        except OSError:
            return None

    @functools.cached_property
    def sysinfo(self):
        vars = {'base': self.path, 'platbase': self.path,
                'installed_base': self.path, 'intsalled_platbase': self.path}
        return (pathlib.Path(sysconfig.get_path('scripts', scheme='venv',
                                                vars=vars)),
                sysconfig.get_config_vars().get('EXE', ''))

    @functools.cached_property
    def py_version_info(self):
        out = self.python('-c',
            'import sys; '
            'print(".".join(str(v) for v in sys.version_info), end="")',
            capture_output=True)
        return tuple(try_int(v) for v in out.split('.'))

    def bin_path(self, name):
        scripts, ext = self.sysinfo
        return scripts / f'{name}{ext}'

    def create(self, requirements=None):
        self.builder.root.mkdir(exist_ok=True)
        token = self.env.set((self, requirements))
        try:
            self.builder.create(self.path)
        except BaseException:
            self.remove()
            raise
        finally:
            self.env.reset(token)

    def remove(self):
        try:
            if self.path.relative_to(self.builder.root) == pathlib.Path():
                raise Exception(f"{self.path}: Not below venv root")
            def on_error(fn, path, e):
                self.builder.out.write(f"ERROR: {fn}: {path}: {e}\n")
            shutil.rmtree(self.path, onexc=on_error)
        except Exception as e:
            self.builder.out.write(f"ERROR: {e}")

    def uv(self, *args, **kwargs):
        p = subprocess.run((self.bin_path('uv'), *args),
                           stdin=subprocess.DEVNULL, text=True, **kwargs)
        if p.returncode != 0: raise Exception(p.stderr)
        return p.stdout

    def python(self, *args, **kwargs):
        p = subprocess.run((self.bin_path('python'), '-P', *args),
                           stdin=subprocess.DEVNULL, text=True, **kwargs)
        if p.returncode != 0: raise Exception(p.stderr)
        return p.stdout

    def pip(self, *args, json_output=False, **kwargs):
        out = self.python('-m', 'pip', '--require-virtualenv', *args, **kwargs)
        if not json_output: return out
        return json.loads(out, object_pairs_hook=Namespace)

    @contextlib.contextmanager
    def check_upgrade(self):
        th = None
        if not (is_dev(v := self.builder.version) or is_wheel(v)):
            th = thread(self._check_upgrade)
            wait_until = time.monotonic() + 5
        try:
            yield
        finally:
            # Give the thread a chance to run at least for a bit.
            if th is not None: th.join(wait_until - time.monotonic())

    def _check_upgrade(self):
        try:
            reqs = self.builder.requirements(config=self.builder.live_config())
            if reqs != self.requirements:
                with write_atomic(
                        self.path / self.requirements_upgrade_txt, 'w') as f:
                    f.write(reqs)
        except Exception:
            if self.builder.debug: raise


class EnvBuilder(venv.EnvBuilder):
    venv_root = '_venv'
    run_toml = 'run.toml'
    run_local_toml = 'run.local.toml'

    def __init__(self, base, config, version, hermetic, ssl_ctx, out, debug):
        super().__init__(with_pip=True)
        self.lock = threading.Lock()
        self.base = base
        self.root = base / self.venv_root
        self.config_url = config
        self._live_config = None
        self._fetch_thread = None
        self.ssl_ctx = ssl_ctx
        self.out, self.debug = out, debug
        if version is None: version = self.config['version']
        if not (is_version(version) or is_tag(version) or is_wheel(version)):
            raise Exception(f"Invalid version: {version}")
        self.version, self.hermetic = version, hermetic

    def __enter__(self):
        with self.lock: fetched = self._live_config is not None
        if not fetched:
            self._fetch_thread = thread(self.live_config)
            self._fetch_wait_until = time.monotonic() + 5
        return self

    def __exit__(self, typ, value, tb):
        if (th := self._fetch_thread) is not None:
            # Give the thread a chance to run at least for a bit.
            th.join(self._fetch_wait_until - time.monotonic())

    @functools.cached_property
    def package(self):
        return self.config['package']

    @functools.cached_property
    def config(self):
        try:
            data = (self.root / self.run_toml).read_bytes()
            config = tomllib.loads(data.decode('utf-8'))
        except Exception:
            return self.live_config()
        self.merge_local_configs(config)
        return config

    def live_config(self):
        with self.lock:
            if (c := self._live_config) is not None: return c
            data = self.fetch(self.run_toml)
            config = tomllib.loads(data.decode('utf-8'))
            self.root.mkdir(exist_ok=True)
            with write_atomic(self.root / self.run_toml, 'wb') as f:
                f.write(data)
            self.merge_local_configs(config)
            self._live_config = config
            return config

    def fetch(self, name):
        if (url := self.config_url) is None:
            with contextlib.suppress(Exception):
                return (self.base / 'config' / name).read_bytes()
            url = CONFIG
        if '://' not in url: return (pathlib.Path(url) / name).read_bytes()
        with request.urlopen(f'{url}/{name}', context=self.ssl_ctx,
                             timeout=30) as f:
            return f.read()

    def merge_local_configs(self, config):
        self.merge_config(config, self.base / self.run_toml)
        self.merge_config(config, self.base / self.run_local_toml)

    def merge_config(self, config, path):
        with contextlib.suppress(OSError), path.open('rb') as f:
            merge_dict(config, tomllib.load(f))

    @property
    def default_command(self):
        key = 'command-dev' if is_dev(self.version) else 'command'
        args = [(k, v) for k, v in self.config['defaults'].items()
                if k == key or k.startswith(key + '_')]
        args.sort()
        return functools.reduce(lambda a, b: a + b, (it[1] for it in args), [])

    def requirements(self, config=None):
        if is_dev(v := self.version): return f'-e {self.base.as_uri()}\n'
        if is_wheel(v): return f'{pathlib.Path(v).resolve().as_uri()}\n'
        if config is None: config = self.config
        version_num = config.get('tags', {}).get(v) if is_tag(v) else v
        if version_num is None:
            raise Exception(f"Unknown version tag: {v}\nAvailable tags: "
                            f"{' '.join(sorted(config['tags'].keys()))}")
        hermetic = self.hermetic if self.hermetic is not None \
                   else config.get('hermetic', True)
        if not hermetic: return f'{config['package']}=={version_num}\n'
        return self.fetch(f'{version_num}.req').decode('utf-8')

    def version_from(self, requirements):
        pat = re.compile(f'(?m)^{re.escape(self.package)}==([^\\s;]+)(?:\\s|$)')
        if (m := pat.search(requirements)) is not None: return m.group(1)

    def find(self):
        pat = 'dev' if is_dev(self.version) \
              else 'wheel' if is_wheel(self.version) else f'{self.version}-*'
        envs = [Env(path, self) for path in self.root.glob(pat)]
        envs.sort(key=lambda e: e.path, reverse=True)
        matching = [e for e in envs if e.requirements is not None]
        return envs, matching

    def new(self):
        name = 'dev' if is_dev(self.version) \
               else 'wheel' if is_wheel(self.version) \
               else f'{self.version}-{time.time_ns():024x}'
        return Env(self.root / name, self)

    def post_setup(self, ctx):
        super().post_setup(ctx)
        env, requirements = Env.env.get()
        pip_args = []
        if is_dev(self.version):
            uv_req = self.base / 'config' / 'uv.req'
            env.pip('install', '--require-hashes', '--only-binary=:all:',
                    '--no-deps', f'--requirement={uv_req}',
                    check=True, stdout=self.out, stderr=self.out)
            rdpath = env.path / env.requirements_deps_txt
            env.uv('export', '--frozen', '--no-emit-project',
                   '--format=requirements.txt', f'--output-file={rdpath}',
                   cwd=self.base, capture_output=True)
            env.pip('install', '--require-hashes', '--only-binary=:all:',
                    '--no-deps', f'--requirement={rdpath}',
                    check=True, stdout=self.out, stderr=self.out)
            pip_args.append('--no-deps')

        if requirements is None: requirements = self.requirements()
        with write_atomic(env.path / env.requirements_txt, 'w') as f:
            f.write(requirements)
            f.flush()
            env.pip('install', '--only-binary=:all:', f'--requirement={f.name}',
                    *pip_args, check=True, stdout=self.out, stderr=self.out)


MAX_WPATH = 32768
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010

own_process_re = re.compile(r'(?i).*\\(?:py|python[0-9.]*)\.exe$')


def maybe_wait_on_exit(stderr):
    if sys.platform != 'win32': return
    import ctypes.wintypes
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    DWORD = ctypes.wintypes.DWORD

    # Check if there are any other console processes besides our own
    # (python.exe and potentially py.exe).
    pids = (DWORD * 2)()
    count = kernel32.GetConsoleProcessList(pids, len(pids))
    if count > 2: return

    # There is at least one process besides python.exe. Check if it's py.exe or
    # the shell.
    psapi = ctypes.WinDLL('psapi', use_last_error=True)
    path = ctypes.create_unicode_buffer(MAX_WPATH)
    for pid in pids:
        h = kernel32.OpenProcess(
            DWORD(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ),
            False, pid)
        if h == 0: continue
        try:
            size = psapi.GetModuleFileNameExW(h, None, path, MAX_WPATH)
            if size == 0: continue
            if own_process_re.match(path[:size]) is not None: count -= 1
        finally:
            kernel32.CloseHandle(h)
    if count > 0: return
    stderr.write("\nPress ENTER to exit.")
    stderr.flush()
    input()


if __name__ == '__main__':
    main(argv=sys.argv, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr,
         base=pathlib.Path(sys.argv[0]).parent.resolve().parent)
