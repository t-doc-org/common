# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import os
import pathlib
import re

from sphinx.util import fileutil


def _copy_asset_file(source, destination, context=None, renderer=None, *,
                     force=False):
    orig_copy_asset_file(source, destination, context, renderer, force=force)
    source = pathlib.Path(source)
    if not source.exists(): return
    destination = pathlib.Path(destination)
    if destination.is_dir(): destination /= source.name
    dstr = str(destination)
    for dest, fn in asset_file_patches:
        if dstr.endswith(dest):
            old = destination.read_text(encoding='utf-8')
            new = fn(old)
            if new != old: destination.write_text(new, encoding='utf-8')

orig_copy_asset_file = fileutil.copy_asset_file
fileutil.copy_asset_file = _copy_asset_file


asset_file_patches = []

def asset_file(dest):
    def wrapper(fn):
        asset_file_patches.append((dest.replace('/', os.sep), fn))
    return wrapper


def overwrite(data, pattern, *fills):
    def replace(m):
        mstart, mend = m.span(0)
        if m.re.groups == 0:
            f = fills[0]
            return (f * ((mend - mstart + len(f) - 1) // len(f)))[:mend
                                                                   - mstart]
        res = ''
        prev_end = mstart
        for i in range(m.re.groups):
            start, end = m.span(1 + i)
            if start == end == -1: continue
            res += data[prev_end: start]
            prev_end = end
            f = fills[i]
            res += (f * ((end - start + len(f) - 1) // len(f)))[:end - start]
        if prev_end != mend: res += data[prev_end: mend]
        return res
    new = re.sub(pattern, replace, data)
    if new == data: raise Exception(f"Patching failed: {pattern}")
    return new
