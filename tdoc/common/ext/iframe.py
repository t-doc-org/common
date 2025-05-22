# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.util import docutils, logging

from . import __version__, report_exceptions

_log = logging.getLogger(__name__)


def setup(app):
    app.add_node(iframe, html=(visit_iframe, None))
    app.add_directive('iframe', IFrame)
    app.add_directive('youtube', YouTube)
    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


class iframe(nodes.Body, nodes.Element): pass


_attr_names = ['allow', 'referrerpolicy', 'sandbox', 'style', 'title']

def visit_iframe(self, node):
    attrs = {}
    if node['credentialless']: attrs['credentialless'] = ''
    for k in _attr_names:
        if (v := node.get(k)) is not None: attrs[k] = v
    attrs.setdefault('allow', 'autoplay; clipboard-write; encrypted-media; '
                     'fullscreen; picture-in-picture; screen-wake-lock; '
                     'web-share')
    self.body.append(self.starttag(
        node, 'iframe', suffix='', classes=['tdoc'], src=node['src'], **attrs))
    self.body.append('</iframe>\n')
    raise nodes.SkipNode


class IFrame(docutils.SphinxDirective):
    required_arguments = 1
    option_spec = {
        'allow': directives.unchanged,
        'class': directives.class_option,
        'credentialful': directives.flag,
        'referrerpolicy': directives.unchanged,
        'sandbox': directives.unchanged,
        'style': directives.unchanged,
        'title': directives.unchanged,
    }

    @report_exceptions
    def run(self):
        node = iframe()
        self.set_source_info(node)
        node['src'] = self.get_src(self.arguments[0])
        node['classes'] += self.options.get('class', [])
        node['credentialless'] = 'credentialful' not in self.options
        for k in _attr_names:
            if (v := self.options.get(k)) is not None: node[k] = v
        return [node]

    def get_src(self, arg):
        return arg


class YouTube(IFrame):
    def get_src(self, arg):
        if '/' not in arg: return f'https://www.youtube.com/embed/{arg}'
        return arg
