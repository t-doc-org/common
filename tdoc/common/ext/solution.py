# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

from docutils import languages, nodes
from docutils.parsers.rst import directives
from docutils.parsers.rst.directives import admonitions
from sphinx.util import logging

from . import _, __version__

_log = logging.getLogger(__name__)


def setup(app):
    app.add_directive('solution', Solution)
    app.add_node(solution, html=(visit_solution, depart_solution))
    app.connect('doctree-read', remove_solutions)
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


def solutions(env, page):
    md = env.metadata[page]
    # TODO: Remove hide-solutions
    if (hs := md.get('hide-solutions', None)) is not None:
        return 'hide' if hs else 'show'
    if (v := md.get('solutions', 'show')) not in ('show', 'hide', 'remove'):
        _log.warning(f"Invalid 'solutions' value in {{metadata}}: {v}")
        v = md['solutions'] = 'show'
    if v == 'remove' and 'tdoc-dev' in env.app.tags: v = 'hide'
    return v


def remove_solutions(app, doctree):
    if solutions(app.env, app.env.docname) != 'remove': return
    for n in list(doctree.findall(solution)):
        if 'always-show' not in n['classes']: n.parent.remove(n)


def set_html_page_config(app, page, config):
    if solutions(app.env, page) != 'show':
        config['html_data']['tdocSolutions'] = 'hide'


def add_header_button(app, page, template, context, doctree):
    if doctree is None or solutions(app.env, page) != 'hide': return
    if not any('always-show' not in sol['classes']
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
