#!/usr/bin/env python
# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import contextlib
import pathlib
import subprocess
import shutil
import sys
import sysconfig
import venv

package = 't-doc-common'
upgrade_marker = 'tdoc.upgrade'


def main(argv, stdin, stdout, stderr):
    base = pathlib.Path(argv[0]).resolve().parent
    vdir = base / '_venv'

    # Create the venv if it doesn't exist.
    builder = EnvBuilder(stderr)
    if not vdir.exists():
        stderr.write("Creating venv...\n")
        builder.create(vdir)
        stderr.write("\n")

    # Upgrade if available and if requested by the user.
    check_upgrade(base, vdir, builder)

    # Run the command.
    bin, ext = get_sysinfo(vdir)
    subprocess.run([pathlib.Path(bin) / f'tdoc{ext}'] + argv[1:], check=True,
                   cwd=base)


class EnvBuilder(venv.EnvBuilder):
    def __init__(self, out):
        super().__init__(with_pip=True)
        self.out = out

    def post_setup(self, ctx):
        super().post_setup(ctx)
        self.pip(ctx, 'install', package)

    def pip(self, ctx, *args):
        subprocess.run((ctx.env_exec_cmd, '-P', '-m', 'pip') + args, check=True,
                       stdin=subprocess.DEVNULL, stdout=self.out,
                       stderr=self.out)


def get_sysinfo(vdir):
    vars = {'base': vdir, 'platbase': vdir,
            'installed_base': vdir, 'intsalled_platbase': vdir}
    return (sysconfig.get_path('scripts', scheme='venv', vars=vars),
            sysconfig.get_config_vars().get('EXE', ''))


def check_upgrade(base, vdir, builder):
    try:
        cur, new = (vdir / upgrade_marker).read_text().strip().split(' ')[:2]
    except Exception:
        return
    if new == cur: return
    out = builder.out
    out.write("A t-doc upgrade is available: %s %s => %s\n"
              "Would you like to upgrade (y/n)? " % (package, cur, new))
    if input().lower() in ('y', 'yes', 'o', 'oui', 'j', 'ja'):
        out.write("\nUpgrading...\n")
        tmp = vdir.with_name(vdir.name + '-old')
        restore = False
        try:
            vdir.rename(tmp)
            restore = True
            builder.create(vdir)
            rmtree(tmp, base, out)
        except BaseException as e:
            if restore:
                rmtree(vdir, base, out)
                tmp.rename(vdir)
            if not isinstance(e, Exception): raise
    out.write("\n")


def rmtree(path, base, err):
    if path.relative_to(base) == pathlib.Path():
        raise Exception(f"Not removing {path}")
    def on_error(fn, path, e):
        err.write(f"Removal: {fn}: {path}: {e}\n")
    shutil.rmtree(path, onexc=on_error)


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv, sys.stdin, sys.stdout, sys.stderr))
    except SystemExit:
        raise
    except BaseException as e:
        if '--debug' in sys.argv:
            raise
        if not isinstance(e, KeyboardInterrupt):
            sys.stderr.write(f'\n{e}\n')
        sys.exit(1)
