# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import pathlib
import re
import zipfile

from docutils import nodes, statemachine
from docutils.parsers.rst import directives
from sphinx import config
from sphinx.directives.code import CodeBlock
from sphinx.util import fileutil, logging, osutil

__project__ = 't-doc-common'
__version__ = '0.15'

_common = pathlib.Path(__file__).absolute().parent
_root = _common.parent.parent

_log = logging.getLogger(__name__)

_license_urls = {
    'CC0-1.0': 'https://creativecommons.org/publicdomain/zero/1.0/',
    'CC-BY-4.0': 'https://creativecommons.org/licenses/by/4.0/',
    'CC-BY-SA-4.0': 'https://creativecommons.org/licenses/by-sa/4.0/',
    'CC-BY-NC-4.0': 'https://creativecommons.org/licenses/by-nc/4.0/',
    'CC-BY-NC-SA-4.0': 'https://creativecommons.org/licenses/by-nc-sa/4.0/',
    'CC-BY-ND-4.0': 'https://creativecommons.org/licenses/by-nd/4.0/',
    'MIT': 'https://opensource.org/license/mit',
}

def setup(app):
    app.add_config_value('license', '', 'html')
    app.add_config_value(
        'license_url', lambda c: _license_urls.get(c.license, ''), 'html', str)
    app.add_config_value('tdoc_enable_sab', 'no', 'html',
                         config.ENUM('no', 'cross-origin-isolation', 'sabayon'))

    app.add_html_theme('t-doc', str(_common))
    app.add_directive('exec', Exec)
    app.add_node(ExecBlock, html=(visit_ExecBlock, depart_ExecBlock))

    app.connect('config-inited', on_config_inited)
    app.connect('builder-inited', on_builder_inited)
    app.connect('doctree-resolved', check_references)
    app.connect('html-page-context', on_html_page_context)
    if build_tag(app):
        app.connect('html-page-context', add_reload_js)
    app.connect('write-started', write_static_files)

    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


def report_exceptions(fn):
    def wrapper(self, /, *args, **kwargs):
        try:
            return fn(self, *args, **kwargs)
        except Exception as e:
            return [self.state.document.reporter.error(e, line=self.lineno)]
    return wrapper


def format_data_attrs(translator, /, **kwargs):
    return ' '.join(f'data-tdoc-{k}="{translator.attval(v)}"'
                    for k, v in sorted(kwargs.items()) if v is not None)


def build_tag(app):
    for tag in app.tags:
        if tag.startswith('tdoc_build_'):
            return tag


def on_config_inited(app, config):
    cv = config.values['html_title']
    super(cv.__class__, cv).__setattr__('default', lambda c: c.project)
    config.templates_path.append(str(_common / 'templates'))

    # Override defaults in html_theme_options.
    opts = config.html_theme_options
    opts.setdefault('use_sidenotes', True)
    opts.setdefault('path_to_docs', 'docs')
    if opts.get('repository_url'):
        opts.setdefault('use_repository_button', True)
        opts.setdefault('use_source_button', True)

    # Set the global HTML context.
    config['html_context']['tdoc_enable_sab'] = app.config.tdoc_enable_sab
    tag = build_tag(app)
    config['html_context']['tdoc_build'] = tag if tag is not None else ''


def on_builder_inited(app):
    # Add our own static paths.
    app.config.html_static_path.append(str(_common / 'static'))
    app.config.html_static_path.append(str(_common / 'static.gen'))


def on_html_page_context(app, page, template, context, doctree):
    license = app.config.license
    if license: context['license'] = license
    license_url = app.config.license_url
    if license_url: context['license_url'] = license_url

    # Set up early fixes.
    app.add_js_file('tdoc-early.js', priority=0,
                    scope=context['pathto']('', resource=True))

    # Add language-specific .js files for {exec}.
    if doctree:
        for lang in sorted(Exec.find_nodes(doctree)):
            app.add_js_file(f'tdoc-{lang}.js', type='module')


def add_reload_js(app, page, template, context, doctree):
    app.add_js_file('tdoc-reload.js', type='module')


def write_static_files(app, builder):
    if builder.format != 'html': return

    # The file must be at the root of the website, to avoid limiting the scope
    # of the service worker to _static.
    fileutil.copy_asset_file(_common / 'scripts' / 'tdoc-worker.js',
                             builder.outdir, force=True)

    # Package all files under tdoc/common/python into a .zip, below tdoc/, and
    # write it to _static.
    client = _common / 'python'
    rel = lambda p: p.relative_to(client)
    static = builder.outdir / '_static'
    osutil.ensuredir(static)
    with zipfile.ZipFile(static / 'tdoc-python.zip', mode='x') as f:
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


class ExecBlock(nodes.literal_block): pass


class Exec(CodeBlock):
    languages = {'python', 'sql'}

    option_spec = CodeBlock.option_spec | {
        'after': directives.class_option,
        'editable': directives.flag,
        'include': directives.unchanged_required,
        'then': directives.class_option,
        'when': lambda c: directives.choice(c, ('click', 'load', 'never')),
    }

    @staticmethod
    def find_nodes(doctree):
        nodes = {}
        for node in doctree.findall(ExecBlock):
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
        node.__class__ = ExecBlock
        node.tagname = node.__class__.__name__
        node['classes'] += ['tdoc-exec']
        if after := self.options.get('after'):
            node['after'] = after
        if then := self.options.get('then'):
            node['then'] = then
        node['when'] = self.options.get('when', 'click')
        if 'editable' in self.options:
            node['classes'] += ['tdoc-editable']


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


def visit_ExecBlock(self, node):
    try:
        return self.visit_literal_block(node)
    except nodes.SkipNode:
        after = node.get('after')
        then = node.get('then')
        attrs = format_data_attrs(
            self, after=' '.join(after) if after else None,
            then=' '.join(then) if then else None,
            when=node.get('when'))
        if attrs:
            def subst(m):
                return f'{m.group(1)} {attrs}{m.group(2)}'
            self.body[-1] = div_attrs_re.sub(subst, self.body[-1], 1)
        raise


def depart_ExecBlock(self, node):
    return self.depart_literal_block(node)
