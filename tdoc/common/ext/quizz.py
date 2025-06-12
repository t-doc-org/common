# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import html

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.util import docutils, logging

from . import __version__, report_exceptions, Role, to_base64

_log = logging.getLogger(__name__)

# TODO: Remove the "Reset answers" button?
# TODO: Add optional check arguments, e.g. split(,)
# TODO: Allow creating questions randomly

def setup(app):
    app.add_directive('quizz', Quizz)
    app.add_role('quizz-hint', QuizzHint)
    app.add_role('quizz-input', QuizzInput)
    app.add_role('quizz-select', QuizzSelect)
    app.add_node(quizz, html=(visit_quizz, depart_quizz))
    app.add_node(quizz_hint)
    app.add_node(quizz_input, html=(visit_quizz_input, None))
    app.add_node(quizz_select, html=(visit_quizz_select, None))
    app.connect('html-page-context', add_js)
    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


def add_js(app, page, template, context, doctree):
    if doctree and any(doctree.findall(quizz)):
        app.add_js_file('tdoc/quizz.js', type='module')


class quizz_input(nodes.Inline, nodes.Element): pass
class quizz_select(nodes.Inline, nodes.Element): pass

field_types = (quizz_input, quizz_select)


class Quizz(docutils.SphinxDirective):
    option_spec = {
        'class': directives.class_option,
        'style': directives.unchanged,
    }
    has_content = True

    @report_exceptions
    def run(self):
        children = self.parse_content_to_nodes()
        if any(True for c in children for n in c.findall(quizz)):
            raise Exception("{quizz}: Must not contain {quizz}")
        if not any(True for c in children
                   for n in c.findall(lambda n: isinstance(n, field_types))):
            raise Exception("{quizz}: Must contain at least one field")

        # Associate hints with fields.
        for child in children:
            for field in child.findall(lambda n: isinstance(n, field_types)):
                for n in field.findall(include_self=False, descend=False,
                                       siblings=True):
                    if isinstance(n, nodes.Text) and not n.strip(): continue
                    if not isinstance(n, quizz_hint): break
                    field['hint'] = n['text']
                    n.parent.remove(n)
                    break
        for child in children:
            for n in child.findall(quizz_hint):
                _log.error("{quizz-hint}: must immediately follow a field",
                           location=n)
                n.parent.remove(n)

        node = quizz('', *children)
        self.set_source_info(node)
        node['classes'] += self.options.get('class', [])
        if v := self.options.get('style', '').strip(): node['style'] = v
        return [node]


class quizz(nodes.Body, nodes.Element): pass


def visit_quizz(self, node):
    attrs = {}
    if v := node.get('style'): attrs['style'] = v
    self.body.append(self.starttag(
        node, 'div', suffix='', classes=['tdoc-quizz'], **attrs))
    self.body.append(
        '<div class="content"><span class="tdoc-quizz-hint"></span>')


def depart_quizz(self, node):
    self.body.append("""\
</div><div class="controls">\
<button class="tdoc-check fa-check" title="Check answers"></button>\
<button class="tdoc-reset fa-rotate-left" title="Reset answers"></button>\
</div></div>\
""")


class QuizzHint(Role):
    def run(self):
        node = quizz_hint()
        self.set_source_info(node)
        node['text'] = self.text
        return [node], []


class quizz_hint(nodes.Inline, nodes.Element): pass


class QuizzField(Role):
    options = {
        'check': directives.unchanged,
        'right': directives.unchanged,
        'style': directives.unchanged,
    }
    content = True

    @report_exceptions
    def run(self):
        node = self.node_type()
        self.set_source_info(node)
        node['text'] = self.text
        node['classes'] = self.options['classes'][:]
        if v := self.options.get('check'): node['check'] = v
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
        self.update_node(node)
        return [node], []

    def update_node(self, node): pass


def attributes(node):
    attrs = {'data-text': to_base64(node['text'])}
    if v := node.get('style'): attrs['style'] = v
    if v := node.get('check'): attrs['data-check'] = v
    if v := node.get('hint'): attrs['data-hint'] = v
    return attrs


class QuizzInput(QuizzField):
    node_type = quizz_input


def visit_quizz_input(self, node):
    self.body.append(self.starttag(
        node, 'input', suffix='', type='text', classes=['tdoc-quizz-field'],
        autocapitalize="off", autocomplete="off", autocorrect="off",
        spellcheck="false", **attributes(node)))
    raise nodes.SkipNode


class QuizzSelect(QuizzField):
    node_type = quizz_select
    options = {
        **QuizzField.options,
        'options': directives.unchanged,
    }

    def update_node(self, node):
        if (opts := self.options.get('options')) is None:
            raise Exception("{quizz-select}: No :options: specified")
        opts = node['options'] = [''] + opts.split('\n')
        if node.get('check') is None and node['text'] not in opts:
            raise Exception("{quizz-select}: Solution is not in :options:")


def visit_quizz_select(self, node):
    self.body.append(self.starttag(
        node, 'select', suffix='', classes=['tdoc-quizz-field'],
        **attributes(node)))
    for opt in node['options']:
        self.body.append(
            f'<option value="{self.attval(opt)}">{html.escape(opt)}</option>')
    self.body.append('<select>')
    raise nodes.SkipNode
