# Copyright 2024 Caroline Blank <caro@c-space.org>
# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import pathlib

from docutils import nodes

from sphinx.directives.code import CodeBlock
from sphinx.util import logging

__version__ = '0.1'
_common = pathlib.Path(__file__).absolute().parent
_root = _common.parent.parent
makefile = str(_common / 'common.mk')

log = logging.getLogger(__name__)


def setup(app):
    app.add_directive('exec', Exec)
    app.add_css_file('tdoc.css')
    app.connect('builder-inited', on_builder_inited)
    app.connect('html-page-context', on_html_page_context)
    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


def on_builder_inited(app):
    app.config.html_static_path.extend([
        str(_common / 'static'),
        str(_root / 'ext' / 'sqlite-wasm' / 'sqlite-wasm'),
    ])


def on_html_page_context(app, page, template, context, doctree):
    if doctree and any(doctree.findall(Exec.match_node('sql'))):
        app.add_js_file('tdoc-sql.js', type='module')
        # TODO: Add Cross-Origin-*-Policy headers in the dev server
        # TODO: Work around inability to specify headers on GitHub Pages


class Exec(CodeBlock):
    @staticmethod
    def match_node(lang=None):
        return lambda n: isinstance(n, nodes.literal_block) \
                         and 'tdoc-exec' in n['classes'] \
                         and (lang is None or n.get('language') == lang)

    def run(self):
        res = super().run()
        for node in res:
            for n in node.findall(nodes.literal_block):
                n['classes'] += ['tdoc-exec']
        # log.info("res: %s", res, color='yellow')
        return res
