# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import copy
import json
import pathlib

from docutils import nodes
from sphinx import config, locale
from sphinx.util import fileutil, logging

from .. import __version__

_log = logging.getLogger(__name__)
_messages = 'tdoc'
_ = locale.get_translation(_messages)

_base = pathlib.Path(__file__).parent.resolve().parent

_license_urls = {
    'CC0-1.0': 'https://creativecommons.org/publicdomain/zero/1.0/',
    'CC-BY-4.0': 'https://creativecommons.org/licenses/by/4.0/',
    'CC-BY-SA-4.0': 'https://creativecommons.org/licenses/by-sa/4.0/',
    'CC-BY-NC-4.0': 'https://creativecommons.org/licenses/by-nc/4.0/',
    'CC-BY-NC-SA-4.0': 'https://creativecommons.org/licenses/by-nc-sa/4.0/',
    'CC-BY-ND-4.0': 'https://creativecommons.org/licenses/by-nd/4.0/',
    'MIT': 'https://opensource.org/license/mit',
}


def names_option(arg):
    if arg is None: raise ValueError('no argument provided')
    return [nodes.fully_normalize_name(n) for n in arg.split()]


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
    app.set_html_assets_policy('always')  # Ensure MathJax is always available
    app.add_event('tdoc-html-page-config')

    app.add_config_value('license', '', 'html')
    app.add_config_value(
        'license_url', lambda c: _license_urls.get(c.license, ''), 'html', str)
    app.add_config_value('tdoc', {}, 'html')
    app.add_config_value('tdoc_enable_sab', 'no', 'html',
                         config.ENUM('no', 'cross-origin-isolation', 'sabayon'))

    app.add_html_theme('t-doc', str(_base))
    app.add_message_catalog(_messages, str(_base / 'locale'))

    app.connect('config-inited', on_config_inited)
    app.connect('html-page-context', on_html_page_context)
    app.connect('html-page-context', add_draw_button, priority=500.6)
    if build_tag(app) is not None:
        app.connect('html-page-context', add_reload_js)
        app.connect('html-page-context', add_terminate_button, priority=500.4)
    app.connect('write-started', write_static_files)

    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


def on_config_inited(app, config):
    cv = config.values['html_title']
    super(cv.__class__, cv).__setattr__('default', lambda c: c.project)
    config.templates_path.append(str(_base / 'templates'))

    # Add our own static paths, and a default one if it exists.
    config.html_static_path.append(str(_base / 'static'))
    config.html_static_path.append(str(_base / 'static.gen'))
    if '_static' not in config.html_static_path \
            and (app.confdir / '_static').exists():
        config.html_static_path.append('_static')

    # Set defaults in the t-doc config.
    tdoc = config.tdoc
    tdoc.setdefault('html_data', {})
    tdoc['enable_sab'] = config.tdoc_enable_sab
    if (build := build_tag(app)) is not None: tdoc['build'] = build

    # Override defaults in html_theme_options.
    opts = config.html_theme_options
    opts.setdefault('use_sidenotes', True)
    opts.setdefault('path_to_docs', 'docs')
    if opts.get('repository_url'):
        opts.setdefault('use_repository_button', True)
        opts.setdefault('use_source_button', True)


def on_html_page_context(app, page, template, context, doctree):
    context['tdoc_version'] = __version__
    license = app.config.license
    if license: context['license'] = license
    license_url = app.config.license_url
    if license_url: context['license_url'] = license_url

    # Set up early and on-load JavaScript.
    tdoc = copy.deepcopy(app.config.tdoc)
    app.emit('tdoc-html-page-config', page, tdoc)
    tdoc = json.dumps(tdoc, separators=(',', ':'))
    app.add_js_file(None, priority=0, body=f'const tdoc = {tdoc};')
    app.add_js_file('tdoc/early.js', priority=1,
                    scope=context['pathto']('', resource=True))
    app.add_js_file('tdoc/load.js', type='module')


def add_draw_button(app, page, template, context, doctree):
    if doctree is None: return
    context["header_buttons"].append({
        'type': 'javascript',
        'javascript': 'tdoc.draw()',
        'tooltip': _("Draw"),
        'label': 'draw',
    })


def add_reload_js(app, page, template, context, doctree):
    app.add_js_file('tdoc/reload.js', type='module')


def add_terminate_button(app, page, template, context, doctree):
    if doctree is None: return
    context["header_buttons"].append({
        'type': 'javascript',
        'javascript': 'tdoc.terminateServer()',
        'tooltip': _("Terminate the local server"),
        'label': 'terminate',
    })


def write_static_files(app, builder):
    if builder.format != 'html': return

    # The file must be at the root of the website, to avoid limiting the scope
    # of the service worker to _static.
    fileutil.copy_asset_file(_base / 'scripts' / 'tdoc-worker.js',
                             builder.outdir, force=True)
