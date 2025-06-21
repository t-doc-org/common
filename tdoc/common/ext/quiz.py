# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import html

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.util import docutils, logging

from . import __version__, report_exceptions, Role, to_base64

_log = logging.getLogger(__name__)


def setup(app):
    app.add_directive('quiz', Quiz)
    app.add_role('quiz-ph', QuizPh)
    app.add_role('quiz-hint', QuizHint)
    app.add_role('quiz-input', QuizInput)
    app.add_role('quiz-select', QuizSelect)
    app.add_node(quiz, html=(visit_quiz, depart_quiz))
    app.add_node(quiz_ph, html=(visit_quiz_ph, None))
    app.add_node(quiz_hint)
    app.add_node(quiz_input, html=(visit_quiz_input, None))
    app.add_node(quiz_select, html=(visit_quiz_select, None))
    app.connect('html-page-context', add_js)
    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


def add_js(app, page, template, context, doctree):
    if doctree and any(doctree.findall(quiz)):
        app.add_js_file('tdoc/quiz.js', type='module')


class quiz_input(nodes.Inline, nodes.Element): pass
class quiz_select(nodes.Inline, nodes.Element): pass

field_types = (quiz_input, quiz_select)


class Quiz(docutils.SphinxDirective):
    optional_arguments = 2
    option_spec = {
        'class': directives.class_option,
        'style': directives.unchanged,
    }
    has_content = True

    @report_exceptions
    def run(self):
        typ = self.arguments[0] if len(self.arguments) > 0 else 'static'
        gen = self.arguments[1] if len(self.arguments) > 1 else None
        if typ == 'static':
            pass
        elif typ == 'table':
            if gen is None:
                raise Exception("{quizz} table: Missing generator argument")
        else:
            raise Exception(f"{{quizz}}: Invalid type: {typ}")

        children = self.parse_content_to_nodes()
        if any(True for c in children for n in c.findall(quiz)):
            raise Exception("{quiz}: Must not contain {quiz}")
        if not any(True for c in children
                   for n in c.findall(lambda n: isinstance(n, field_types))):
            raise Exception("{quiz}: Must contain at least one field")
        if typ == 'table':
            if not sum(1 for c in children if isinstance(c, nodes.table)):
                raise Exception("{quizz} table: Must contain a single table")
            names = set()
            for c in children:
                for n in c.findall(
                        lambda n: isinstance(n, field_types + (quiz_ph,))):
                    if (name := n['text']) in names:
                        raise Exception("{{quizz}}: Duplicate placeholder or "
                                        f" field name: {name}")
                    names.add(name)

        # Associate hints with fields.
        for child in children:
            for field in child.findall(lambda n: isinstance(n, field_types)):
                for n in field.findall(include_self=False, descend=False,
                                       siblings=True):
                    if isinstance(n, nodes.Text) and not n.strip(): continue
                    if not isinstance(n, quiz_hint): break
                    field['hint'] = n['text']
                    n.parent.remove(n)
                    break
        for child in children:
            for n in child.findall(quiz_hint):
                _log.error("{quiz-hint}: must immediately follow a field",
                           location=n)
                n.parent.remove(n)

        node = quiz('', *children)
        self.set_source_info(node)
        node['type'] = typ
        if gen is not None: node['gen'] = gen
        node['classes'] += self.options.get('class', [])
        if v := self.options.get('style', '').strip(): node['style'] = v
        return [node]


class quiz(nodes.Body, nodes.Element): pass


def visit_quiz(self, node):
    attrs = {'data-type': node['type']}
    if v := node.get('gen'): attrs['data-gen'] = v
    if v := node.get('style'): attrs['style'] = v
    self.body.append(self.starttag(
        node, 'div', suffix='', classes=['tdoc-quiz'], **attrs))
    self.body.append(
        '<div class="content"><span class="tdoc-quiz-hint"></span>')


def depart_quiz(self, node):
    self.body.append('</div>')
    if node.get('type') == 'static':
        self.body.append("""\
<div class="controls">\
<button class="tdoc-check fa-check" title="Check answers"></button>\
</div>\
""")
    self.body.append('</div>')


class QuizPh(Role):
    def run(self):
        node = quiz_ph()
        self.set_source_info(node)
        node['text'] = self.text
        return [node], []


class quiz_ph(nodes.Inline, nodes.Element): pass


def visit_quiz_ph(self, node):
    self.body.append(self.starttag(
        node, 'span', suffix='', classes=['tdoc-quiz-ph'],
        **{'data-text': node['text']}))
    raise nodes.SkipNode


class QuizHint(Role):
    def run(self):
        node = quiz_hint()
        self.set_source_info(node)
        node['text'] = self.text
        return [node], []


class quiz_hint(nodes.Inline, nodes.Element): pass


class QuizField(Role):
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
        node['role'] = self.name
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
    attrs = {'data-role': node['role'], 'data-text': to_base64(node['text'])}
    if v := node.get('style'): attrs['style'] = v
    if v := node.get('check'): attrs['data-check'] = v
    if v := node.get('hint'): attrs['data-hint'] = v
    return attrs


class QuizInput(QuizField):
    node_type = quiz_input


def visit_quiz_input(self, node):
    self.body.append(self.starttag(
        node, 'input', suffix='', type='text', classes=['tdoc-quiz-field'],
        autocapitalize="off", autocomplete="off", autocorrect="off",
        spellcheck="false", **attributes(node)))
    raise nodes.SkipNode


class QuizSelect(QuizField):
    node_type = quiz_select
    options = {
        **QuizField.options,
        'options': directives.unchanged,
    }

    def update_node(self, node):
        if (opts := self.options.get('options')) is None:
            raise Exception("{quiz-select}: No :options: specified")
        opts = node['options'] = [''] + opts.split('\n')


def visit_quiz_select(self, node):
    self.body.append(self.starttag(
        node, 'select', suffix='', classes=['tdoc-quiz-field'],
        **attributes(node)))
    for opt in node['options']:
        self.body.append(
            f'<option value="{self.attval(opt)}">{html.escape(opt)}</option>')
    self.body.append('</select>')
    raise nodes.SkipNode
