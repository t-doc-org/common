#!/usr/bin/env python
# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import contextlib
import contextvars
import itertools
import os
import pathlib
import re
import subprocess
import shutil
import sys
import sysconfig
import time
import venv

# TODO: Allow forcing the creation of a new venv

idle_days = 3
keep_live_envs = 2

executable_re = re.compile(r'^run-([^@]+)@(.+)\.py$')


def main(argv, stdin, stdout, stderr):
    # Determine the command to run and the requirements for running it.
    executable = pathlib.Path(argv[0]).name
    if (m := executable_re.fullmatch(executable)) is not None:
        command, requirements = m.group(1, 2)
        if reqs := os.environ.get('RUN_REQUIREMENTS'):
            requirements = reqs
    elif len(argv) >= 3:
        command, requirements = argv[1:3]
        argv = argv[:1] + argv[3:]
    else:
        stderr.write("Not enough arguments\n\n"
                     f"Usage: {executable} COMMAND REQUIREMENTS [ARG ...]\n")
        return 1

    base = pathlib.Path.cwd()
    builder = EnvBuilder(base, stderr)

    # Find the most recent venv with the right requirements, or create one.
    envs = builder.find()
    if not (es := envs.setdefault(requirements, [])):
        stderr.write("Creating venv...\n")
        env = builder.new()
        env.create(requirements)
        stderr.write("\n")
    else:
        env = es[0]

    # Garbage-collect old venvs.
    limit = time.time_ns() - idle_days * 24 * 3600 * 1_000_000_000
    for reqs, es in envs.items():
        keep = keep_live_envs if is_live(reqs) else 0
        for e in itertools.islice(es, keep):
            if e is not env and e.last_used < limit: e.remove()

    # Check for upgrades, and upgrade if requested.
    if env.want_upgrade():
        stderr.write("Upgrading...\n")
        new = builder.new()
        try:
            new.create(requirements)
            env = new
        except Exception:
            stderr.write("\nUpgrade failed. Continuing with current version.\n")
        stderr.write("\n")

    # Run the command.
    env.touch()
    bin, ext = env.sysinfo
    return subprocess.run([pathlib.Path(bin) / f'{command}{ext}'] + argv[1:],
                          cwd=base).returncode


class lazy:
    def __init__(self, fn):
        self.fn = fn

    def __get__(self, instance, owner=None):
        if instance is None: return self
        res = self.fn(instance)
        setattr(instance, self.fn.__name__, res)
        return res


live_re = re.compile(r'(?i)^([A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9])$')

def is_live(requirements):
    return live_re.fullmatch(requirements or '') is not None


class Env:
    prefix = 'venv'
    requirements_txt = 'requirements.txt'
    upgrade_txt = 'upgrade.txt'

    env = contextvars.ContextVar('env')

    def __init__(self, path, builder):
        self.path, self.builder = path, builder

    @lazy
    def last_used(self):
        try:
            return (self.path / self.requirements_txt).stat(
                follow_symlinks=False).st_mtime_ns
        except OSError:
            return 0

    @lazy
    def requirements(self):
        try:
            return (self.path / self.requirements_txt).read_text()
        except OSError:
            return None

    @lazy
    def sysinfo(self):
        vars = {'base': self.path, 'platbase': self.path,
                'installed_base': self.path, 'intsalled_platbase': self.path}
        return (sysconfig.get_path('scripts', scheme='venv', vars=vars),
                sysconfig.get_config_vars().get('EXE', ''))

    def want_upgrade(self):
        if not is_live(self.requirements): return False
        try:
            upgrade = (self.path / self.upgrade_txt).read_text()
            cur, new = upgrade.split(' ', 1)[:2]
        except Exception:
            return False
        self.builder.out.write(f"""\
A t-doc upgrade is available: {self.requirements} {cur} => {new}
Would you like to upgrade (y/n)? """)
        resp = input().lower()
        self.builder.out.write("\n")
        return resp in ('y', 'yes', 'o', 'oui', 'j', 'ja')

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

    def touch(self):
        with contextlib.suppress(OSError):
            os.utime(self.path / self.requirements_txt, follow_symlinks=False)
            with contextlib.suppress(AttributeError): del self.last_used

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
        envs = {}
        for path in self.root.glob(f'{Env.prefix}-*'):
            env = Env(path, self)
            envs.setdefault(env.requirements, []).append(env)
        for reqs, es in envs.items():
            es.sort(key=lambda e: e.last_used, reverse=True)
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


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv, sys.stdin, sys.stdout, sys.stderr))
    except SystemExit:
        raise
    except BaseException as e:
        if '--debug' in sys.argv: raise
        if not isinstance(e, KeyboardInterrupt):
            sys.stderr.write(f'\n{e}\n')
        sys.exit(1)
