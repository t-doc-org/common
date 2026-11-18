# Copyright 2026 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import collections
import functools
import gzip
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import threading
from xml.etree import ElementTree

from docutils import nodes
from sphinx.environment import collectors
from sphinx.util import display, logging, osutil

from .. import ext

_log = logging.getLogger(__name__)


def setup(app):
    app.add_config_value('xournalpp_path', '', 'html', str)
    app.add_node(xopp)
    app.add_role('xopp', Xopp)
    app.connect('builder-inited', XoppCollector.init)
    app.add_env_collector(XoppCollector)
    app.connect('write-started', render_xopp)
    return ext.setup_result


class xopp(nodes.reference): pass


class Xopp(ext.ReferenceRole):
    @ext.report_exceptions
    def run(self):
        title = self.title if self.has_explicit_title \
                else pathlib.Path(self.target).stem
        rel, src = self.env.relfn2path(self.target)
        rel, src = pathlib.Path(rel), pathlib.Path(src)
        dst = rel.with_suffix('.pdf')
        doc_uri = self.env.app.builder.get_target_uri(
            self.env.current_document.docname)
        node = xopp('', nodes.Text(title), internal=True, classes=['xopp'],
                    src=src, dst=dst, target='_blank',
                    refuri=osutil.relative_uri(doc_uri, dst.as_posix()))
        return [node], []


class XoppCollector(collectors.EnvironmentCollector):
    @staticmethod
    def init(app):
        if not hasattr(app.env, 'tdoc_xopp'):
            # {docname: {dst: src}}
            app.env.tdoc_xopp = collections.defaultdict(dict)

    def clear_doc(self, app, env, docname):
        app.env.tdoc_xopp.pop(docname, None)

    def merge_other(self, app, env, docnames, other):
        for docname in docnames:
            if (fs := other.tdoc_xopp.get(docname)) is not None:
                env.tdoc_xopp[docname] = fs
            else:
                env.tdoc_xopp.pop(docname, None)

    def process_doc(self, app, doctree):
        env, xopps = app.env, None
        for node in doctree.findall(xopp):
            if xopps is None: xopps = env.tdoc_xopp[env.docname]
            xopps[node['dst']] = node['src']


def render_xopp(app, builder):
    if builder.format != 'html' or not app.env.tdoc_xopp: return

    # Check the binary even if there's nothing to (re-)build.
    if (exe := xournalpp_path(app)) is None: return

    # Find files whose destination is older than the source.
    stale = {}
    for docname, xopps in app.env.tdoc_xopp.items():
        for dst, src in xopps.items():
            try:
                if ext.needs_build(d := builder.outdir / dst, src):
                    stale[d] = src
            except OSError as e:
                _log.error("{xopp}: %s", e, location=docname)
    if not stale: return

    # Render xopp files to pdf.
    lock = threading.Lock()
    def expand(*args):
        with lock: return expand_role(app, *args)
    for task, it in ext.map_parallel(
            app, lambda args: process(exe, expand, *args), stale.items(),
            "rendering xopp files... ", 'brown',
            lambda it: osutil._relative_path(it[1], builder.srcdir).as_posix()):
        if (e := task.exception()) is not None:
            _log.error("{xopp}: %s", e, location=f'{it[1]}:0')


def xournalpp_path(app):
    if not (path := app.config.xournalpp_path):
        path = 'xournalpp'
        if sys.platform == 'win32' and (p := ext.find_app_path(f'{path}.exe')):
            path = p.with_stem(p.stem.replace('-wrapper', ''))
    try:
        subprocess.run([path, '--version'], stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, check=True, text=True,
                       errors='replace')
        return path
    except OSError as e:
        _log.error("{xopp}: Unable to run xournalpp: %s", e)
    except subprocess.CalledProcessError as e:
        _log.error("{xopp}: Unable to run xournalpp:\n%s", e.stdout)


def process(exe, expand, dst, src):
    # Load the document and expand roles.
    with gzip.open(src) as zf:
        tree = ElementTree.parse(zf)
    expand = functools.partial(expand, dst, src)
    modified = False
    for el in tree.iterfind('./page/layer//text'):
        if el.text is None: continue
        if (v := role_re.sub(expand, el.text)) != el.text:
            el.text = v
            modified = True

    # If no expansion was done, render from the source.
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not modified:
        render(exe, dst, src)
        return

    # With expansion, write the modified document to a file with the same name
    # in a tempoary directory (the file name is used as the title of the PDF),
    # and render from the expanded document.
    tmp = pathlib.Path(tempfile.mkdtemp(dir=dst.parent, prefix='xournal.'))
    path = tmp / src.name
    try:
        with gzip.open(path, 'wb') as zf:
            tree.write(zf, encoding='utf-8')
        render(exe, dst, path)
    finally:
        path.unlink(missing_ok=True)
        tmp.rmdir()


def render(exe, dst, src):
    try:
        subprocess.run([exe, f'--create-pdf={dst}', src],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       check=True, text=True, errors='replace')
    except OSError as e:
        _log.error("{xopp}: Unable to run xournalpp: %s", e)
    except subprocess.CalledProcessError as e:
        _log.error("{xopp}: Export failed:\n%s", e.stdout, location=f'{src}:0')


role_re = re.compile(r'\{[^}]+\}`[^`]+`')

def expand_role(app, dst, src, m):
    doctree = ext.str_to_doctree(app, str(dst.relative_to(app.outdir)), m[0],
                                 filename=src, filetype='markdown')
    return ''.join(n.astext() for n in doctree.findall(nodes.Text))
