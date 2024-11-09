# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import json
import pathlib
import re
import yaml
import zipfile

from docutils import nodes, statemachine
from docutils.parsers.rst import directives
from sphinx import config, locale
from sphinx.directives import code
from sphinx.util import docutils, fileutil, logging, osutil

__project__ = 't-doc-common'
__version__ = '0.17'

_log = logging.getLogger(__name__)
_messages = 'tdoc'
_ = locale.get_translation(_messages)

_common = pathlib.Path(__file__).absolute().parent
_root = _common.parent.parent

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
    app.add_event('tdoc-html-page-config')

    app.add_config_value('license', '', 'html')
    app.add_config_value(
        'license_url', lambda c: _license_urls.get(c.license, ''), 'html', str)
    app.add_config_value('tdoc_enable_sab', 'no', 'html',
                         config.ENUM('no', 'cross-origin-isolation', 'sabayon'))

    app.add_html_theme('t-doc', str(_common))
    app.add_message_catalog(_messages, str(_common / 'locale'))

    app.add_node(exec, html=(visit_exec, depart_exec))
    app.add_directive('exec', Exec)

    app.connect('config-inited', on_config_inited)
    app.connect('builder-inited', on_builder_inited)
    app.connect('doctree-resolved', check_references)
    app.connect('html-page-context', on_html_page_context)
    if build_tag(app):
        app.connect('html-page-context', add_reload_js)
    app.connect('write-started', write_static_files)

    app.add_node(metadata)
    app.add_directive('metadata', Metadata)
    app.connect('doctree-read', extract_metadata)
    app.connect('html-page-context', add_head_elements)

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


def format_attrs(translator, /, **kwargs):
    return ' '.join(f'{k.replace('_', '-')}="{translator.attval(v)}"'
                    for k, v in sorted(kwargs.items()) if v is not None)


def format_data_attrs(translator, /, **kwargs):
    return ' '.join(f'data-tdoc-{k.replace('_', '-')}="{translator.attval(v)}"'
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
    context = config.html_context
    context['tdoc_enable_sab'] = app.config.tdoc_enable_sab
    tag = build_tag(app)
    context['tdoc_build'] = tag if tag is not None else ''
    context['tdoc_togglebutton_selector'] = getattr(
        config, 'togglebutton_selector', '._:not(._)')


def on_builder_inited(app):
    # Add our own static paths.
    app.config.html_static_path.append(str(_common / 'static'))
    app.config.html_static_path.append(str(_common / 'static.gen'))

    # Add a default static path.
    if '_static' not in app.config.html_static_path:
        app.config.html_static_path.append('_static')


def on_html_page_context(app, page, template, context, doctree):
    license = app.config.license
    if license: context['license'] = license
    license_url = app.config.license_url
    if license_url: context['license_url'] = license_url

    # Set up early and core JavaScript.
    config = {'htmlData': {}}
    app.emit('tdoc-html-page-config', page, config)
    config = json.dumps(config, separators=(',', ':'))
    app.add_js_file(None, priority=0, body=f'const tdocConfig = {config};')
    app.add_js_file('tdoc/early.js', priority=1,
                    scope=context['pathto']('', resource=True))
    app.add_js_file('tdoc/core.js', type='module', id='tdoc-core-js')

    # Add language-specific .js files for {exec}.
    if doctree:
        for lang in sorted(Exec.find_nodes(doctree)):
            app.add_js_file(f'tdoc/exec-{lang}.js', type='module')


def add_reload_js(app, page, template, context, doctree):
    app.add_js_file('tdoc/reload.js', type='module')


def write_static_files(app, builder):
    if builder.format != 'html': return

    # The file must be at the root of the website, to avoid limiting the scope
    # of the service worker to _static.
    fileutil.copy_asset_file(_common / 'scripts' / 'tdoc-worker.js',
                             builder.outdir, force=True)

    # Package all files under tdoc/common/python into a .zip, below tdoc/, and
    # write it to _static/tdoc.
    client = _common / 'python'
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


class exec(nodes.literal_block): pass


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


class metadata(nodes.Element): pass


class Metadata(docutils.SphinxDirective):
    has_content = True

    @report_exceptions
    def run(self):
        return [metadata(attrs=yaml.safe_load(
                    ''.join(f'{line}\n' for line in self.content)))]


def extract_metadata(app, doctree):
    md = app.env.metadata[app.env.docname]
    nodes = list(doctree.findall(metadata))
    for i, node in enumerate(nodes):
        if i == 0:
            if (attrs := node['attrs']) is not None: md.update(attrs)
        else:
            _log.warning(
                f"{app.env.docname}: More than one {{metadata}} directive")
        node.parent.remove(node)


def add_head_elements(app, page, template, context, doctree):
    md = app.env.metadata[page]
    add_head_files(app.add_css_file, md.get('styles', []))
    add_head_files(app.add_js_file, md.get('scripts', []))


def add_head_files(add, entries):
    for entry in entries:
        if isinstance(entry, str):
            add(entry, priority=900)
        else:
            kwargs = dict(entry)
            path = kwargs.pop('src', None)
            for k, v in kwargs.items():
                if v is None: kwargs[k] = ''
            add(path, priority=900, **kwargs)
