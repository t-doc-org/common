# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

from sphinx.util import logging

from . import __version__, Dyn, dyn, tdoc_config

_log = logging.getLogger(__name__)


def setup(app):
    app.add_directive('jsxgraph', JsxGraph)
    app.connect('html-page-context', add_css_js)
    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


class JsxGraph(Dyn):
    required_arguments = 1
    has_content = True

    def populate(self, node):
        node['classes'].append('jxgbox')
        node['args'] = self.json_content()


def add_css_js(app, page, template, context, doctree):
    if doctree and doctree.next_node(dyn.has_type('jsxgraph')) is not None:
        tdoc = tdoc_config(app, page, doctree, context)
        base = tdoc['versions']['jsxgraph']
        app.add_css_file(f'{base}/jsxgraph.css', priority=199)  # Before theme
        app.add_js_file('tdoc/jsxgraph.js', type='module')
