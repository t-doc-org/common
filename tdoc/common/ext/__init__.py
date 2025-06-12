# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import base64
import copy
import functools
import json
import pathlib

from docutils import nodes, statemachine
from myst_parser import mocking
from sphinx import config, locale
from sphinx.environment import collectors
from sphinx.util import docutils, fileutil, logging

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

# BUG(myst_parser): MockState.parse_directive_block() [myst_parser] returns the
# content as a StringList, whereas Body.parse_directive_block() [docutils]
# returns a list. The StringList is constructed with source=content.source,
# which is a bound method and clearly wrong. Patch the method to unwrap the
# list.
def _parse_directive_block(self, *args, **kwargs):
    arguments, options, content, content_offset = \
        MockState_parse_directive_block(self, *args, **kwargs)
    if isinstance(content, statemachine.StringList): content = content.data
    return arguments, options, content, content_offset

MockState_parse_directive_block = mocking.MockState.parse_directive_block
mocking.MockState.parse_directive_block = _parse_directive_block


def to_base64(s):
    return base64.b64encode(s.encode('utf-8')).decode('utf-8').rstrip('=')


def names_option(arg):
    if arg is None: raise ValueError('no argument provided')
    return [nodes.fully_normalize_name(n) for n in arg.split()]


def report_exceptions(fn):
    @functools.wraps(fn)
    def wrapper(self, /, *args, **kwargs):
        try:
            return fn(self, *args, **kwargs)
        except Exception as e:
            if isinstance(self, Role):
                err = self.inliner.document.reporter.error(e, line=self.lineno)
                return [], [err]
            return [self.state.document.reporter.error(e, line=self.lineno)]
    return wrapper


def format_attrs(translator, /, **kwargs):
    return ' '.join(f'{k.replace('_', '-')}="{translator.attval(v)}"'
                    for k, v in sorted(kwargs.items()) if v is not None)


def format_data_attrs(translator, /, **kwargs):
    return ' '.join(f'data-tdoc-{k.replace('_', '-')}="{translator.attval(v)}"'
                    for k, v in sorted(kwargs.items()) if v is not None)


def setup(app):
    app.set_html_assets_policy('always')  # Ensure MathJax is always available
    app.add_event('tdoc-html-page-config')

    app.add_config_value('license', '', 'html', str)
    app.add_config_value(
        'license_url', lambda c: _license_urls.get(c.license, ''), 'html', str)
    app.add_config_value('tdoc', {}, 'html', dict)
    app.add_config_value('tdoc_api', '', 'html', str)
    app.add_config_value('tdoc_enable_sab', 'no', 'html',
                         config.ENUM('no', 'cross-origin-isolation', 'sabayon'))

    app.add_html_theme('t-doc', str(_base))
    app.add_message_catalog(_messages, str(_base / 'locale'))

    app.connect('config-inited', on_config_inited)
    app.connect('html-page-context', on_html_page_context)
    app.connect('html-page-context', add_draw_button, priority=500.6)
    if 'tdoc-dev' in app.tags:
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

    # Override defaults in html_theme_options.
    opts = config.html_theme_options
    opts.setdefault('use_sidenotes', True)
    opts.setdefault('path_to_docs', 'docs')
    if opts.get('repository_url'):
        opts.setdefault('use_repository_button', True)
        opts.setdefault('use_source_button', True)


def on_html_page_context(app, page, template, context, doctree):
    context['tdoc_version'] = __version__
    if v := app.config.license: context['license'] = v
    if v := app.config.license_url: context['license_url'] = v

    # Set up early and on-load JavaScript.
    tdoc = {
        'conf': copy.deepcopy(app.config.tdoc),
        'enable_sab': app.config.tdoc_enable_sab, 'html_data': {},
    }
    if 'tdoc-dev' in app.tags: tdoc['dev'] = True
    if v := app.config.tdoc_api: tdoc['api_url'] = v
    app.emit('tdoc-html-page-config', page, tdoc, doctree)
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


class Role(docutils.SphinxRole):
    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        return self(*args, **kwargs)


class UniqueChecker(collectors.EnvironmentCollector):
    def __init__(self, name, iter_nodes, err):
        self.name = name
        self.iter_nodes = iter_nodes
        self.err = err

    def __repr__(self): return f'UniqueChecker({self.name})'
    def __call__(self): return self

    def enable(self, app):
        def init(app):
            if not hasattr(app.env, 'tdoc_unique'): app.env.tdoc_unique = {}
            # ID => (docname, location)
            app.env.tdoc_unique.setdefault(self.name, {})
        self.init_listener = app.connect('builder-inited', init)
        super().enable(app)

    def disable(self, app):
        super().disable(app)
        app.disconnect(self.init_listener)

    def clear_doc(self, app, env, docname):
        ids = env.tdoc_unique[self.name]
        for v in list(ids):
            if ids[v][0] == docname: del ids[v]

    def merge_other(self, app, env, docnames, other):
        ids = env.tdoc_unique[self.name]
        for v, (dn, loc) in other.tdoc_unique.get(self.name, {}).items():
            if dn not in docnames: continue
            if v not in ids:
                ids[v] = (dn, loc)
            else:
                _log.error(f"{self.err}: {v}", location=loc)

    def process_doc(self, app, doctree):
        ids = app.env.tdoc_unique[self.name]
        for node, v in self.iter_nodes(doctree):
            if not v: continue
            if v not in ids:
                ids[v] = (app.env.docname, (node.source, node.line))
            else:
                doctree.reporter.error(f"{self.err}: {v}", base_node=node)
