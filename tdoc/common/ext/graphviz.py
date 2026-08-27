# Copyright 2026 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import os
import pathlib
import sys

from sphinx.ext import graphviz
from sphinx.util import logging

from .. import ext

if sys.platform == 'win32': import winreg

_log = logging.getLogger(__name__)


def setup(app):
    if sys.platform == 'win32':
        app.connect('config-inited', find_graphviz_binaries)
    return {
        'version': ext.__version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


reg_key = 'SOFTWARE\\Graphviz\\Graphviz'


def find_graphviz_binaries(app, config):
    # Find where Graphviz is installed, and add its "bin" directory to $PATH.
    for flag in [winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY]:
        for k in [winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE]:
            try:
                with winreg.OpenKey(k, reg_key,
                                    access=winreg.KEY_READ | flag) as key:
                    v, t = winreg.QueryValueEx(key, '')
            except FileNotFoundError:
                continue
            if t == winreg.REG_EXPAND_SZ:
                v = winreg.ExpandEnvironmnentStrings(v)
            elif t != winreg.REG_SZ:
                continue
            p = pathlib.Path(v) / 'bin'
            if not (p / 'dot.exe').exists(): continue
            os.environ['PATH'] += f'{os.pathsep}{p}'
            return
