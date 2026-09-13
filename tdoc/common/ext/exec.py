# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import pathlib
import zipfile

from docutils import nodes, statemachine
from docutils.parsers.rst import directives
import pyjson5
from sphinx.directives import code
from sphinx.util import display, docutils, logging, osutil

from .. import ext

_log = logging.getLogger(__name__)
_base = pathlib.Path(__file__).parent.resolve().parent


def setup(app):
    app.add_directive('exec', Exec)
    app.add_node(exec, html=(visit_exec, None))
    app.add_env_collector(ext.UniqueChecker('exec-editor',
        lambda doctree: ((n, n.get('editor')) for n in doctree.findall(exec)),
        lambda v: f"{{exec}}: Duplicate :editor: ID: {v}"))
    app.connect('doctree-resolved', check_nodes)
    app.connect('tdoc-html-page-config', set_html_page_config)
    app.connect('html-page-context', add_js)
    app.add_config_value('tdoc_python_modules', [], 'html', list)
    app.connect('config-inited', set_default_metadata)
    app.connect('config-inited', set_python_modules)
    app.connect('write-started', write_static_files)
    return ext.setup_result


class Exec(docutils.SphinxDirective):
    required_arguments = 1
    has_content = True
    option_spec = ext.editor_options | {
        'after': ext.opt_words,
        'caption': directives.unchanged_required,
        'class': ext.opt_classes,
        'console-style': directives.unchanged,
        'env': directives.unchanged,
        'include': directives.unchanged_required,
        'name': directives.unchanged,
        'output-style': directives.unchanged,
        'reset': lambda c: directives.choice(c, ('show', 'hide', 'auto')),
        'style': directives.unchanged,
        'then': ext.opt_words,
        'when': ext.opt_set('click', 'load'),
    }

    @staticmethod
    def find_nodes(doctree):
        nodes = {}
        for node in doctree.findall(exec):
            nodes.setdefault(node['runner'], []).append(node)
        return nodes

    @ext.report_exceptions
    def run(self):
        content = statemachine.StringList()
        if include := self.options.get('include'):
            for path in include.split():
                rel_path, path = self.env.relfn2path(path)
                self.env.note_dependency(rel_path)
                text = pathlib.Path(path).read_text(self.config.source_encoding)
                content.extend(statemachine.StringList(
                    initlist=text.splitlines(),
                    source=path))
        content += self.content
        text = '\n'.join(content)

        node = exec(text, text)
        self.set_source_info(node)
        if v := self.options.get('name'): node['cname'] = v
        if v := self.options.get('after'): node['after'] = v
        node['classes'] += self.options.get('class', [])
        if v := self.options.get('console-style'): node['console-style'] = v
        ext.parse_editor_options(self.options, node)
        node['env'] = self.options.get('env', '').strip()
        if v := self.options.get('output-style'): node['output-style'] = v
        if (v := self.options.get('reset')) and v != 'hide': node['reset'] = v
        node['runner'] = self.arguments[0]
        if v := self.options.get('style'): node['style'] = v
        if v := self.options.get('then'): node['then'] = v
        node['when'] = self.options.get('when', {'click'})

        if v := self.options.get('caption'):
            node = code.container_wrapper(self, node, v)
        self.add_name(node)  # Removes the 'name' option
        return [node]


class exec(nodes.literal_block): pass


def check_nodes(app, doctree, docname):
    md = ext.meta(app.env, docname, 'exec', {})
    for runner, nodes in Exec.find_nodes(doctree).items():
        # Check references.
        names = {n for node in nodes if (n := node.get('cname')) is not None}
        for node in nodes:
            check_refs(node, names, runner, 'after', doctree)
            check_refs(node, names, runner, 'then', doctree)

        # Check runner.
        if (cfg := md.get(runner)) is None:
            for node in nodes:
                doctree.reporter.error(
                    f"{{exec}}: Unknown runner: {runner}", base_node=node)


def check_refs(node, names, runner, typ, doctree):
    for ref in node.get(typ, ()):
        if ref not in names:
            doctree.reporter.error(
                f"{{exec}} {runner}: Unknown :{typ}: reference: {ref}",
                base_node=node)


def set_html_page_config(app, docname, config, doctree):
    if docname is None or doctree is None: return
    cfg = {}
    md = ext.meta(app.env, docname, 'exec', {})
    for runner, nodes in Exec.find_nodes(doctree).items():
        c = cfg[runner] = md.get(runner, {}).copy()
        if envs := set(n['env'] for n in nodes if n['when']):
            c['_envs'] = sorted(envs)
    if cfg: config['exec'] = cfg


def add_js(app, docname, template, context, doctree):
    if doctree:
        for runner in sorted(Exec.find_nodes(doctree)):
            app.add_js_file(f'tdoc/exec-{runner}.js', type='module')


_default_metadata = {
    'exec': {
        'html': {},
        'micropython': {},
        'python': {},
        'sql': {},
    },
}

def set_default_metadata(app, config):
    ext.merge_dict(app.config.metadata, _default_metadata, override=False)


def set_python_modules(app, config):
    if '_python' not in config.tdoc_python_modules \
            and (app.confdir / '_python').exists():
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
            add_modules(f, _base / 'python')
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


def visit_exec(self, node):
    linenos = node.get('linenos', False)
    self.body.append(self.starttag(
        node, 'tdoc-exec', '', CLASS='highlight-text notranslate',
        **ext.tag_attrs(
            after=' '.join(node.get('after', ())) or None,
            console_style=node.get('console-style'),
            editor=node.get('editor'),
            env=node['env'] if node['when'] else None,
            linenos='' if linenos else None,
            name=node.get('cname'),
            output_style=node.get('output-style'),
            reset=node.get('reset'),
            runner=node['runner'],
            then=' '.join(node.get('then', ())) or None,
            when=' '.join(sorted(node['when'])) or None)))
    self.body.append(self.highlighter.highlight_block(
        node.rawsource, 'text', location=node,
        linenos='inline' if linenos else False,
        **ext.kwfilter(prestyles=node.get('style'))))
    self.body.append('</tdoc-exec>\n')
    raise nodes.SkipNode()
