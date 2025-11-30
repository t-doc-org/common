# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import re

from docutils import nodes
from docutils.parsers.rst import directives
import pyjson5
from sphinx.util import logging

from . import __version__, Dyn, dyn, tdoc_config, to_json

_log = logging.getLogger(__name__)


def setup(app):
    app.add_directive('jsxgraph', JsxGraph)
    app.connect('html-page-context', add_css_js)
    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


template_re = re.compile(r'(?s)([a-zA-Z0-9_-]+)(?:\((.*)\))?')


class JsxGraph(Dyn):
    optional_arguments = 1
    option_spec = Dyn.option_spec | {
        'template': directives.unchanged,
    }

    def populate(self, node):
        node['classes'].append('jxgbox')
        if (v := self.options.get('template')) is not None:
            if 'name' in node:
                raise Exception(
                    "{jsxgraph} Graph with :template: must not have a name")
            if (m := template_re.fullmatch(v.strip())) is None:
                raise Exception(f"{{jsxgraph}} Invalid :template: value: {v}")
            attrs = {'data-template': m.group(1)}
            if (v := m.group(2)) is not None:
                attrs['data-args'] = to_json(pyjson5.decode(f'[{v}]'))
            node['attrs'] = attrs
        elif 'name' not in node:
            raise Exception("{jsxgraph} Graph must have a name")
        node.append(nodes.container('', nodes.Text("Rendering..."),
                                    classes=['spinner']))
        super().populate(node)


def add_css_js(app, page, template, context, doctree):
    if doctree and doctree.next_node(dyn.has_type('jsxgraph')) is not None:
        tdoc = tdoc_config(app, page, doctree, context)
        base = tdoc['versions']['jsxgraph']
        app.add_css_file(f'{base}/jsxgraph.css', priority=199)  # Before theme
        app.add_js_file('tdoc/jsxgraph.js', type='module')
