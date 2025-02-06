# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import argparse
import functools
import os
import re
import sys

from . import __project__

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


_ansi_seqs = {
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
_nop_seqs = {k: '' for k in _ansi_seqs}


class AnsiStream:
    """Wrapper around an output stream exposing ANSI sequences as attributes."""
    def __init__(self, stream, color=None):
        self.__stream = stream
        if color is None: color = want_colors(stream)
        self.__tags = _ansi_seqs if color else _nop_seqs

    def __getattr__(self, name):
        try:
            return self.__tags[name]
        except KeyError:
            return getattr(self.__stream, name)


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
        except KeyboardInterrupt:
            sys.exit(1)
        except BaseException as e:
            if '--debug' in argv: raise
            stderr.write(f'\n{e}\n')
            sys.exit(1)
    return wrapper
