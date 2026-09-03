# Copyright 2026 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import collections
import contextlib
import functools
import os
import pathlib
import re

from docutils import nodes, utils
from sphinx._cli.util import colour
from sphinx.environment import collectors
from sphinx.util import logging

from .. import ext, util

_log = logging.getLogger(__name__)


def setup(app):
    app.add_event('tdoc-check-file-for-fixes')
    app.connect('builder-inited', FixCollector.init, priority=0)
    app.add_env_collector(FixCollector)
    app.connect('build-finished', check_files_for_fixes)
    app.connect('build-finished', store, priority=999)
    app.connect('tdoc-check-file-for-fixes', _fix_bad_filename)

    return {
        'version': ext.__version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


def add(env, name, *, docname=None, location=None):
    if docname is None: docname = env.docname
    if location is None and docname is not None:
        location = (ext.repo_relative(env, env.doc2path(docname)), None)
    elif isinstance(location, tuple):
        src, line = location
        location = (ext.repo_relative(env, src), line)
    elif isinstance(location, (str, os.PathLike)):
        location = (ext.repo_relative(env, location), None)
    elif isinstance(location, nodes.Node):
        src, line = utils.get_source_line(location)
        if src: location = (ext.repo_relative(env, src), line)
    ls = env.tdoc_fixes[docname][name]
    if location is not None: ls.add(location)


class SourceFile:
    def __init__(self, env, path):
        self.env, self.path = env, path
        self.rel_path = path.relative_to(env.srcdir)

    @functools.cached_property
    def text(self): return self.path.read_text('utf-8')

    @functools.cached_property
    def bytes(self): return self.path.read_bytes()

    def add_fix(self, name, line=None):
        add(self.env, name, location=(self.path, line))


def check_files_for_fixes(app, exc):
    if not app.events.listeners.get('tdoc-check-file-for-fixes'): return
    def on_error(e): raise e
    for parent, dirs, files in app.srcdir.walk(on_error=on_error):
        for f in files:
            app.emit('tdoc-check-file-for-fixes',
                     SourceFile(app.env, parent / f))


class FixCollector(collectors.EnvironmentCollector):
    @staticmethod
    def init(app):
        if not hasattr(app.env, 'tdoc_fixes'):
            # {docname: {name: {(path, line)}}}
            app.env.tdoc_fixes = collections.defaultdict(ext.dict_of_set)

    def clear_doc(self, app, env, docname):
        app.env.tdoc_fixes.pop(docname, None)

    def merge_other(self, app, env, docnames, other):
        for docname in docnames:
            if (fs := other.tdoc_fixes.get(docname)) is not None:
                env.tdoc_fixes[docname] = fs
            else:
                env.tdoc_fixes.pop(docname, None)

    def process_doc(self, app, doctree): pass


def store(app, exc):
    # Merge the per-document fix dicts.
    data = ext.dict_of_set()
    for docname, fixes in app.env.tdoc_fixes.items():
        for name, locations in fixes.items():
            data[name].update(locations)

    # Write the merged fixes to the build directory.
    (app.outdir.parent / util.fixes).write_text(util.to_json(data), 'utf-8')

    # List the fixes.
    if not data: return
    _log.info(colour.bold("Fixes required:"))
    for name, locs in sorted(data.items()):
        name = colour.yellow(name)
        if not locs:
            _log.info(f"  {name}")
            continue
        _log.info(f"  {name} ({len(locs)} locations)")
        for src, line in sorted(locs):
            _log.info(f"    {src}{f":{line}" if line else ""}")


# https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file#naming-conventions
_bad_filename_re = re.compile(r'[\x00-\x20"*/:<>?\\|\x7f-\U0010ffff]')


def _fix_bad_filename(app, file):
    for part in str(file.rel_path).split(os.sep):
        if not _bad_filename_re.search(part): continue
        file.add_fix('bad-filename')
        break
