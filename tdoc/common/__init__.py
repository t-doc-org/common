# Copyright 2024 Caroline Blank <caro@c-space.org>
# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import pathlib

from docutils import nodes
from sphinx.directives.code import CodeBlock
from sphinx.util import logging

__version__ = '0.3'

_common = pathlib.Path(__file__).absolute().parent
_root = _common.parent.parent
makefile = str(_common / 'common.mk')

_log = logging.getLogger(__name__)

_license_urls = {
    'CC0-1.0': 'https://creativecommons.org/publicdomain/zero/1.0/',
    'CC-BY-4.0': 'https://creativecommons.org/licenses/by/4.0/',
    'CC-BY-SA-4.0': 'https://creativecommons.org/licenses/by-sa/4.0/',
    'CC-BY-NC-4.0': 'https://creativecommons.org/licenses/by-nc/4.0/',
    'CC-BY-NC-SA-4.0': 'https://creativecommons.org/licenses/by-nc-sa/4.0/',
    'CC-BY-ND-4.0': 'https://creativecommons.org/licenses/by-nd/4.0/',
}

def setup(app):
    app.add_config_value('license', '', 'html')
    app.add_config_value(
        'license_url', lambda c: _license_urls.get(c.license, ''), 'html', str)

    app.add_html_theme('t-doc', str(_common))
    app.add_directive('exec', Exec)

    app.connect("config-inited", on_config_inited)
    app.connect('builder-inited', on_builder_inited)
    app.connect('html-page-context', on_html_page_context)

    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


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
    app.config.html_static_path.append(str(_common / 'static'))
    sw = _root / 'ext' / 'sqlite-wasm' / 'sqlite-wasm'
    if (sw / 'jswasm').is_dir():
        app.config.html_static_path.append(str(sw))


def on_html_page_context(app, page, template, context, doctree):
    license = app.config.license
    if license: context['license'] = license
    license_url = app.config.license_url
    if license_url: context['license_url'] = license_url

    if doctree and any(doctree.findall(Exec.match_node('sql'))):
        app.add_js_file('tdoc-sql.js', type='module')
        # TODO: Add Cross-Origin-*-Policy headers in the dev server
        # TODO: Work around inability to specify headers on GitHub Pages


class Exec(CodeBlock):
    # TODO: :after: option
    # TODO: :show: option
    # TODO: :immediate: or :run:
    @staticmethod
    def match_node(lang=None):
        return lambda n: isinstance(n, nodes.literal_block) \
                         and 'tdoc-exec' in n['classes'] \
                         and (lang is None or n.get('language') == lang)

    def run(self):
        res = super().run()
        for node in res:
            for n in node.findall(nodes.literal_block):
                n['classes'] += ['tdoc-exec']
        # _log.info("res: %s", res, color='yellow')
        return res
