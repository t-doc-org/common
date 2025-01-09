# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import argparse
import contextlib
import functools
import os
import pathlib
import re
import shutil
import sys

from . import __project__

_colors = True
try:
    if sys.platform == 'win32':
        import colorama
        colorama.just_fix_windows_console()
except ImportError:
    _colors = False

# This module is imported by tdocv.py, so non-stdlib dependencies should be kept
# to a minimum.

def want_colors(stdout):
    if not _colors: return False
    if 'NO_COLOR' in os.environ: return False
    if not hasattr(stdout, 'isatty') or not stdout.isatty(): return False
    return True


_tag_re = re.compile(r'@\{([A-Z_+]+)\}')
_ansi_tags = {
    'NORM': '\x1b[0m',
    'BOLD': '\x1b[1m',

    'BLACK': '\x1b[30m',
    'RED': '\x1b[31m',
    'GREEN': '\x1b[32m',
    'YELLOW': '\x1b[33m',
    'BLUE': '\x1b[34m',
    'MAGENTA': '\x1b[35m',
    'CYAN': '\x1b[36m',
    'WHITE': '\x1b[37m',

    'LBLACK': '\x1b[90m',
    'LRED': '\x1b[91m',
    'LGREEN': '\x1b[92m',
    'LYELLOW': '\x1b[93m',
    'LBLUE': '\x1b[94m',
    'LMAGENTA': '\x1b[95m',
    'LCYAN': '\x1b[96m',
    'LWHITE': '\x1b[97m',
}


def no_ansi(s):
    return _tag_re.sub('', s)


def ansi(s):
    def replace(m):
        return _ansi_tags.get(m.group(1), m.group(0))
    return _tag_re.sub(replace, s)


def get_arg_parser(stderr):
    """Get an ArgumentParser class printing errors to the given stream."""
    class Parser(argparse.ArgumentParser):
        def _print_message(self, message, file=None):
            super()._print_message(message, stderr)
    return Parser


def main(fn):
    """Decorate fn as a main() function."""
    @functools.wraps(fn)
    def wrapper(argv=None, stdin=None, stdout=None, stderr=None):
        if argv is None: argv = sys.argv
        if stdin is None: stdin = sys.stdin
        if stdout is None: stdout = sys.stdout
        if stderr is None: stderr = sys.stderr
        try:
            sys.exit(fn(argv, stdin, stdout, stderr))
        except SystemExit:
            raise
        except BaseException as e:
            stderr.write('\n')
            if '--debug' in argv:
                raise
            stderr.write(f'{e}\n')
            sys.exit(1)
    return wrapper


def rmtree(path, base, err):
    if path.relative_to(base) == pathlib.Path():
        raise Exception(f"Not removing {path}")
    def on_error(fn, path, e):
        err.write(f"Removal: {fn}: {path}: {e}\n")
    shutil.rmtree(path, onexc=on_error)


_upgrade_marker = 'tdoc.upgrade'


def write_upgrade_marker(cur_version, new_version):
    if sys.prefix == sys.base_prefix: return  # Not running in a venv
    marker = pathlib.Path(sys.prefix) / _upgrade_marker
    with contextlib.suppress(Exception):
        marker.write_text(f'{__project__} {cur_version} {new_version}')


def check_upgrade(base, venv, builder):
    try:
        marker = venv / _upgrade_marker
        pkg, cur, new = marker.read_text().strip().split(' ')[:3]
    except Exception:
        return
    if new == cur: return
    out = builder.stderr
    color = ansi if want_colors(out) else no_ansi
    out.write(color("@{LYELLOW}A t-doc upgrade is available:@{NORM} "
                    "%s @{CYAN}%s@{NORM} => @{CYAN}%s@{NORM}\n"
                    "@{LWHITE}Would you like to upgrade?@{NORM} ")
              % (pkg, cur, new))
    if input().lower() in ('y', 'yes', 'o', 'oui', 'j', 'ja'):
        out.write(color("\n@{LMAGENTA}Upgrading...@{NORM}\n"))
        tmp = venv.with_name(venv.name + '-old')
        restore = False
        try:
            venv.rename(tmp)
            restore = True
            builder.create(venv)
            rmtree(tmp, base, out)
        except BaseException as e:
            if restore:
                rmtree(venv, base, out)
                tmp.rename(venv)
            if not isinstance(e, Exception): raise
    out.write("\n")
