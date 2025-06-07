# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.util import docutils, logging

from . import __version__, report_exceptions, Role, to_base64

_log = logging.getLogger(__name__)


def setup(app):
    app.add_directive('quizz', Quizz)
    app.add_role('quizz-input', QuizzInput)
    app.add_node(quizz, html=(visit_quizz, depart_quizz))
    app.add_node(quizz_input, html=(visit_quizz_input, None))
    app.connect('html-page-context', add_js)
    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


class Quizz(docutils.SphinxDirective):
    option_spec = {
        'class': directives.class_option,
    }
    has_content = True

    @report_exceptions
    def run(self):
        children = self.parse_content_to_nodes()
        if any(True for c in children for n in c.findall(quizz)):
            raise Exception("{quizz}: Must not contain {quizz}")
        if not any(True for c in children for n in c.findall(quizz_input)):
            raise Exception("{quizz}: Must contain at least one field")
        node = quizz('', *children)
        self.set_source_info(node)
        node['classes'] += self.options.get('class', [])
        return [node]


class quizz(nodes.Body, nodes.Element): pass


def visit_quizz(self, node):
    self.body.append(self.starttag(
        node, 'div', suffix='', classes=['tdoc-quizz']))
    self.body.append('<div class="content">')


def depart_quizz(self, node):
    self.body.append("""\
</div><div class="controls">\
<button class="tdoc-check fa-check" title="Check answers"></button>\
<button class="tdoc-reset fa-rotate-left" title="Reset answers"></button>\
</div></div>\
""")


class QuizzInput(Role):
    options = {
        'right': directives.unchanged,
        'style': directives.unchanged,
        # TODO: Filter to apply to answer before comparing
        # TODO: Solution separator
        # TODO: JS function to apply to role content to compute answer
        # TODO: JS function to check answer
    }
    content = True

    def run(self):
        node = quizz_input()
        self.set_source_info(node)
        node['text'] = self.text
        node['classes'] = self.options['classes'][:]
        style = []
        if (v := self.options.get('right')) is not None:
            node['classes'].append('right')
            if v := v.strip():
                if not v.endswith(';'): v += ';'
                style.append(v)
        if v := self.options.get('style', '').strip():
            if not v.endswith(';'): v += ';'
            style.append(v)
        if style: node['style'] = ' '.join(style)
        return [node], []


class quizz_input(nodes.Inline, nodes.Element): pass


def visit_quizz_input(self, node):
    kwargs = {'data-text': to_base64(node['text'])}
    if v := node.get('style'): kwargs['style'] = v
    self.body.append(self.starttag(
        node, 'input', suffix='', type='text', classes=['tdoc-quizz-field'],
        autocapitalize="off", autocomplete="off", autocorrect="off",
        spellcheck="false", **kwargs))
    raise nodes.SkipNode


def add_js(app, page, template, context, doctree):
    if doctree and any(doctree.findall(quizz)):
        app.add_js_file('tdoc/quizz.js', type='module')
