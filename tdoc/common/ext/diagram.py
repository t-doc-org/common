# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import copy

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.util import docutils, logging

from . import __version__, merge_dict, report_exceptions

_log = logging.getLogger(__name__)

# TODO: Remove :style: if it isn't useful

def setup(app):
    app.add_config_value('tdoc_diagram', {}, 'html', dict)
    app.add_directive('diagram', Diagram)
    app.add_node(diagram, html=(visit_diagram, depart_diagram))
    app.connect('tdoc-html-page-config', set_html_page_config)
    app.connect('html-page-context', add_js)
    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


class Diagram(docutils.SphinxDirective):
    required_arguments = 1
    option_spec = {
        'class': directives.class_option,
        'style': directives.unchanged,
    }
    has_content = True
    types = ('mermaid',)

    @report_exceptions
    def run(self):
        if (typ := self.arguments[0]) not in self.types:
            raise Exception(f"{{diagram}}: Unsupported type: {typ}")
        node = diagram(type=typ)
        self.set_source_info(node)
        node['classes'] += self.options.get('class', [])
        if typ == 'mermaid' and self.content.count('---') == 1:
            node.append(nodes.Text("---\n"))
        if v := self.options.get('style', '').strip(): node['style'] = v
        node.append(nodes.Text(''.join(f'{line}\n' for line in self.content)))
        return [node]


class diagram(nodes.General, nodes.Element): pass


def visit_diagram(self, node):
    attrs = {'data-type': node['type']}
    if v := node.get('style'): attrs['style'] = v
    self.body.append(self.starttag(node, 'div', '', classes=['tdoc-diagram'],
                                   **attrs))


def depart_diagram(self, node):
    self.body.append('</div>\n')


def set_html_page_config(app, page, config, doctree):
    if page is None or doctree is None: return
    cfg = app.config.tdoc_diagram
    if (md := app.env.metadata[page].get('diagram')) is not None:
        cfg = merge_dict(copy.deepcopy(cfg), md)
    dcfg = {}
    for t in {n['type'] for n in doctree.findall(diagram)}:
        dcfg[t] = cfg.get(t, {})
    if dcfg: config['diagram'] = dcfg


def add_js(app, page, template, context, doctree):
    if doctree and doctree.next_node(diagram) is not None:
        app.add_js_file('tdoc/diagram.js', type='module')
