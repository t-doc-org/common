#!/usr/bin/env python
# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import contextlib
import pathlib
import subprocess
import sys
import venv

# TODO: Support running a specific version


class EnvBuilder(venv.EnvBuilder):
    def __init__(self, stderr):
        super().__init__(with_pip=True)
        self.stderr = stderr

    def post_setup(self, ctx):
        super().post_setup(ctx)
        self.pip(ctx, 'install', 't-doc-common')

    def pip(self, ctx, *args, json_output=False):
        subprocess.run((ctx.env_exec_cmd, '-m', 'pip') + args, check=True,
                       stdin=subprocess.DEVNULL, stdout=self.stderr,
                       stderr=self.stderr)


def main(argv, stdin, stdout, stderr):
    base = pathlib.Path(argv[0]).parent.resolve()
    vdir = base / '_venv'

    # Create the venv if it doesn't exist.
    builder = EnvBuilder(stderr)
    if not vdir.exists():
        stderr.write("Creating venv...\n")
        builder.create(vdir)
        stderr.write("\n")

    # Import from modules installed in the venv.
    for lib in (vdir / 'lib').glob('python*.*'):
        sys.path.append(lib / 'site-packages')
        with contextlib.suppress(ImportError):
            from tdoc.common import util
            break
    else:
        raise Exception("Failed to import tdoc.common.util")

    # Upgrade if available and requested by the user.
    util.check_upgrade(base, vdir, builder)

    # Run the command.
    subprocess.run([vdir / 'bin' / 'tdoc'] + argv[1:], check=True, cwd=base)


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
