# Copyright 2026 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import os
import pathlib
import subprocess
import sys

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

    return {
        'version': ext.__version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


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
            # TODO: Index by dst instead of src
            app.env.tdoc_xopp = {}  # src => ({docnames}, dst)

    def clear_doc(self, app, env, docname):
        for src, (docnames, dst) in list(env.tdoc_xopp.items()):
            docnames.discard(docname)
            if not docnames: del env.tdoc_xopp[src]

    def merge_other(self, app, env, docnames, other):
        for src, (docs, dst) in other.tdoc_xopp.items():
            docnames = self.entry(env, src, dst)
            docnames.update(docs)

    def process_doc(self, app, doctree):
        env = app.env
        docname = env.docname
        for node in doctree.findall(xopp):
            docnames = self.entry(env, node['src'], node['dst'])
            docnames.add(docname)

    def entry(self, env, src, dst):
        return env.tdoc_xopp.setdefault(src, (set(), dst))[0]


def render_xopp(app, builder):
    if builder.format != 'html' or not app.env.tdoc_xopp: return

    # Check the binary even if there's nothing to (re-)build.
    if (exe := xournalpp_path(app)) is None: return

    # Find files whose destination is older than the source.
    stale = []
    for src, (docnames, dst) in app.env.tdoc_xopp.items():
        try:
            if ext.needs_build(src, d := builder.outdir / dst):
                stale.append((src, d))
        except OSError as e:
            _log.error("{xopp}: %s: %s", src, e, location=next(iter(docnames)))
    if not stale: return

    # Render xopp files to pdf.
    for src, dst in display.status_iterator(
            stale, "rendering xopp files... ", 'brown', len(stale),
            app.config.verbosity,
            lambda it: osutil._relative_path(it[0], builder.srcdir).as_posix()):
        render(exe, src, dst)


def xournalpp_path(app):
    if not (path := app.config.xournalpp_path):
        path = 'xournalpp'
        if sys.platform == 'win32':
            if (lad := os.environ.get('LOCALAPPDATA')) is not None:
                p = pathlib.Path(lad) / 'Programs' / 'Xournal++' / 'bin' \
                    / 'xournalpp.exe'
                if p.exists(): path = p
    try:
        subprocess.run([path, '--version'], stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, check=True, text=True)
        return path
    except OSError as e:
        _log.error("{xopp}: Unable to run xournalpp: %s", e)
    except subprocess.CalledProcessError as e:
        _log.error("{xopp}: Unable to run xournalpp:\n%s", e.stdout)


def render(exe, src, dst):
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([exe, f'--create-pdf={dst}', src],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       check=True, text=True)
    except OSError as e:
        _log.error("{xopp}: Unable to run xournalpp: %s", e)
    except subprocess.CalledProcessError as e:
        _log.error("{xopp}: Export failed for %s:\n%s", src, e.stdout)
