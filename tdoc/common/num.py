# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import pathlib

from docutils import nodes
from sphinx.util import docutils, logging

from . import __version__

_log = logging.getLogger(__name__)

# TODO: Selectively disable entries in numfig_format by setting the dict values
#       to an object implementing __mod__() and returning an empty string
# TODO: Substitute None in numfig_format with NoNum

class NoNum:
    # TODO: Differentiate between rendering for {numref} or for a caption?
    #       Doesn't make sense to have {numref} if the number is never displayed
    def __contains__(self, value): return False
    def __mod__(self, other): return ''


def setup(app):
    app.add_role('num', Num())
    app.add_enumerable_node(num, 'num', get_num_title, html=(visit_num, depart_num))
    app.connect('doctree-resolved', update_num_nodes)
    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


class Num(docutils.ReferenceRole):
    def run(self):
        node = num()
        node['names'].append(nodes.fully_normalize_name(self.target))
        self.inliner.document.note_explicit_target(node, node)
        node['title'] = self.title if self.has_explicit_title else '%s'
        return [node], []


class num(nodes.Inline, nodes.TextElement): pass


def get_num_title(node):
    return True  # The actual value doesn't matter, as long as it's truthy


def update_num_nodes(app, doctree, docname):
    add_num_content(app.env, doctree, docname)
    # TOCs are extracted on doctree-read, as a transform with priority=880,
    # while toc_fignumbers are only assigned later, as a post-transform, shortly
    # before doctree-resolved. So the num nodes in the TOCs must be updated
    # separately.
    add_num_content(app.env, app.env.tocs[docname], docname)


def add_num_content(env, doctree, docname):
    fignumbers = env.toc_fignumbers.get(docname, {})
    for node in doctree.findall(num):
        numbers = fignumbers['num'][node['ids'][0]]
        num_str = '.'.join(map(str, numbers))
        node += [nodes.Text(node['title'] % num_str)]


def visit_num(self, node):
    # When the role is used in a heading, it can be rendered multiple times,
    # e.g. for the document and for the TOC. Only the document render must
    # include the ID.
    render_doc = pathlib.Path(node.document['source']).exists()
    if render_doc: self.body.append(self.starttag(node, 'span', suffix=''))


def depart_num(self, node):
    render_doc = pathlib.Path(node.document['source']).exists()
    if render_doc: self.body.append('</span>')
