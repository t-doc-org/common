# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import pathlib
import re

from docutils import nodes, statemachine
from docutils.parsers.rst import directives
from sphinx.directives.code import CodeBlock
from sphinx.util import logging

__project__ = 't-doc-common'
__version__ = '0.8'

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

    app.add_html_theme('t-doc', str(_common))
    app.add_directive('exec', Exec)
    app.add_node(ExecBlock, html=(visit_ExecBlock, depart_ExecBlock))

    app.connect("config-inited", on_config_inited)
    app.connect('builder-inited', on_builder_inited)
    app.connect('doctree-resolved', check_after_references)
    app.connect('html-page-context', on_html_page_context)

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
            return [self.state.document.reporter.warning(e, line=self.lineno)]
    return wrapper


def format_data_attrs(translator, /, **kwargs):
    return ' '.join(f'data-tdoc-{k}="{translator.attval(v)}"'
                    for k, v in sorted(kwargs.items()) if v is not None)


def on_config_inited(app, config):
    cv = config.values['html_title']
    super(cv.__class__, cv).__setattr__('default', lambda c: c.project)
    config.templates_path.append(str(_common / 'components'))

    # Override defaults in html_theme_options.
    opts = config.html_theme_options
    opts.setdefault('use_sidenotes', True)
    opts.setdefault('path_to_docs', 'docs')
    if opts.get('repository_url'):
        opts.setdefault('use_repository_button', True)
        opts.setdefault('use_source_button', True)


def on_builder_inited(app):
    # Add our own static paths.
    app.config.html_static_path.append(str(_common / 'static'))
    app.config.html_static_path.append(str(_common / 'static.gen'))
    sqlite_path = (_root / 'node_modules' / '@sqlite.org' / 'sqlite-wasm'
                   / 'sqlite-wasm' / 'jswasm')
    if sqlite_path.is_dir():
        app.config.html_static_path.append(str(sqlite_path))


def on_html_page_context(app, page, template, context, doctree):
    license = app.config.license
    if license: context['license'] = license
    license_url = app.config.license_url
    if license_url: context['license_url'] = license_url

    if doctree and any(doctree.findall(Exec.match_node('sql'))):
        app.add_js_file('tdoc-sql.js', type='module')
        # TODO: Add Cross-Origin-*-Policy headers in the dev server
        # TODO: Work around inability to specify headers on GitHub Pages


class ExecBlock(nodes.literal_block): pass


class Exec(CodeBlock):
    # TODO: Validate the language against the list of supported languages

    option_spec = CodeBlock.option_spec | {
        'after': directives.class_option,
        'editable': directives.flag,
        'include': directives.unchanged_required,
        'when': lambda c: directives.choice(c, ('click', 'load', 'never')),
    }

    @staticmethod
    def match_node(lang=None):
        return lambda n: isinstance(n, ExecBlock) \
                         and 'tdoc-exec' in n['classes'] \
                         and (lang is None or n.get('language') == lang)

    @report_exceptions
    def run(self):
        if include := self.options.get('include'):
            content = statemachine.StringList()
            for path in include.split():
                rel_path, path = self.env.relfn2path(path)
                self.env.note_dependency(rel_path)
                content.extend(statemachine.StringList(
                    initlist=pathlib.Path(path).read_text().splitlines(),
                    source=path))
            self.content[:0] = content
        res = super().run()
        for node in res:
            for n in node.findall(nodes.literal_block):
                self._update_node(node)
        return res

    def _update_node(self, node):
        node.__class__ = ExecBlock
        node.tagname = node.__class__.__name__
        node['classes'] += ['tdoc-exec']
        if after := self.options.get('after'):
            node['after'] = after
        node['when'] = self.options.get('when', 'click')
        if 'editable' in self.options:
            node['classes'] += ['tdoc-editable']


def check_after_references(app, doctree, docname):
    nodes = list(doctree.findall(Exec.match_node('sql')))
    names = set()
    for n in nodes:
        names.update(n['names'])
    for n in nodes:
        for after in n.get('after', ()):
            if after not in names:
                doctree.reporter.error(
                    f"'exec': Unknown :after: reference: {after}", base_node=n)


div_attrs_re = re.compile(r'(?s)^(<div[^>]*)(>.*)$')


def visit_ExecBlock(self, node):
    try:
        return self.visit_literal_block(node)
    except nodes.SkipNode:
        after = node.get('after')
        attrs = format_data_attrs(
            self, after=' '.join(after) if after else None,
            when=node.get('when'))
        if attrs:
            def subst(m):
                return f'{m.group(1)} {attrs}{m.group(2)}'
            self.body[-1] = div_attrs_re.sub(subst, self.body[-1], 1)
        raise


def depart_ExecBlock(self, node):
    return self.depart_literal_block(node)
