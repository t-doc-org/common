# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

from docutils import languages, nodes
from docutils.parsers.rst import directives
from docutils.parsers.rst.directives import admonitions
from sphinx.util import logging

from . import _, __version__

_log = logging.getLogger(__name__)


def setup(app):
    app.add_node(solution, html=(visit_solution, depart_solution))
    app.add_directive('solution', Solution)
    app.connect('tdoc-html-page-config', set_html_page_config)
    app.connect('html-page-context', add_header_button, priority=501)
    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


class solution(nodes.Admonition, nodes.Element): pass


def visit_solution(self, node):
    return self.visit_admonition(node)


def depart_solution(self, node):
    return self.depart_admonition(node)


class Solution(admonitions.BaseAdmonition):
    node_class = solution
    optional_arguments = 1
    option_spec = admonitions.BaseAdmonition.option_spec | {
        'expand': directives.flag,
        'show': directives.flag,
    }

    def run(self):
        res = super().run()
        title_text = self.arguments[0] if self.arguments else _("Solution")
        for node in res:
            if not isinstance(node, self.node_class): continue
            text_nodes, msgs = self.state.inline_text(title_text, self.lineno)
            title = nodes.title(title_text, '', *text_nodes)
            title.source, title.line = \
                self.state_machine.get_source_and_line(self.lineno)
            node[:0] = [title] + msgs
            cls = node['classes']
            if not cls: cls += ['note', 'dropdown']
            cls += ['solution']
            if 'expand' in self.options: cls += ['expand']
            if 'show' in self.options: cls += ['always-show']
        return res


def set_html_page_config(app, page, config):
    hide = app.env.metadata[page].get('hide-solutions', False)
    if hide is not False: config['htmlData']['tdocSolutions'] = 'hide'


def add_header_button(app, page, template, context, doctree):
    context["header_buttons"].append({
        'type': 'javascript',
        'javascript': 'tdocToggleSolutions()',
        'tooltip': _("Toggle solutions"),
        'label': 'toggle-solutions',
    })
