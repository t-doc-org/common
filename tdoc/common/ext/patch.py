# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import functools
import os
import pathlib
import re

from docutils import statemachine
from myst_parser import mocking
from sphinx import jinja2glue
from sphinx.util import fileutil


def patch(obj, name):
    """Monkey-patch a function on an object."""
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs): return fn(orig, *args, **kwargs)
        orig = getattr(obj, name)
        setattr(obj, name, wrapper)
        return wrapper
    return deco


# BUG(myst-parser): MockState.parse_directive_block() [myst_parser] returns the
# content as a StringList, whereas Body.parse_directive_block() [docutils]
# returns a list. The StringList is constructed with source=content.source,
# which is a bound method and clearly wrong. Patch the method to unwrap the
# list.
@patch(mocking.MockState, 'parse_directive_block')
def _parse_directive_block(orig, self, /, *args, **kwargs):
    arguments, options, content, content_offset = orig(self, *args, **kwargs)
    if isinstance(content, statemachine.StringList): content = content.data
    return arguments, options, content, content_offset


_asset_file_patches = []

def asset_file(dest):
    """Patch an asset file written to the given destination."""
    def deco(fn): _asset_file_patches.append((dest.replace('/', os.sep), fn))
    return deco


@patch(fileutil, 'copy_asset_file')
def _copy_asset_file(orig, /, source, destination, *args, **kwargs):
    orig(source, destination, *args, **kwargs)
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


_template_patches = {}

def template(name):
    """Patch the template with the given name."""
    def deco(fn): _template_patches.setdefault(name, []).append(fn)
    return deco


@patch(jinja2glue.SphinxFileSystemLoader, 'get_source')
def _get_source(orig, self, /, env, template):
    contents, filename, uptodate = orig(self, env, template)
    for fn in _template_patches.get(template, ()):
        contents = fn(contents, env)
    return contents, filename, uptodate


def sub(data, pattern, repl, count=0, flags=0):
    """Substitute a regexp, and check that it made a difference."""
    new = re.sub(pattern, repl, data, count, flags)
    if new == data: raise Exception(f"Patching failed: {pattern}")
    return new
