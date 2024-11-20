# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import pathlib

from docutils import nodes
from sphinx import errors
from sphinx.util import docutils, logging

from . import __version__

_log = logging.getLogger(__name__)


def setup(app):
    app.add_role('num', Num())
    app.add_enumerable_node(num, 'num', lambda n: True,
                            html=(visit_num, depart_num))
    app.connect('config-inited', update_numfig_format)
    app.connect('doctree-resolved', update_num_nodes)
    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


class NoNum:
    def __contains__(self, value): return False
    def __mod__(self, other): return ''


def update_numfig_format(app, config):
    # Disable numbering by default for all standard enumerable node types except
    # 'section', and set the default format for 'num'.
    numfig_format = config.numfig_format
    for k in ('code-block', 'figure', 'section', 'table'):
        if numfig_format.setdefault(k, k == 'section') is True:
            del numfig_format[k]
    numfig_format.setdefault('num', '%s')
    print(numfig_format)
    for k, v in numfig_format.items():
        if v is False:
            if k == 'section':
                raise errors.ConfigError(
                    f"numfig_format: Numbering cannot be disabled for '{k}'")
            numfig_format[k] = NoNum()


class Num(docutils.ReferenceRole):
    def run(self):
        node = num()
        node['names'].append(nodes.fully_normalize_name(self.target))
        self.inliner.document.note_explicit_target(node, node)
        node['title'] = self.title if self.has_explicit_title else '%s'
        return [node], []


class num(nodes.Inline, nodes.TextElement): pass


def update_num_nodes(app, doctree, docname):
    for node, text in find_num(app.env, doctree, docname):
        del node['title']
        node += [text]

    # TOCs are extracted on doctree-read, as a transform with priority=880,
    # while toc_fignumbers are only assigned later, as a post-transform, shortly
    # before doctree-resolved. So the num nodes in the TOCs must be updated
    # separately. Replace the node by its text altogether, to avoid duplicate
    # 'id' attributes.
    for node, text in find_num(app.env, app.env.tocs[docname], docname):
        node.parent.replace(node, text)


def find_num(env, doctree, docname):
    fignumbers = env.toc_fignumbers.get(docname, {}).get('num')
    for node in doctree.findall(num):
        if fignumbers is None:
            raise errors.ConfigError(":num: node found, but numfig is disabled")
        numbers = fignumbers[node['ids'][0]]
        num_str = '.'.join(map(str, numbers))
        yield node, nodes.Text(node['title'] % num_str)


def visit_num(self, node):
    self.body.append(self.starttag(node, 'span', suffix=''))


def depart_num(self, node):
    self.body.append('</span>')
