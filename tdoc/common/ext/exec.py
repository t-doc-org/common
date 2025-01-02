# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import pathlib
import re
import zipfile

from docutils import nodes, statemachine
from docutils.parsers.rst import directives
from sphinx.directives import code
from sphinx.environment import collectors
from sphinx.util import display, logging, osutil

from . import __version__, format_attrs, format_data_attrs, names_option, \
    report_exceptions

_log = logging.getLogger(__name__)
_base = pathlib.Path(__file__).absolute().parent.parent


def setup(app):
    app.add_directive('exec', Exec)
    app.add_node(exec, html=(visit_exec, depart_exec))
    app.connect('builder-inited', ExecCollector.init)
    app.add_env_collector(ExecCollector)
    app.connect('doctree-resolved', check_references)
    app.connect('html-page-context', add_js)
    app.add_config_value('tdoc_python_modules', [], 'html')
    app.connect('config-inited', set_python_modules)
    app.connect('write-started', write_static_files)
    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


class Exec(code.CodeBlock):
    languages = {'html', 'python', 'sql'}

    option_spec = code.CodeBlock.option_spec | {
        'after': names_option,
        'editor': directives.unchanged,
        'include': directives.unchanged_required,
        'output-style': directives.unchanged,
        'style': directives.unchanged,
        'then': names_option,
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
        if (v := self.options.get('editor')) is not None: node['editor'] = v


class exec(nodes.literal_block): pass


class ExecCollector(collectors.EnvironmentCollector):
    @staticmethod
    def init(app):
        app.env.tdoc_editors = {}  # ID => (docname, location)

    def clear_doc(self, app, env, docname):
        editors = env.tdoc_editors
        for eid in list(editors):
            if editors[eid][0] == docname: del editors[eid]

    def merge_other(self, app, env, docnames, other):
        editors = env.tdoc_editors
        for eid, (dn, loc) in other.tdoc_editors.items():
            if dn not in docnames: continue
            if eid not in editors:
                editors[eid] = (dn, loc)
            else:
                _log.error(f"{{exec}}: Duplicate :editor: ID: {eid}",
                           location=loc)

    def process_doc(self, app, doctree):
        editors = app.env.tdoc_editors
        for node in doctree.findall(exec):
            if not (eid := node.get('editor')): continue
            if eid not in editors:
                editors[eid] = (app.env.docname, (node.source, node.line))
            else:
                doctree.reporter.error(
                    f"{{exec}}: Duplicate :editor: ID: {eid}", base_node=node)


def check_references(app, doctree, docname):
    for lang, nodes in Exec.find_nodes(doctree).items():
        names = set()
        for node in nodes:
            names.update(node['names'])
        for node in nodes:
            check_refs(node, names, lang, 'after', doctree)
            check_refs(node, names, lang, 'then', doctree)


def check_refs(node, names, lang, typ, doctree):
    for ref in node.get(typ, ()):
        if ref not in names:
            doctree.reporter.error(
                f"{{exec}} {lang}: Unknown :{typ}: reference: {ref}",
                base_node=node)


def add_js(app, page, template, context, doctree):
    if doctree:
        for lang in sorted(Exec.find_nodes(doctree)):
            app.add_js_file(f'tdoc/exec-{lang}.js', type='module')


def set_python_modules(app, config):
    config.tdoc_python_modules.insert(0, str(_base / 'python'))
    if '_python' not in config.tdoc_python_modules:
        config.tdoc_python_modules.append('_python')


def write_static_files(app, builder):
    if builder.format != 'html': return

    # Package python modules into a .zip and write it to _static/tdoc.
    with display.progress_message("packaging Python modules..."):
        static = builder.outdir / '_static' / 'tdoc'
        osutil.ensuredir(static)
        zpath = static / 'exec-python.zip'
        zpath.unlink(missing_ok=True)
        with zipfile.ZipFile(zpath, mode='x') as f:
            for mpath in app.config.tdoc_python_modules:
                add_modules(f, app.confdir / mpath)


def add_modules(f, mpath):
    if not mpath.exists(): return
    rel = lambda p: p.relative_to(mpath)
    def on_error(e): raise e
    for root, dirs, files in mpath.walk(on_error=on_error):
        try: dirs.remove('__pycache__')
        except ValueError: pass
        dirs.sort()
        for dn in dirs: f.mkdir(str(rel(root / dn)))
        files.sort()
        for fn in files:
            path = root / fn
            data = path.read_bytes()
            ct = zipfile.ZIP_DEFLATED if data else zipfile.ZIP_STORED
            f.writestr(zipfile.ZipInfo(str(rel(path))), data, compress_type=ct,
                       compresslevel=9)


div_attrs_re = re.compile(r'(?s)^(<div[^>]*)(>.*)$')
pre_attrs_re = re.compile(r'(?s)^(.*<pre[^>]*)(>.*)$')


def visit_exec(self, node):
    try:
        return self.visit_literal_block(node)
    except nodes.SkipNode:
        nameids = node.document.nameids
        after = [nameids[n] for n in node.get('after', ())]
        then = [nameids[n] for n in node.get('then', ())]
        def subst(m): return f'{m.group(1)} {attrs}{m.group(2)}'
        attrs = format_data_attrs(self,
            after=' '.join(after),
            editor=node.get('editor'),
            output_style=node.get('output-style'),
            then=' '.join(then),
            when=node.get('when'))
        if attrs:
            self.body[-1] = div_attrs_re.sub(subst, self.body[-1], 1)
        if attrs := format_attrs(self, style=node.get('style')):
            self.body[-1] = pre_attrs_re.sub(subst, self.body[-1], 1)
        raise


def depart_exec(self, node):
    return self.depart_literal_block(node)
