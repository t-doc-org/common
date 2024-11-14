# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import pathlib
import re
import zipfile

from docutils import nodes, statemachine
from docutils.parsers.rst import directives
from sphinx.directives import code
from sphinx.util import logging, osutil

from . import __version__, format_attrs, format_data_attrs, report_exceptions

_log = logging.getLogger(__name__)
_base = pathlib.Path(__file__).absolute().parent


def setup(app):
    app.add_node(exec, html=(visit_exec, depart_exec))
    app.add_directive('exec', Exec)
    app.connect('doctree-resolved', check_references)
    app.connect('html-page-context', add_js)
    app.connect('write-started', write_static_files)
    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


class exec(nodes.literal_block): pass


def visit_exec(self, node):
    try:
        return self.visit_literal_block(node)
    except nodes.SkipNode:
        after = node.get('after')
        then = node.get('then')
        def subst(m): return f'{m.group(1)} {attrs}{m.group(2)}'
        attrs = format_data_attrs(self,
            after=' '.join(after) if after else None,
            output_style=node.get('output-style'),
            then=' '.join(then) if then else None,
            when=node.get('when'))
        if attrs:
            self.body[-1] = div_attrs_re.sub(subst, self.body[-1], 1)
        if attrs := format_attrs(self, style=node.get('style')):
            self.body[-1] = pre_attrs_re.sub(subst, self.body[-1], 1)
        raise


def depart_exec(self, node):
    return self.depart_literal_block(node)


class Exec(code.CodeBlock):
    languages = {'html', 'python', 'sql'}

    option_spec = code.CodeBlock.option_spec | {
        'after': directives.class_option,
        'editable': directives.flag,
        'include': directives.unchanged_required,
        'output-style': directives.unchanged,
        'style': directives.unchanged,
        'then': directives.class_option,
        'when': lambda c: directives.choice(c, ('click', 'load', 'never')),
    }

    @staticmethod
    def find_nodes(doctree):
        nodes = {}
        for node in doctree.findall(exec):
            nodes.setdefault(node['language'], []).append(node)
        return nodes

    @report_exceptions
    def run(self):
        if include := self.options.get('include'):
            content = statemachine.StringList()
            for path in include.split():
                rel_path, path = self.env.relfn2path(path)
                self.env.note_dependency(rel_path)
                text = pathlib.Path(path).read_text(self.config.source_encoding)
                content.extend(statemachine.StringList(
                    initlist=text.splitlines(),
                    source=path))
            self.content[:0] = content
        res = super().run()
        for node in res:
            for n in node.findall(nodes.literal_block):
                self._update_node(node)
        return res

    def _update_node(self, node):
        if (lang := node['language']) not in self.languages:
            raise Exception(f"{{exec}}: Unsupported language: {lang}")
        node.__class__ = exec
        node.tagname = node.__class__.__name__
        node['classes'] += ['tdoc-exec']
        if v := self.options.get('after'): node['after'] = v
        if v := self.options.get('output-style'): node['output-style'] = v
        if v := self.options.get('style'): node['style'] = v
        if v := self.options.get('then'): node['then'] = v
        node['when'] = self.options.get('when', 'click')
        if 'editable' in self.options: node['classes'] += ['tdoc-editable']


def check_references(app, doctree, docname):
    for lang, nodes in Exec.find_nodes(doctree).items():
        names = set()
        for node in nodes:
            names.update(node['names'])
        for node in nodes:
            check_refs(node, names, 'after', doctree)
            check_refs(node, names, 'then', doctree)


def check_refs(node, names, typ, doctree):
    for ref in node.get(typ, ()):
        if ref not in names:
            doctree.reporter.error(
                f"{{exec}} {lang}: Unknown :{typ}: reference: {ref}",
                base_node=node)


div_attrs_re = re.compile(r'(?s)^(<div[^>]*)(>.*)$')
pre_attrs_re = re.compile(r'(?s)^(.*<pre[^>]*)(>.*)$')


def add_js(app, page, template, context, doctree):
    if doctree:
        for lang in sorted(Exec.find_nodes(doctree)):
            app.add_js_file(f'tdoc/exec-{lang}.js', type='module')


def write_static_files(app, builder):
    if builder.format != 'html': return

    # Package all files under tdoc/common/python into a .zip, below tdoc/, and
    # write it to _static/tdoc.
    client = _base / 'python'
    rel = lambda p: p.relative_to(client)
    static = builder.outdir / '_static' / 'tdoc'
    osutil.ensuredir(static)
    with zipfile.ZipFile(static / 'exec-python.zip', mode='x') as f:
        f.mkdir('tdoc')
        for root, dirs, files in client.walk():
            dirs.sort()
            for dn in dirs:
                f.mkdir(f'tdoc/{rel(root / dn)}')
            files.sort()
            for fn in files:
                path = root / fn
                data = path.read_bytes()
                ct = zipfile.ZIP_DEFLATED if data else zipfile.ZIP_STORED
                f.writestr(zipfile.ZipInfo(f'tdoc/{rel(path)}'),
                           data, compress_type=ct, compresslevel=9)
