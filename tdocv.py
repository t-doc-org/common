#!/usr/bin/env python
# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import contextlib
import pathlib
import subprocess
import sys
import sysconfig
import venv


class EnvBuilder(venv.EnvBuilder):
    def __init__(self, out):
        super().__init__(with_pip=True)
        self.out = out

    def post_setup(self, ctx):
        super().post_setup(ctx)
        self.pip(ctx, 'install', 't-doc-common')

    def pip(self, ctx, *args):
        subprocess.run((ctx.env_exec_cmd, '-m', 'pip') + args, check=True,
                       stdin=subprocess.DEVNULL, stdout=self.out,
                       stderr=self.out)


def get_sysinfo(vdir, py_version):
    vars = {
        'base': vdir, 'platbase': vdir,
        'installed_base': vdir, 'intsalled_platbase': vdir,
        'py_version_short': py_version,
    }
    return (sysconfig.get_path('purelib', scheme='venv', vars=vars),
            sysconfig.get_path('scripts', scheme='venv', vars=vars),
            sysconfig.get_config_vars().get('EXE', ''))


def main(argv, stdin, stdout, stderr):
    base = pathlib.Path(argv[0]).resolve().parent
    vdir = base / '_venv'

    # Create the venv if it doesn't exist.
    builder = EnvBuilder(stderr)
    if not vdir.exists():
        stderr.write("Creating venv...\n")
        builder.create(vdir)
        stderr.write("\n")

    # Import from modules installed in the venv.
    lib, bin, ext = get_sysinfo(vdir, '*.*')
    for path in base.glob(str(pathlib.Path(lib).relative_to(base))):
        try:
            old = sys.path[:]
            sys.path.insert(0, str(path))
            from tdoc.common import util
            break
        except ImportError:
            sys.path = old
    else:
        raise Exception("Failed to import tdoc.common.util")

    # Upgrade if available and requested by the user.
    util.check_upgrade(base, vdir, builder)

    # Run the command.
    subprocess.run([pathlib.Path(bin) / f'tdoc{ext}'] + argv[1:], check=True,
                   cwd=base)


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
