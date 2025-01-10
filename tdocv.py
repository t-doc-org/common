#!/usr/bin/env python
# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import contextlib
import contextvars
import pathlib
import subprocess
import shutil
import sys
import sysconfig
import time
import venv

# TODO: Use a naming convention to determine (package, cmd)
# TODO: Allow forcing requirements (file? env var?)

package = 't-doc-common'
command = 'tdoc'
keep_envs = 2
keep_envs_days = 3


def main(argv, stdin, stdout, stderr):
    base = pathlib.Path.cwd()
    builder = EnvBuilder(base, stderr)

    # Find the most recent venv. Create one if none exists.
    envs = builder.find()
    if not any(e.valid for e in envs):
        stderr.write("Creating venv...\n")
        env = builder.new()
        env.create()
        envs.insert(0, env)
        stderr.write("\n")
    for env in envs:
        if env.valid: break

    # Garbage-collect old venvs.
    limit = time.time_ns() - keep_envs_days * 24 * 3600 * 1_000_000_000
    count = 0
    for e in envs:
        if e.valid:
            count += 1
            if count <= keep_envs: continue
        if e.time >= limit: continue
        e.remove()

    # Upgrade if available and if requested by the user.
    if (reqs := env.check_upgrade()) is not None:
        stderr.write("Upgrading...\n")
        new = builder.new()
        try:
            new.create(reqs)
            env = new
        except Exception:
            stderr.write("\nUpgrade failed. Continuing with current version.\n")
        stderr.write("\n")

    # Run the command.
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


class Env:
    prefix = 'venv'
    requirements_txt = 'requirements.txt'
    upgrade_txt = 'upgrade.txt'

    env = contextvars.ContextVar('env')

    def __init__(self, path, builder):
        self.path, self.builder = path, builder

    @lazy
    def time(self):
        return int(self.path.stem.rsplit('-', 1)[-1], 16)

    @lazy
    def valid(self):
        with contextlib.suppress(IOError):
            (self.path / self.requirements_txt).read_text()
            return True
        return False

    @lazy
    def sysinfo(self):
        vars = {'base': self.path, 'platbase': self.path,
                'installed_base': self.path, 'intsalled_platbase': self.path}
        return (sysconfig.get_path('scripts', scheme='venv', vars=vars),
                sysconfig.get_config_vars().get('EXE', ''))

    def check_upgrade(self):
        try:
            reqs = (self.path / self.upgrade_txt).read_text()
        except Exception:
            return
        self.builder.out.write(f"""\
A t-doc upgrade is available:
{''.join(f'  {line}\n' for line in reqs.splitlines())}\
Would you like to upgrade (y/n)? """)
        resp = input().lower()
        self.builder.out.write("\n")
        if resp in ('y', 'yes', 'o', 'oui', 'j', 'ja'): return reqs

    def create(self, reqs=None):
        if reqs is None: reqs = f'{package}\n'
        self.reqs = reqs
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
    def requirements():
        self = Env.env.get()
        reqs = self.path / f'{self.requirements_txt}.tmp'
        reqs.write_text(self.reqs)
        yield reqs
        reqs.rename(self.path / self.requirements_txt)

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
        envs.sort(key=lambda e: e.time, reverse=True)
        return envs

    def new(self):
        return Env(self.root / f'{Env.prefix}-{time.time_ns():024x}', self)

    def post_setup(self, ctx):
        super().post_setup(ctx)
        with Env.requirements() as reqs:
            self.pip(ctx, 'install', '--only-binary=:all:',
                     '--requirement', reqs)

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
