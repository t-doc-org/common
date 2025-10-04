# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import os
import pathlib
import re

from sphinx import jinja2glue
from sphinx.util import fileutil

_asset_file_patches = []

def asset_file(dest):
    def wrapper(fn): _asset_file_patches.append((dest.replace('/', os.sep), fn))
    return wrapper


def _copy_asset_file(source, destination, context=None, renderer=None, *,
                     force=False):
    orig_copy_asset_file(source, destination, context, renderer, force=force)
    source = pathlib.Path(source)
    if not source.exists(): return
    destination = pathlib.Path(destination)
    if destination.is_dir(): destination /= source.name
    dstr = str(destination)
    for dest, fn in _asset_file_patches:
        if dstr.endswith(dest):
            old = destination.read_text(encoding='utf-8')
            new = fn(old)
            if new != old: destination.write_text(new, encoding='utf-8')

orig_copy_asset_file = fileutil.copy_asset_file
fileutil.copy_asset_file = _copy_asset_file


_template_patches = {}

def template(name):
    def wrapper(fn): _template_patches.setdefault(name, []).append(fn)
    return wrapper


def _get_source(self, env, template):
    contents, filename, uptodate = \
        SphinxFileSystemLoader_get_source(self, env, template)
    for fn in _template_patches.get(template, ()):
        contents = fn(contents, env)
    return contents, filename, uptodate

SphinxFileSystemLoader_get_source = jinja2glue.SphinxFileSystemLoader.get_source
jinja2glue.SphinxFileSystemLoader.get_source = _get_source


def sub(data, pattern, repl, count=0, flags=0):
    new = re.sub(pattern, repl, data, count, flags)
    if new == data: raise Exception(f"Patching failed: {pattern}")
    return new
