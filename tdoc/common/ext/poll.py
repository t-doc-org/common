# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.util import docutils, logging

from . import __version__, report_exceptions

_log = logging.getLogger(__name__)


def setup(app):
    app.add_directive('poll', Poll)
    app.add_node(poll, html=(visit_poll, depart_poll))
    app.add_node(answers, html=(visit_answers, depart_answers))
    app.add_node(answer, html=(visit_answer, depart_answer))
    app.connect('html-page-context', add_js)
    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


# TODO: Change :multi: into "":mode: single", ":mode: multi"
# TODO: Hide the vote count for non-:multi: polls
# TODO: Auto-close polls after N minutes of inactivity
# TODO: Check for duplicate poll IDs

class Poll(docutils.SphinxDirective):
    option_spec = {
        'id': directives.unchanged,
        'multi': directives.flag,
        'class': directives.class_option,
    }
    has_content = True

    @report_exceptions
    def run(self):
        children = self.parse_content_to_nodes()
        if not children or not isinstance(children[-1], nodes.bullet_list):
            raise Exception("{poll}: Must end with a bullet list")
        ans = answers('', *(answer('', *a) for a in children[-1]))
        node = poll('', *children[:-1], ans)
        self.set_source_info(node)
        if (v := self.options.get('id')) is None:
            raise Exception("{poll}: Missing :id:")
        node['id'] = v
        cls = node['classes']
        if 'multi' in self.options: cls += ['multi']
        cls += self.options.get('class', [])
        return [node]


class poll(nodes.Body, nodes.Element): pass
class answers(nodes.Sequential, nodes.Element): pass
class answer(nodes.Part, nodes.Element): pass


def visit_poll(self, node):
    self.body.append(self.starttag(
        node, 'div', suffix='', classes=['tdoc-poll'],
        **{'data-id': node['id']}))


def depart_poll(self, node):
    self.body.append('</div>\n')


def visit_answers(self, node):
    self.body.append("""
<table class="tdoc-poll-answers table">\
<thead><tr><th class="tdoc-poll-header" colspan="4"><div><div>\
<div class="voters" title="Voters">\
<span class="tdoc fa-user"></span><span></span></div>\
<div class="votes" title="Votes">\
<span class="tdoc fa-check-to-slot"></span><span></span></div>\
<div class="closed" title="The poll is closed">\
<span class="tdoc fa-lock"></span></div>\
</div><div class="controls">\
<button class="tdoc-open fa-play"></button>\
<button class="tdoc-show fa-eye"></button>\
<button class="tdoc-clear fa-trash" title="Clear votes"></button>\
</div></div></th></thead><tbody>\
""")


def depart_answers(self, node):
    self.body.append('</tbody></table>')


def visit_answer(self, node):
    self.body.append('<tr><td class="tdoc-poll-ans">')


def depart_answer(self, node):
    self.body.append("""\
</td><td class="tdoc-poll-sel"><span class="tdoc fa-circle-check"></span></td>\
<td class="tdoc-poll-cnt"></td><td class="tdoc-poll-pct"></td></tr>\
""")


def add_js(app, page, template, context, doctree):
    if doctree and any(doctree.findall(poll)):
        app.add_js_file('tdoc/poll.js', type='module')
