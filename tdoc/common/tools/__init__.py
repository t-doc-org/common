# Copyright 2026 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import contextlib
import pathlib
import threading
import tomllib

from . import deps
from .. import __project__, __version__, console


@console.main
def main(argv, stdin, stdout, stderr):
    """Run the command."""
    threading.current_thread().name = 'main'

    parser = console.get_arg_parser(stdin, stdout, stderr)(
        prog=pathlib.Path(argv[0]).name,
        description="Run t-doc developer tools.")
    root = parser.add_subparsers(title='Sub-commands')
    root.required = True

    deps.add_commands(root, common_options)

    p = root.add_parser('version', help="Display version information.")
    p.set_defaults(handler=cmd_version)
    common_options(p)

    opts = parser.parse_args(argv[1:])
    find_common(opts)
    return opts.handler(opts)


def common_options(parser):
    arg = parser.add_argument_group("Common options").add_argument
    arg('--color', dest='color', choices=['auto', 'false', 'true'],
        default='auto',
        help="Control the use of colors in output (default: %(default)s).")
    arg('--debug', action='store_true', dest='debug',
        help="Enable debug functionality.")


def find_common(opts):
    opts.common = pathlib.Path(__file__).parent.resolve().parent.parent.parent
    with contextlib.suppress(Exception):
        with (opts.common / 'pyproject.toml').open('rb') as f:
            data = tomllib.load(f)
        if data['project']['name'] == __project__: return
    raise Exception(f"This isn't an editable install of {__project__}; "
                    "tdoc-dev is unavailable.")


def cmd_version(opts):
    opts.stdout.write(f"{__project__}-{__version__}\n")
