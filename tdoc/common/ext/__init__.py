# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import base64
import copy
import functools
import json
import pathlib
import re

from docutils import nodes, statemachine
from docutils.parsers.rst import directives
from myst_parser import mocking
from sphinx import config, jinja2glue, locale
from sphinx.environment import collectors
from sphinx.util import docutils, fileutil, logging

from .. import __version__, deps

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

# BUG(myst-parser): MockState.parse_directive_block() [myst_parser] returns the
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


unset = object()

def merge_dict(dst, src):
    for k, sv in src.items():
        dv = dst.get(k, unset)
        if isinstance(sv, dict) and isinstance(dv, dict):
            merge_dict(dv, sv)
        else:
            dst[k] = copy.deepcopy(sv)
    return dst


def names_option(arg):
    if arg is None: raise ValueError('no argument provided')
    return [nodes.fully_normalize_name(n) for n in arg.split()]


def log_exception(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            _log.error(f"{fn.__name__}: {e}")
            raise
    return wrapper


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
    app.add_config_value('tdoc_domain_storage', {}, 'html', dict)
    app.add_config_value('tdoc_enable_sab', 'no', 'html',
                         config.ENUM('no', 'cross-origin-isolation', 'sabayon'))
    app.add_config_value('tdoc_versions', {}, 'html', dict)

    app.add_html_theme('t-doc', str(_base))
    app.add_message_catalog(_messages, str(_base / 'locale'))

    app.connect('config-inited', on_config_inited)
    app.connect('builder-inited', on_builder_inited)
    app.connect('html-page-context', set_html_context, priority=0)
    app.connect('html-page-context', add_js, priority=499.9)
    app.connect('html-page-context', restore_mathjax, priority=500.1)
    if 'tdoc-dev' in app.tags:
        app.connect('html-page-context', add_terminate_button, priority=500.4)
    app.connect('html-page-context', add_draw_button, priority=500.6)
    app.connect('html-page-context', add_user_button, priority=500.7)
    app.connect('write-started', write_static_files)

    app.add_node(dyn, html=(visit_dyn, depart_dyn))
    app.connect('tdoc-html-page-config', add_dyn_config)
    app.add_env_collector(UniqueChecker('dyn-name',
        lambda doctree: ((n, (n['type'], name) if (name := n.get('name'))
                                               else None)
                         for n in doctree.findall(dyn)),
        lambda v: f"{{{v[0]}}}: Duplicate name: {v[1]}"))

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

    # Override config defaults.
    if config.author and not config.copyright:
        config.copyright = f'%Y {config.author}'

    # Override defaults in html_theme_options.
    opts = config.html_theme_options
    opts.setdefault('use_sidenotes', True)
    opts.setdefault('path_to_docs', 'docs')
    if opts.get('repository_url'):
        opts.setdefault('use_repository_button', True)
        opts.setdefault('use_source_button', True)
    opts.setdefault('use_download_button', False)


def on_builder_inited(app):
    # The config is used in domain.html.jinja.
    tdoc = tdoc_config(app)
    app.config.html_context['tdoc'] = \
        json.dumps(tdoc, separators=(',', ':')).replace('<', '\\x3c')


def set_html_context(app, page, template, context, doctree):
    context['tdoc_version'] = __version__
    context.setdefault('html_attrs', {})
    if 'tdoc-dev' in app.tags: context['html_attrs']['data-tdoc-dev'] = ''
    if v := app.config.license: context['license'] = v
    if v := app.config.license_url: context['license_url'] = v


# BUG(pydata-sphinx-theme): The layout.html template doesn't allow overriding
# the <html> tag. Patch the template source at load-time to add attributes from
# the html_attrs context variable, by monkey-patching SphinxFileSystemLoader.
html_re = re.compile(r'(?m)^(<html[^>]*)(>)$')

def _get_source(self, env, template):
    contents, filename, uptodate = \
        SphinxFileSystemLoader_get_source(self, env, template)
    if template == 'pydata_sphinx_theme/layout.html':
        contents, n = html_re.subn(
            r'\1{{ html_attrs | default({}) | xmlattr }}\2', contents)
        if n != 1:
            raise Exception(
                "Patching of pydata_sphinx_theme/layout.html failed")
    return contents, filename, uptodate

SphinxFileSystemLoader_get_source = jinja2glue.SphinxFileSystemLoader.get_source
jinja2glue.SphinxFileSystemLoader.get_source = _get_source


def add_js(app, page, template, context, doctree):
    # Set up early and on-load JavaScript. Temporarily override mathjax_path
    # as per version specification, then restore it after
    # mathjax.install_mathjax() has run.
    tdoc = tdoc_config(app, page, doctree, context)
    mathjax = tdoc['versions'].pop('mathjax')
    if mathjax.startswith('/'): mathjax = f'../{mathjax[1:]}'
    context['tdoc_mathjax_path'] = app.config.mathjax_path
    app.config.mathjax_path = f'{mathjax}/tex-chtml-full.js'
    tdoc = json.dumps(tdoc, separators=(',', ':')).replace('<', '\\x3c')
    app.add_js_file(None, priority=0, body=f'const tdoc = {tdoc};')
    app.add_js_file('tdoc/early.js', priority=1)
    app.add_js_file('tdoc/load.js', type='module')


def restore_mathjax(app, page, template, context, doctree):
    app.config.mathjax_path = context['tdoc_mathjax_path']
    del context['tdoc_mathjax_path']


def tdoc_config(app, page=None, doctree=None, context=None):
    tdoc = {
        'conf': copy.deepcopy(app.config.tdoc),
        'domain_storage': copy.deepcopy(app.config.tdoc_domain_storage),
        'enable_sab': app.config.tdoc_enable_sab,
    }
    if is_dev := 'tdoc-dev' in app.tags: tdoc['dev'] = True
    versions = tdoc['versions'] = \
        (app.env.metadata[page].get('versions') or {}).copy()
    for name, v in app.config.tdoc_versions.items():
        versions.setdefault(name, v)
    for name, info in deps.info.items():
        if '://' not in (v := versions.setdefault(name, info['version'])):
            versions[name] = f'/_cache/{name}/{v}' if is_dev else info['url'](v)
    if v := app.config.tdoc_api: tdoc['api_url'] = v
    app.emit('tdoc-html-page-config', page, tdoc, doctree)
    return tdoc


def add_terminate_button(app, page, template, context, doctree):
    if doctree is None: return
    context["header_buttons"].append({
        'type': 'javascript',
        'javascript': 'tdoc.terminateServer()',
        'tooltip': _("Terminate the local server"),
        'label': 'terminate',
    })


def add_draw_button(app, page, template, context, doctree):
    if doctree is None: return
    context["header_buttons"].append({
        'type': 'javascript',
        'javascript': 'tdoc.draw()',
        'tooltip': _("Draw"),
        'label': 'draw',
    })


def add_user_button(app, page, template, context, doctree):
    if doctree is None: return
    context["header_buttons"].append({
        'type': 'group',
        'label': 'user',
        'buttons': [{
            'type': 'link',
            'text': "Not signed in",
            'icon': 'fa fa-user',
            'label': 'user',
        }, {
            'type': 'javascript',
            'javascript': 'tdoc.login()',
            'text': "Sign in",
            'icon': 'fa fa-right-to-bracket',
            'label': 'login',
        }, {
            'type': 'javascript',
            'javascript': 'tdoc.logout()',
            'text': "Sign out",
            'icon': 'fa fa-right-from-bracket',
            'label': 'logout',
        }],
    })


def write_static_files(app, builder):
    if builder.format != 'html': return

    # The file must be at the root of the website, to avoid limiting the scope
    # of the service worker to _static.
    fileutil.copy_asset_file(_base / 'scripts' / 'tdoc-worker.js',
                             builder.outdir, force=True)


class RoleMixin:
    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        return self(*args, **kwargs)


class Role(docutils.SphinxRole, RoleMixin): pass
class ReferenceRole(docutils.ReferenceRole, RoleMixin): pass


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
                _log.error(self.err(v), location=loc)

    def process_doc(self, app, doctree):
        ids = app.env.tdoc_unique[self.name]
        for node, v in self.iter_nodes(doctree):
            if not v: continue
            if v not in ids:
                ids[v] = (app.env.docname, (node.source, node.line))
            else:
                doctree.reporter.error(self.err(v), base_node=node)


class DictUpdater:
    def __init__(self, d):
        self.__dict__['_d'] = d

    def __getitem__(self, key):
        return DictUpdater(self._d.setdefault(key, {}))

    def __setitem__(self, key, value):
        self._d[key] = value

    def __delitem__(self, key):
        del self._d[key]

    __getattr__ = __getitem__
    __setattr__ = __setitem__
    __delattr__ = __delitem__


class Dyn(docutils.SphinxDirective):
    option_spec = {
        'class': directives.class_option,
        'style': directives.unchanged,
    }

    @report_exceptions
    def run(self):
        node = dyn(type=self.name)
        self.set_source_info(node)
        self.state.document.set_id(node)
        if self.arguments: node['name'] = self.arguments[0]
        node['classes'] += self.options.get('class', [])
        if v := self.options.get('style', '').strip(): node['style'] = v
        self.populate(node)
        return [node]

    def populate(self, node):
        if self.has_content:
            node.append(nodes.Text(''.join(f'{line}\n'
                                           for line in self.content)))


class dyn(nodes.General, nodes.Element):
    @classmethod
    def has_type(cls, typ):
        return lambda n: isinstance(n, cls) and n['type'] == typ


def visit_dyn(self, node):
    attrs = {'data-type': node['type']}
    if v := node.get('name'): attrs['data-name'] = v
    if v := node.get('style'): attrs['style'] = v
    self.body.append(self.starttag(node, 'div', '', classes=['tdoc-dyn'],
                                   **attrs))


def depart_dyn(self, node):
    self.body.append('</div>\n')


def add_dyn_config(app, page, config, doctree):
    if page is None or doctree is None: return
    dcfg = {}
    for typ in {n['type'] for n in doctree.findall(dyn)}:
        cfg = getattr(app.config, f'tdoc_{typ}', {})
        if (md := app.env.metadata[page].get(typ)) is not None:
            cfg = merge_dict(copy.deepcopy(cfg), md)
        dcfg[typ] = cfg
    if dcfg: config['dyn'] = dcfg
