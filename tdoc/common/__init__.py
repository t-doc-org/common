# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import json
import pathlib

from sphinx import config, locale
from sphinx.util import fileutil, logging

__project__ = 't-doc-common'
__version__ = '0.18'

_log = logging.getLogger(__name__)
_messages = 'tdoc'
_ = locale.get_translation(_messages)

_common = pathlib.Path(__file__).absolute().parent

_license_urls = {
    'CC0-1.0': 'https://creativecommons.org/publicdomain/zero/1.0/',
    'CC-BY-4.0': 'https://creativecommons.org/licenses/by/4.0/',
    'CC-BY-SA-4.0': 'https://creativecommons.org/licenses/by-sa/4.0/',
    'CC-BY-NC-4.0': 'https://creativecommons.org/licenses/by-nc/4.0/',
    'CC-BY-NC-SA-4.0': 'https://creativecommons.org/licenses/by-nc-sa/4.0/',
    'CC-BY-ND-4.0': 'https://creativecommons.org/licenses/by-nd/4.0/',
    'MIT': 'https://opensource.org/license/mit',
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


def setup(app):
    app.add_event('tdoc-html-page-config')

    app.add_config_value('license', '', 'html')
    app.add_config_value(
        'license_url', lambda c: _license_urls.get(c.license, ''), 'html', str)
    app.add_config_value('tdoc_enable_sab', 'no', 'html',
                         config.ENUM('no', 'cross-origin-isolation', 'sabayon'))

    app.add_html_theme('t-doc', str(_common))
    app.add_message_catalog(_messages, str(_common / 'locale'))

    app.connect('config-inited', on_config_inited)
    app.connect('builder-inited', on_builder_inited)
    app.connect('html-page-context', on_html_page_context)
    if build_tag(app):
        app.connect('html-page-context', add_reload_js)
    app.connect('write-started', write_static_files)

    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


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


def add_reload_js(app, page, template, context, doctree):
    app.add_js_file('tdoc/reload.js', type='module')


def write_static_files(app, builder):
    if builder.format != 'html': return

    # The file must be at the root of the website, to avoid limiting the scope
    # of the service worker to _static.
    fileutil.copy_asset_file(_common / 'scripts' / 'tdoc-worker.js',
                             builder.outdir, force=True)
