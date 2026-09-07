# Copyright 2026 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import collections
import contextlib
import functools
import math
import os
import pathlib
import re

from docutils import nodes, utils
from sphinx._cli.util import colour
from sphinx.environment import collectors
from sphinx.util import build_phase, display, logging

from .. import ext, fixes, util

_log = logging.getLogger(__name__)


def setup(app):
    app.add_event('tdoc-list-sources')
    app.connect('builder-inited', FixCollector.init, priority=0)
    app.add_env_collector(FixCollector)
    app.connect('builder-inited', check_sources_for_fixes)
    app.connect('build-finished', store, priority=999)
    app.connect('tdoc-list-sources', _fix_bad_filename)
    return ext.setup_result


def add(env, name, *, location=None):
    if env.app.builder.phase >= build_phase.BuildPhase.RESOLVING:
        raise Exception(f"Adding fix '{name}' in or after phase RESOLVING")
    if location is None and env.docname:
        location = (ext.repo_relative(env, env.doc2path(env.docname)), None)
    elif isinstance(location, tuple):
        src, line = location
        location = (ext.repo_relative(env, src), line)
    elif isinstance(location, (str, os.PathLike)):
        location = (ext.repo_relative(env, location), None)
    elif isinstance(location, nodes.Node):
        src, line = utils.get_source_line(location)
        if src: location = (ext.repo_relative(env, src), line)
    ls = env.tdoc_fixes[env.docname or None][name]
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


def check_sources_for_fixes(app):
    if not app.events.listeners.get('tdoc-list-sources'): return
    with display.progress_message("listing source files"):
        files = []
        def on_error(e): pass
        for parent, ds, fs in app.srcdir.walk(on_error=on_error):
            files.extend(SourceFile(app.env, parent / f) for f in fs)
        app.emit('tdoc-list-sources', files)


class FixCollector(collectors.EnvironmentCollector):
    @staticmethod
    def init(app):
        if not hasattr(app.env, 'tdoc_fixes'):
            # {docname: {name: {(path, line)}}}
            app.env.tdoc_fixes = collections.defaultdict(ext.dict_of_set)
        else:
            app.env.tdoc_fixes.pop(None, None)

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
    for docname, fxs in app.env.tdoc_fixes.items():
        for name, locations in fxs.items():
            data[name].update(locations)

    # Write the merged fixes to the build directory.
    (app.outdir.parent / util.fixes).write_text(util.to_json(data), 'utf-8')

    # Render a shield describing the fix status.
    (app.outdir / util.fixes_badge).write_text(badge(data), 'utf-8')

    # List the fixes.
    if not data: return
    _log.info(colour.bold("Fixes required:"))
    for name, locs in sorted(data.items()):
        dl, = fixes.attrs(name, 'deadline')
        deadline = f" [deadline: {dl}]" if dl is not None else ""
        loc_cnt = f" ({len(locs)} locations)" if locs else ""
        _log.info(f"  {colour.yellow(name)}{deadline}{loc_cnt}")
        for src, line in sorted(locs):
            _log.info(f"    {src}{f":{line}" if line else ""}")


_colors = {'error': '#d72d47', 'warning': '#f66a0a', 'info': '#276be9',
           '': '#34D058'}


def badge(data):
    count = len(data)
    digits = 1 + math.floor(math.log10(count)) if count > 0 else 1
    dw = 6 * digits
    tx = 43.5 + dw // 2
    level = min((fixes.level(n) for n in data), key=util.level_key, default='')
    color = _colors.get(level, _colors['warning'])
    return f"""\
<svg xmlns="http://www.w3.org/2000/svg" width="{50 + dw}" height="20"\
 role="img" aria-label="Fixes: {count}">\
<title>Fixes: {count}</title>\
<filter id="blur"><feGaussianBlur stdDeviation="16"/></filter>\
<linearGradient id="s" x2="0" y2="100%">\
<stop offset="0" stop-color="#bbb" stop-opacity=".1"/>\
<stop offset="1" stop-opacity=".1"/>\
</linearGradient>\
<clipPath id="r"><rect width="{50 + dw}" height="20" rx="3"/></clipPath>\
<g clip-path="url(#r)">\
<rect width="39" height="20" fill="#555"/>\
<rect x="39" width="{11 + dw}" height="20" fill="{color}"/>\
<rect width="{50 + dw}" height="20" fill="url(#s)"/>\
</g>\
<g fill="#fff" text-anchor="middle"\
 font-family="Verdana,Geneva,DejaVu Sans,sans-serif"\
 text-rendering="geometricPrecision" font-size="11">\
<g>\
<g aria-hidden="true" fill="#010101">\
<text x="20.5" y="15" fill-opacity=".8" filter="url(#blur)"\
 textLength="25">Fixes</text>\
<text x="20.5" y="15" fill-opacity=".3" textLength="29">Fixes</text>\
</g>\
<text x="20.5" y="14" textLength="29">Fixes</text>\
</g>\
<g>\
<g aria-hidden="true" fill="#010101">\
<text x="{tx}" y="15" fill-opacity=".8" filter="url(#blur)"\
 textLength="{1 + dw}">{count}</text>\
<text x="{tx}" y="15" fill-opacity=".3" textLength="{1 + dw}">{count}</text>\
</g>\
<text x="{tx}" y="14" textLength="{1 + dw}">{count}</text>\
</g>\
</g>\
</svg>"""


# https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file#naming-conventions
_bad_filename_re = re.compile(r'[\x00-\x20"*/:<>?\\|\x7f-\U0010ffff]')


def _fix_bad_filename(app, files):
    for file in files:
        if any(_bad_filename_re.search(p)
               for p in str(file.rel_path).split(os.sep)):
            file.add_fix('bad-filename')
