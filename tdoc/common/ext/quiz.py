# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import html

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.util import docutils, logging

from .. import ext

_log = logging.getLogger(__name__)


def setup(app):
    app.add_directive('quiz', Quiz)
    app.add_directive('quiz-check', QuizCheck)
    app.add_role('quiz-ph', QuizPh)
    app.add_role('quiz-hint', QuizHint)
    app.add_role('quiz-input', QuizInput)
    app.add_role('quiz-select', QuizSelect)
    app.add_node(quiz, html=(visit_quiz, depart_quiz))
    app.add_node(quiz_ph, html=(visit_quiz_ph, None))
    app.add_node(quiz_hint)
    app.add_node(quiz_input, html=(visit_quiz_input, None))
    app.add_node(quiz_select, html=(visit_quiz_select, None))
    app.add_node(quiz_group, html=(visit_quiz_group, depart_quiz_group))
    app.add_node(quiz_check, html=(visit_quiz_check, depart_quiz_check))
    app.connect('html-page-context', add_js)
    return {
        'version': ext.__version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


def add_js(app, page, template, context, doctree):
    if doctree and doctree.next_node(quiz) is not None:
        app.add_js_file('tdoc/quiz.js', type='module')


class quiz(nodes.Body, nodes.Element): pass
class quiz_ph(nodes.Inline, nodes.Element): pass
class quiz_hint(nodes.Inline, nodes.Element): pass

class quiz_input(nodes.Inline, nodes.Element): pass
class quiz_select(nodes.Inline, nodes.Element): pass
class quiz_group(nodes.Sequential, nodes.Element): pass
class quiz_check(nodes.Part, nodes.Element): pass

field_roles = (quiz_input, quiz_select)
field_types = (quiz_input, quiz_select, quiz_check)
named_types = (quiz_ph,) + field_types


class Quiz(docutils.SphinxDirective):
    optional_arguments = 2
    option_spec = {
        'class': ext.opt_classes,
        'style': directives.unchanged,
    }
    has_content = True

    @ext.report_exceptions
    def run(self):
        typ = self.arguments[0] if len(self.arguments) > 0 else 'static'
        gen = self.arguments[1] if len(self.arguments) > 1 else None
        if typ == 'static':
            pass
        elif typ == 'table':
            if gen is None:
                raise Exception("{quiz} table: Missing generator argument")
        else:
            raise Exception(f"{{quiz}}: Invalid type: {typ}")

        children = self.parse_content_to_nodes()
        if any(True for c in children for n in c.findall(quiz)):
            raise Exception("{quiz}: Must not contain {quiz}")
        if not any(True for c in children
                   for n in c.findall(lambda n: isinstance(n, field_types))):
            raise Exception("{quiz}: Must contain at least one field")
        if typ == 'static':
            self.handle_static(children)
        elif typ == 'table':
            self.handle_table(children)

        # Associate hints with role fields.
        for child in children:
            for field in child.findall(lambda n: isinstance(n, field_roles)):
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

    def handle_static(self, children):
        for c in children:
            for g in c.findall(lambda n: isinstance(n, quiz_group)
                                         and n['type'] == 'radio'):
                if sum(f['text'] == '1' for f in g) != 1:
                    _log.error("{quiz-check}: Single-choice fields must have "
                               "exactly one solution", location=g)

    def handle_table(self, children):
        if not sum(isinstance(c, nodes.table) for c in children):
            raise Exception("{quiz} table: Must contain a single table")
        names = set()
        for c in children:
            for g in c.findall(quiz_group):
                if (name := g.get('name')) is None:
                    _log.error("{quiz-check}: Must have a name", location=g)
                    continue
                for i, n in enumerate(g):
                    if n['text'] != '0':
                        _log.error("{quiz-check}: Must not define solutions",
                                   location=n)
                    n['text'] = f'{name}_{i}'
            for n in c.findall(lambda n: isinstance(n, named_types)):
                if (name := n['text']) in names:
                    raise Exception("{quiz}: Duplicate placeholder or "
                                    f"field name: {name}")
                names.add(name)


def visit_quiz(self, node):
    attrs = {'type': node['type']}
    if v := node.get('gen'): attrs['generator'] = v
    if v := node.get('style'): attrs['style'] = v
    self.body.append(self.starttag(node, 'tdoc-quiz', suffix='', **attrs))
    self.body.append(
        '<div class="content"><span class="tdoc-quiz-hint"></span>\n')


def depart_quiz(self, node):
    self.body.append('</div>')
    if node['type'] == 'static':
        self.body.append("""\
<div class="controls">\
<button class="tdoc-check fa-check" title="Check answers"></button>\
</div>\
""")
    self.body.append('</tdoc-quiz>\n')


class QuizPh(ext.Role):
    def run(self):
        node = quiz_ph()
        self.set_source_info(node)
        node['text'] = self.text
        return [node], []


def visit_quiz_ph(self, node):
    self.body.append(self.starttag(node, 'tdoc-quiz-ph', suffix='',
                                   text=node['text']))
    self.body.append('</tdoc-quiz-ph>')
    raise nodes.SkipNode()


class QuizHint(ext.Role):
    def run(self):
        node = quiz_hint()
        self.set_source_info(node)
        node['text'] = self.text
        return [node], []


class QuizField(ext.Role):
    options = {
        'check': directives.unchanged,
        'right': directives.unchanged,
        'style': directives.unchanged,
    }
    content = True

    @ext.report_exceptions
    def run(self):
        node = self.node_type()
        self.set_source_info(node)
        node['role'] = self.name
        node['text'] = self.text
        node['classes'] = self.options['classes'][:]
        if v := self.options.get('check'): node['check'] = v
        set_style(node, self.options)
        self.update_node(node)
        return [node], []

    def update_node(self, node): pass


def set_style(node, options):
    style = []
    if (v := options.get('right', 'false').strip()) != 'false':
        node['classes'].append('right')
        if v not in ('', 'true'):
            if not v.endswith(';'): v += ';'
            style.append(v)
    if v := options.get('style', '').strip():
        if not v.endswith(';'): v += ';'
        style.append(v)
    if style: node['style'] = ' '.join(style)


def attributes(node):
    attrs = {'data-text': ext.to_base64(node['text'])}
    if v := node.get('style'): attrs['style'] = v
    if v := node.get('role'): attrs['data-role'] = v
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
    raise nodes.SkipNode()


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
    raise nodes.SkipNode()


class QuizCheck(docutils.SphinxDirective):
    optional_arguments = 1
    option_spec = {
        'class': ext.opt_classes,
        'hint': directives.unchanged,
        'multi': ext.opt_bool,
        'randomize': ext.opt_bool,
        'right': directives.unchanged,
        'style': directives.unchanged,
    }
    has_content = True

    @ext.report_exceptions
    def run(self):
        children = self.parse_content_to_nodes()
        if len(children) != 1 or not isinstance(children[0], nodes.bullet_list):
            raise Exception("{quiz-check}: Must contain a bullet list")
        node = quiz_group('', *(quiz_check('', *c) for c in children[0]))
        self.set_source_info(node)
        self.state.document.set_id(node)
        if self.arguments: node['name'] = self.arguments[0]
        node['role'] = self.name
        node['type'] = 'checkbox' if self.options.get('multi', False) \
                       else 'radio'
        if v := self.options.get('hint'): node['hint'] = v
        if self.options.get('randomize', False): node['randomize'] = True
        # Find and remove ':' prefixes that tag solutions.
        pid = node['ids'][0]
        for i, c in enumerate(node):
            c['ids'].append(f'{pid}-{i}')
            n = c.next_node(nodes.Text)
            if (sol := n.startswith(':')):
                p = n.parent
                if len(n) > 1:
                    p.replace(n, n.__class__(n[1:]))
                else:
                    p.remove(n)
                    if not p.children: p.parent.remove(p)
            c['text'] = '1' if sol else '0'
        node['classes'] += self.options.get('class', [])
        set_style(node, self.options)
        return [node]


def visit_quiz_group(self, node):
    attrs = {'data-role': node['role']}
    if v := node.get('hint'): attrs['data-hint'] = v
    if node.get('randomize'): attrs['data-randomize'] = ''
    if v := node.get('style'): attrs['style'] = v
    self.body.append(self.starttag(node, 'ul', classes=['tdoc-quiz-group'],
                                   **attrs))


def depart_quiz_group(self, node):
    self.body.append('</ul>\n')


def visit_quiz_check(self, node):
    self.body.append('<li>')
    self.body.append(self.starttag(
        node, 'input', suffix='', type=node.parent['type'],
        classes=['tdoc-quiz-field'], name=node.parent['ids'][0],
        **attributes(node)))
    self.body.append(f'<label for="{node['ids'][0]}">\n')


def depart_quiz_check(self, node):
    self.body.append('</label></li>\n')
