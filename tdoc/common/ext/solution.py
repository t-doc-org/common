# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

from docutils import languages, nodes
from docutils.parsers.rst import directives
from docutils.parsers.rst.directives import admonitions
from sphinx import config
from sphinx.util import logging

from . import _, __version__

_log = logging.getLogger(__name__)


def setup(app):
    app.add_config_value('tdoc_solutions', 'show', 'html',
                         config.ENUM('show', 'hide', 'dynamic'))
    app.add_directive('solution', Solution)
    app.add_node(solution, html=(visit_solution, depart_solution))
    app.connect('tdoc-html-page-config', set_html_page_config)
    app.connect('html-page-context', add_header_button, priority=500.5)
    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


class solution(nodes.Admonition, nodes.Element): pass


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


def set_html_page_config(app, page, config, doctree):
    md = app.env.metadata[page]
    v = md.get('solutions', app.config.tdoc_solutions)
    if not app.config.values['tdoc_solutions'].valid_types.match(v):
        _log.warning(f"{{metadata}}: Invalid 'solutions' value: {v}")
        v = md['solutions'] = 'show'
    if v != 'show':
        config['html_data']['tdocSolutions'] = v


def add_header_button(app, page, template, context, doctree):
    if doctree is None: return
    if all('always-show' in sol['classes']
           for sol in doctree.findall(solution)): return
    context["header_buttons"].append({
        'type': 'javascript',
        'javascript': 'tdoc.toggleSolutions()',
        'tooltip': _("Toggle solutions"),
        'label': 'toggle-solutions',
    })


def visit_solution(self, node):
    return self.visit_admonition(node)


def depart_solution(self, node):
    return self.depart_admonition(node)
