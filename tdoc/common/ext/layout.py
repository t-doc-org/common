# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import datetime

from docutils import nodes
from docutils.parsers.rst import directives
import markupsafe
from sphinx.util import docutils, logging

from . import __version__, report_exceptions

_log = logging.getLogger(__name__)


def setup(app):
    app.add_directive('block', Block)
    app.add_directive('blocks', Blocks)
    app.add_directive('list-grid', ListGrid)
    app.add_node(block)
    app.add_node(blocks)
    app.add_node(grid, html=(visit_grid, depart_grid))
    app.add_node(grid_cell, html=(visit_grid_cell, depart_grid_cell))
    # Move blocks before TOC extraction in TocTreeCollector.process_doc().
    app.connect('doctree-read', move_blocks, priority=499)
    app.connect('html-page-context', set_html_context)
    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


class Block(docutils.SphinxDirective):
    required_arguments = 1
    has_content = True

    @report_exceptions
    def run(self):
        children = self.parse_content_to_nodes()
        node = block('', *children, type=self.arguments[0])
        self.set_source_info(node)
        return [node]


class Blocks(docutils.SphinxDirective):
    required_arguments = 1
    option_spec = {
        'class': directives.class_option,
    }

    @report_exceptions
    def run(self):
        node = blocks(type=self.arguments[0])
        self.set_source_info(node)
        node['classes'] += self.options.get('class', [])
        return [node]


class block(nodes.Structural, nodes.Element): pass
class blocks(nodes.Structural, nodes.Element): pass


def move_blocks(app, doctree):
    # Extract all blocks and group them by type.
    bm = {}
    for b in doctree.findall(block):
        sect = closest_section(b)
        b.parent.remove(b)
        typ = b['type']
        dsect = nodes.section(names=[f'{typ} {it}' for it in sect['names']],
                              classes=sect['classes'])
        dsect.source, dsect.line = b.source, b.line
        doctree.set_id(dsect)
        if (title := sect.next_node(nodes.title)) is not None:
            dsect.append(title.deepcopy())
        dsect += b.children
        bm.setdefault(typ, []).append(dsect)

    # Replace the destination markers with the extracted blocks.
    done = set()
    for d in doctree.findall(blocks):
        parent = d.parent
        idx = parent.index(d)
        parent.remove(d)
        if (typ := d['type']) in done:
            _log.error(f"Duplicate {{blocks}} directive for type '{typ}'",
                       location=d)
            continue
        if (sects := bm.pop(typ, None)) is not None:
            for sect in sects: sect['classes'] += d['classes']
            parent[idx: idx] = sects
        done.add(typ)

    for typ, sects in sorted(bm.items()):
        _log.warning(f"No {{blocks}} directive for {{block}} type '{typ}'",
                     location=sects[0])


def closest_section(node):
    while node is not None:
        if isinstance(node, nodes.section): return node
        node = node.parent


class ListGrid(docutils.SphinxDirective):
    option_spec = {
        'cell-style': directives.unchanged,
        'class': directives.class_option,
        'style': directives.unchanged,
    }
    has_content = True

    @report_exceptions
    def run(self):
        children = self.parse_content_to_nodes()
        if len(children) != 1 or not isinstance(children[0], nodes.bullet_list):
            raise Exception("{list-grid}: Must contain exactly one bullet list")
        node = grid('', *(grid_cell('', *it.children)
                          for it in children[0].children))
        self.set_source_info(node)
        node['classes'] += self.options.get('class', [])
        if v := self.options.get('style', '').strip(): node['style'] = v
        if v := self.options.get('cell-style', '').strip():
            node['cell-style'] = v
        return [node]


class grid(nodes.Sequential, nodes.Element): pass
class grid_cell(nodes.Part, nodes.Element): pass


def visit_grid(self, node):
    attrs = {}
    if v := node.get('style'): attrs['style'] = v
    self.body.append(self.starttag(node, 'div', classes=['tdoc-grid'], **attrs))


def depart_grid(self, node):
    self.body.append('</div>\n')


def visit_grid_cell(self, node):
    attrs = {}
    if v := node.parent.get('cell-style'): attrs['style'] = v
    self.body.append(self.starttag(node, 'div', '', **attrs))


def depart_grid_cell(self, node):
    self.body.append('</div>\n')


def set_html_context(app, page, template, context, doctree):
    md = app.env.metadata[page]
    if v := md.get('print-styles'): app.add_css_file(v)

    attrs = context['html_attrs']
    if v := app.config.author: attrs['data-tdoc-author'] = v
    attrs['data-tdoc-date'] = datetime.datetime.now().strftime('%Y-%m-%d')
    if v := md.get('subject'): attrs['data-tdoc-subject'] = v
    if context and (v := context.get('title')):
        attrs['data-tdoc-title'] = markupsafe.Markup(v).striptags()
    if v := md.get('page-break-force'):
        if not isinstance(v, (list, tuple)): v = [v]
        attrs['data-tdoc-page-break-force'] = ' '.join(f'h{h}' for h in v)
    if v := md.get('page-break-avoid'):
        if not isinstance(v, (list, tuple)): v = [v]
        attrs['data-tdoc-page-break-avoid'] = ' '.join(f'h{h}' for h in v)
