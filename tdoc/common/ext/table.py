# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

from docutils import nodes
from docutils.parsers.rst import directives
from mdit_py_plugins.attrs import parse
from sphinx.util import docutils, logging

from . import __version__, report_exceptions

_log = logging.getLogger(__name__)


def setup(app):
    app.add_directive('flex-table', FlexTable)
    app.add_node(flex_table, html=(visit_flex_table, depart_flex_table))
    app.add_node(flex_row, html=(visit_flex_row, depart_flex_row))
    app.add_node(flex_cell, html=(visit_flex_cell, depart_flex_cell))
    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


class FlexTable(docutils.SphinxDirective):
    option_spec = {
        'class': directives.class_option,
        'name': directives.unchanged,
    }
    has_content = True

    @report_exceptions
    def run(self):
        table = flex_table()
        self.set_source_info(table)
        self.add_name(table)
        table['classes'] += self.options.get('class', [])
        for i, line in enumerate(self.content, 1):
            lineno = self.lineno + self.content_offset + i
            try:
                row = self.parse_row(line, lineno)
            except Exception as e:
                return [self.state.document.reporter.error(e, line=lineno)]
            table.append(row)
        return [table]

    def parse_row(self, line, lineno):
        row = flex_row()
        start = skip_whitespace(line, 0, len(line))
        attrs, start = parse_attrs(line, start, len(line), row)
        if (t := attrs.pop('t', None)) == 'h':
            row['type'] = 'thead'
        elif t == 'b':
            row['type'] = 'tbody'
        elif t is not None:
            raise Exception(f"{{flex-table}} Invalid row type: {t}")
        if attrs:
            raise Exception("{{flex-table}} Unknown row attributes: "
                            f"{' '.join(sorted(attrs.keys()))}")
        while True:
            cell, start = self.parse_cell(line, lineno, start)
            if cell is None: break
            row.append(cell)
        return row

    def parse_cell(self, line, lineno, start):
        if start >= len(line): return None, len(line)
        if line[start] != '|':
            raise Exception("{flex-table} Row must start with '|'")
        start += 1
        end = start
        while end < len(line) and not (
                line[end] == '|'
                and trailing_backslashes(line, start, end) % 2 == 0):
            end += 1
        cell = flex_cell()
        attrs, start = parse_attrs(line, start, end, cell)
        if (t := attrs.pop('t', None)) == 'h':
            cell['tag'] = 'th'
        elif t == 'd':
            cell['tag'] = 'td'
        elif t is not None:
            raise Exception(f"{{flex-table}} Invalid cell type: {t}")
        if (v := attrs.pop('cols', None)) is not None: cell['cols'] = v
        if (v := attrs.pop('rows', None)) is not None: cell['rows'] = v
        cell['attrs'] = attrs
        # BUG(myst-pasrser): The line number reported in errors is off by 1.
        content, msgs = self.parse_inline(line[start: end], lineno=lineno - 1)
        cell += content
        cell += msgs
        return cell, end


def skip_whitespace(text, start, end):
    while start < end and text[start].isspace(): start += 1
    return start


def trailing_backslashes(text, start, end):
    end -= 1
    i = end
    while i >= start and text[i] == '\\': i -= 1
    return end - i


def parse_attrs(text, start, end, node):
    if start >= end or text[start] != '{': return {}, start
    cnt, attrs = parse.parse(text[start: end])
    if text[start + cnt] != '}':
        raise Exception("{flex-table} Invalid attributes")
    if (v := attrs.pop('id', None)) is not None: node['ids'].append(v)
    if (v := attrs.pop('class', '').split()): node['classes'].extend(v)
    return attrs, start + cnt + 1


class flex_table(nodes.General, nodes.Element): pass


def visit_flex_table(self, node):
    self.context.append(None)
    self.body.append(self.starttag(node, 'table', ''))


def depart_flex_table(self, node):
    if (prev_typ := self.context[-1]) is not None:
        self.body.append(f'</{prev_typ}>')
    self.context.pop()
    self.body.append('</table>\n')


class flex_row(nodes.Part, nodes.Element): pass


def visit_flex_row(self, node):
    prev_typ = self.context[-1]
    typ = node.get('type', prev_typ if prev_typ is not None else 'tbody')
    if typ != prev_typ:
        if prev_typ is not None: self.body.append(f'</{prev_typ}>')
        self.body.append(f'<{typ}>')
        self.context[-1] = typ
    self.body.append(self.starttag(node, 'tr'))


def depart_flex_row(self, node):
    self.body.append('</tr>')


class flex_cell(nodes.Part, nodes.Element): pass


def visit_flex_cell(self, node):
    tag = node.get('tag', 'th' if self.context[-1] == 'thead' else 'td')
    attrs = {}
    if (v := node.get('cols')) is not None: attrs['colspan'] = v
    if (v := node.get('rows')) is not None: attrs['rowspan'] = v
    self.body.append(self.starttag(node, tag, '', **attrs))


def depart_flex_cell(self, node):
    self.body.append(f'</{node.get('tag', 'td')}>\n')
