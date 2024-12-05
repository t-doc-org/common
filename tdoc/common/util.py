# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import argparse
import functools
import os
import re
import sys


_colors = True
try:
    if sys.platform == 'win32':
        import colorama
        colorama.just_fix_windows_console()
except ImportError:
    _colors = False


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
