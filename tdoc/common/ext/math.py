# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

from docutils import nodes
from docutils.parsers.rst import directives
import markupsafe

from sphinx.util import docutils, logging

from . import __version__, deps, report_exceptions, tdoc_config, UniqueChecker

_log = logging.getLogger(__name__)


def setup(app):
    app.add_directive('jsxgraph', JsxGraph)
    app.add_node(jsxgraph, html=(visit_jsxgraph, depart_jsxgraph))
    app.add_env_collector(UniqueChecker('jsxgraph-name',
        lambda doctree: ((n, n.get('name')) for n in doctree.findall(jsxgraph)),
        "{jsxgraph}: Duplicate name"))
    app.connect('html-page-context', add_css_js)
    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


class JsxGraph(docutils.SphinxDirective):
    required_arguments = 1
    option_spec = {
        'class': directives.class_option,
        'style': directives.unchanged,
    }

    @report_exceptions
    def run(self):
        node = jsxgraph('')
        self.set_source_info(node)
        self.state.document.set_id(node)
        node['name'] = self.arguments[0]
        node['classes'] += self.options.get('class', [])
        if v := self.options.get('style', '').strip(): node['style'] = v
        return [node]


class jsxgraph(nodes.General, nodes.Element): pass


def visit_jsxgraph(self, node):
    attrs = {'data-name': node['name']}
    if v := node.get('style'): attrs['style'] = v
    self.body.append(
        self.starttag(node, 'div', '', classes=['tdoc-jsxgraph', 'jxgbox'],
                      **attrs))
    self.body.append('<div class="spinner">Rendering...</div>')


def depart_jsxgraph(self, node):
    self.body.append('</div>\n')


def add_css_js(app, page, template, context, doctree):
    if doctree and doctree.next_node(jsxgraph) is not None:
        tdoc = tdoc_config(app, page, doctree, context)
        base = tdoc['versions']['jsxgraph']
        app.add_css_file(f'{base}/jsxgraph.css', priority=199)  # Before theme
