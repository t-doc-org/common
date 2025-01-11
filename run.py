#!/usr/bin/env python
# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import contextlib
import contextvars
import os
import pathlib
import re
import subprocess
import shutil
import sys
import sysconfig
import time
import venv

# Set this variable to temporarily install a specific version.
VERSION = ''

package = 't-doc-common'
command = 'tdoc'
default_args = ['serve']


def main(argv, stdin, stdout, stderr):
    base = pathlib.Path(argv[0]).resolve().parent
    version = os.environ.get('TDOC_VERSION', VERSION)
    requirements = f'{package}=={version}' if version else package

    # Find the most recent matching venv, or create one if there is none.
    builder = EnvBuilder(base, stderr)
    envs = builder.find()
    matching = [e for e in envs if e.requirements == requirements]
    if not matching:
        stderr.write("Installing...\n")
        env = builder.new()
        env.create(requirements)
        stderr.write("\n")
    else:
        env = matching[0]

    # Remove old venvs.
    for e in envs:
        if e is not env: e.remove()

    # Check for upgrades, and upgrade if requested.
    cur, new = env.upgrade
    if new is not None:
        stderr.write(f"""\
A t-doc upgrade is available: {package} {cur} => {new}
Release notes: <https://t-doc.org/common/release_notes.html\
#release-{new.replace('.', '-')}>
""")
        if VERSION:
            stderr.write("Unset VERSION in run.py and restart the server to "
                         "upgrade.\n\n")
        elif version:
            stderr.write("Unset TDOC_VERSION and restart the server to "
                         "upgrade.\n\n")
        else:
            stderr.write("Would you like to apply the upgrade (y/n)? ")
            resp = input().lower()
            stderr.write("\n")
            if resp in ('y', 'yes', 'o', 'oui', 'j', 'ja'):
                stderr.write("Upgrading...\n")
                new_env = builder.new()
                try:
                    new_env.create(requirements)
                    env = new_env
                except Exception:
                    stderr.write("\nThe upgrade failed. Continuing with the "
                                 "current version.\n")
                stderr.write("\n")

    # Run the command.
    bin, ext = env.sysinfo
    args = argv[1:] if len(argv) > 1 else default_args
    return subprocess.run([pathlib.Path(bin) / f'{command}{ext}'] + args,
                          cwd=base).returncode


class lazy:
    def __init__(self, fn):
        self.fn = fn

    def __get__(self, instance, owner=None):
        if instance is None: return self
        res = self.fn(instance)
        setattr(instance, self.fn.__name__, res)
        return res


class Env:
    prefix = 'venv'
    requirements_txt = 'requirements.txt'
    upgrade_txt = 'upgrade.txt'

    env = contextvars.ContextVar('env')

    def __init__(self, path, builder):
        self.path, self.builder = path, builder

    @lazy
    def requirements(self):
        try:
            return (self.path / self.requirements_txt).read_text()
        except OSError:
            return None

    @lazy
    def upgrade(self):
        try:
            upgrade = (self.path / self.upgrade_txt).read_text()
            return upgrade.split(' ', 1)[:2]
        except Exception:
            return None, None

    @lazy
    def sysinfo(self):
        vars = {'base': self.path, 'platbase': self.path,
                'installed_base': self.path, 'intsalled_platbase': self.path}
        return (sysconfig.get_path('scripts', scheme='venv', vars=vars),
                sysconfig.get_config_vars().get('EXE', ''))

    def create(self, reqs):
        self.requirements = reqs
        self.builder.root.mkdir(exist_ok=True)
        token = self.env.set(self)
        try:
            self.builder.create(self.path)
        except BaseException:
            self.remove()
            raise
        finally:
            self.env.reset(token)

    @contextlib.contextmanager
    @staticmethod
    def create_requirements():
        self = Env.env.get()
        rpath = self.path / f'{self.requirements_txt}.tmp'
        rpath.write_text(self.requirements)
        yield rpath
        rpath.rename(self.path / self.requirements_txt)

    def remove(self):
        try:
            if self.path.relative_to(self.builder.root) == pathlib.Path():
                raise Exception(f"{self.path}: Not below venv root")
            def on_error(fn, path, e):
                self.builder.out.write(f"ERROR: {fn}: {path}: {e}\n")
            shutil.rmtree(self.path, onexc=on_error)
        except Exception as e:
            self.builder.out.write(f"ERROR: {e}")


class EnvBuilder(venv.EnvBuilder):
    venv_root = '_venv'

    def __init__(self, base, out):
        super().__init__(with_pip=True)
        self.root = base / self.venv_root
        self.out = out

    def find(self):
        envs = [Env(path, self) for path in self.root.glob(f'{Env.prefix}-*')]
        envs.sort(key=lambda e: e.path, reverse=True)
        return envs

    def new(self):
        return Env(self.root / f'{Env.prefix}-{time.time_ns():024x}', self)

    def post_setup(self, ctx):
        super().post_setup(ctx)
        with Env.create_requirements() as rpath:
            self.pip(ctx, 'install', '--only-binary=:all:',
                     '--requirement', rpath)

    def pip(self, ctx, *args):
        subprocess.run((ctx.env_exec_cmd, '-P', '-m', 'pip',
                        '--require-virtualenv') + args,
                       check=True, stdin=subprocess.DEVNULL, stdout=self.out,
                       stderr=self.out)


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
    input()


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv, sys.stdin, sys.stdout, sys.stderr))
    except SystemExit:
        raise
    except BaseException as e:
        if '--debug' in sys.argv: raise
        if not isinstance(e, KeyboardInterrupt):
            sys.stderr.write(f'\n{e}\n')
            maybe_wait_on_exit(sys.stderr)
        sys.exit(1)
