# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import datetime
from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.util import docutils, logging

from . import __version__, report_exceptions, UniqueChecker
from .. import util

_log = logging.getLogger(__name__)


def setup(app):
    app.add_directive('poll', Poll)
    app.add_node(poll, html=(visit_poll, depart_poll))
    app.add_node(answers, html=(visit_answers, depart_answers))
    app.add_node(answer, html=(visit_answer, depart_answer))
    app.add_env_collector(UniqueChecker('poll-id',
        lambda doctree: ((n, n['id']) for n in doctree.findall(poll)),
        "{poll}: Duplicate poll ID"))
    app.connect('html-page-context', add_js)
    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


class Poll(docutils.SphinxDirective):
    required_arguments = 1
    option_spec = {
        'mode': lambda c: directives.choice(c, ('single', 'multi')),
        'number': lambda c: directives.choice(c,
            ('none', 'decimal', 'lower-alpha', 'upper-alpha')),
        'close-after': directives.unchanged,
        'class': directives.class_option,
    }
    has_content = True

    @report_exceptions
    def run(self):
        children = self.parse_content_to_nodes()
        if any(True for c in children for n in c.findall(poll)):
            raise Exception("{poll}: Must not contain {poll}")
        if not children or not isinstance(children[-1], nodes.bullet_list):
            raise Exception("{poll}: Must end with a bullet list")
        ans = answers('', *(answer('', *a) for a in children[-1]))
        # Find and remove ':' prefixes that tag solutions.
        for a in ans:
            for n in a.findall(nodes.Text):
                if n.startswith(':'):
                    a['solution'] = True
                    p = n.parent
                    if len(n) > 1:
                        p.replace(n, n.__class__(n[1:]))
                    else:
                        p.remove(n)
                        if not p.children: p.parent.remove(p)
                break
        node = poll('', *children[:-1], ans)
        self.set_source_info(node)
        node['id'] = self.arguments[0]
        node['mode'] = self.options.get('mode', 'single')
        if (v := self.options.get('close-after', '15m')) != 'never':
            node['close-after'] = util.parse_duration(v)
        node['number'] = self.options.get('number', 'upper-alpha')
        node['classes'] += self.options.get('class', [])
        return [node]


class poll(nodes.Body, nodes.Element): pass
class answers(nodes.Sequential, nodes.Element): pass
class answer(nodes.Part, nodes.Element): pass


def visit_poll(self, node):
    kwargs = {'data-id': node['id'], 'data-mode': node['mode']}
    if (v := node.get('close-after')) is not None:
        kwargs['data-close-after'] = v // datetime.timedelta(milliseconds=1)
    self.body.append(self.starttag(
        node, 'div', suffix='', classes=['tdoc-poll', f'num-{node['number']}'],
        **kwargs))


def depart_poll(self, node):
    self.body.append('</div>\n')


def visit_answers(self, node):
    cols = 5 if node.parent['number'] != 'none' else 4
    self.body.append(f"""
<table class="tdoc-poll-answers table">\
<thead><tr><th class="tdoc-poll-header" colspan="{cols}"><div>\
<div class="stats">\
<div class="voters" title="Voters">\
<span class="tdoc fa-user"></span><span></span></div>\
<div class="votes" title="Votes">\
<span class="tdoc fa-check-to-slot"></span><span></span></div>\
<div class="closed" title="The poll is closed">\
<span class="tdoc fa-lock"></span></div>\
</div><div class="controls">\
<button class="tdoc-open fa-play"></button>\
<button class="tdoc-results fa-eye"></button>\
<button class="tdoc-solutions fa-check"></button>\
<button class="tdoc-clear fa-trash"\
 title="Clear votes (Ctrl+click to clear all)"></button>\
</div></div></th></thead><tbody>\
""")


def depart_answers(self, node):
    self.body.append('</tbody></table>')


def visit_answer(self, node):
    num = '<td class="tdoc-poll-num"></td>' \
          if node.parent.parent['number'] != 'none' else ''
    s = ' s' if node.get('solution') else ''
    self.body.append(f"""\
<tr>{num}\
<td class="tdoc-poll-sel{s}"><span class="tdoc fa-circle-check"></span></td>\
<td class="tdoc-poll-ans">\
""")


def depart_answer(self, node):
    self.body.append("""\
</td><td class="tdoc-poll-cnt"></td><td class="tdoc-poll-pct"></td></tr>\
""")


def add_js(app, page, template, context, doctree):
    if doctree and any(doctree.findall(poll)):
        app.add_js_file('tdoc/poll.js', type='module')
