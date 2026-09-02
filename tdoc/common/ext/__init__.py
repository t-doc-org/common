# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import base64
from concurrent import futures
import contextlib
import copy
import functools
import logging as _logging
import pathlib
import posixpath
import re
import sys
import time

from docutils import nodes
from docutils.parsers.rst import directives
import pyjson5
from sphinx import addnodes, config, errors, locale
from sphinx._cli.util import errors as cli_errors
from sphinx.builders import html
from sphinx.domains import rst
from sphinx.environment import collectors
from sphinx.ext.intersphinx import _load
from sphinx.util import display, docutils, fileutil, logging

from . import patch
from .. import __version__, deps, util

if sys.platform == 'win32': import winreg

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


@patch.asset_file('/_static/styles/pydata-sphinx-theme.css')
def pydata_sphinx_theme_css(data):
    overwrite = lambda m: f'{m[1]}{' ' * len(m[2])}{m[3]}'

    # BUG(pydata-sphinx-theme): The theme's CSS sets a top margin on the next
    # element after the title. Remove that, and set a bottom margin on the title
    # instead.
    data = patch.sub(data,
                     r'(\.admonition>\.admonition-title\+\*,'
                     r'div\.admonition>\.admonition-title\+\*'
                     r'\{)(margin-top:[^}]+)(\})',
                     overwrite)
    # BUG(pydata-sphinx-theme): The rule in the theme's CSS is too broad. The
    # selector should be more precise (.admonition > :last-child), but basic.css
    # already has such a rule, so it can be removed altogether.
    data = patch.sub(data,
                     r'(\.admonition :last-child\{)(margin-bottom:[^}]+)(\})',
                     overwrite)
    # BUG(pydata-sphinx-theme): The theme's CSS sets left and right margins on
    # all direct descendants of admonition containers. This breaks horizontal
    # alignment classes.
    data = patch.sub(data,
                     r'(\.admonition p\.admonition-title~\*,'
                     r'div\.admonition p\.admonition-title~\*'
                     r'\{)(margin-left:[^;]+;margin-right:[^}]+)(\})',
                     overwrite)
    # BUG(pydata-sphinx-theme): The theme's CSS sets a left margin on lists that
    # are direct descendants of admonition containers.
    data = patch.sub(data,
                     r'(\.admonition>ol,\.admonition>ul,'
                     r'div\.admonition>ol,div\.admonition>ul'
                     r'\{)(margin-left:[^}]+)(\})',
                     overwrite)
    return data


def to_base64(s):
    return base64.b64encode(s.encode('utf-8')).decode('utf-8').rstrip('=')


unset = object()

def merge_dict(dst, src, override=True):
    for k, sv in src.items():
        dv = dst.get(k, unset)
        if isinstance(sv, dict) and isinstance(dv, dict):
            merge_dict(dv, sv, override)
        elif override or dv is unset:
            dst[k] = copy.deepcopy(sv)
    return dst


def opt_bool(arg):
    if arg is None or (v := arg.strip().lower()) in ('', 'true'): return True
    if v == 'false': return False
    raise ValueError("must be true, false or empty")


def opt_names(arg):
    if arg is None: raise ValueError('no argument provided')
    return [nodes.fully_normalize_name(n) for n in arg.split()]


def opt_classes(arg):
    # TODO: Monkey-patch all directives to use this instead of class_option
    if arg is None: return []
    classes = []
    for a in arg.split():
        if not (name := nodes.make_id(a)):
            raise ValueError(f"cannot make \"{a}\" into a class name")
        classes.append(name)
    return classes


def opt_set(*values):
    if values: values = frozenset(values)
    def parse(arg):
        if arg is None: return set()
        vs = set(arg.split())
        if values and (u := vs - values):
            raise ValueError(f"invalid values: {" ".join(u)}")
        return vs
    return parse


editor_options = {
    'editor': directives.unchanged,
    'editor-config': directives.unchanged,
}


def parse_editor_options(options, node):
    if (v := options.get('editor')) not in (None, 'none'):
        cfg = {}
        if v: cfg.update(id=v, store='local')
        if v := options.get('editor-config'):
            cfg.update(pyjson5.decode(f'{{{v}}}'))
        node['editor'] = util.to_json(cfg) if cfg else ''


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
            msgs = [self.reporter.error(e, line=self.lineno)]
            if isinstance(self, RoleMixin): return [], msgs
            return msgs
    return wrapper


def format_attrs(translator, /, **kwargs):
    return ' '.join(f'{k.replace('_', '-')}="{translator.attval(v)}"'
                    for k, v in sorted(kwargs.items()) if v is not None)


def meta(env, docname, key, default=None):
    v = env.metadata[docname]
    for k in key.split('.'):
        try:
            v = v[k]
        except (KeyError, TypeError):
            return default
    return v


def needs_build(dst, src):
    src_st = src.stat()
    try: dst_st = dst.stat()
    except OSError: return True
    return src_st.st_mtime_ns > dst_st.st_mtime_ns


app_paths_key = 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths'

def find_app_path(name):
    for k in [winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE]:
        try:
            with winreg.OpenKey(k, f'{app_paths_key}\\{name}') as key:
                v, t = winreg.QueryValueEx(key, '')
        except FileNotFoundError:
            continue
        if t == winreg.REG_EXPAND_SZ:
            v = winreg.ExpandEnvironmnentStrings(v)
        elif t != winreg.REG_SZ:
            continue
        if len(v) >= 2 and v[0] == v[-1] == '"': v = v[1:-1]
        if (p := pathlib.Path(v)).exists(): return p


def map_parallel(app, fn, items, summary=None, color='brown', stringify=str):
    with futures.ThreadPoolExecutor(max_workers=app.parallel) as ex:
        tasks = [(ex.submit(lambda it=it: fn(it)), it) for it in items]
        its = tasks if summary is None \
              else display.status_iterator(
                  tasks, summary, color=color, length=len(tasks),
                  verbosity=app.config.verbosity,
                  stringify_func=lambda a: stringify(a[1]))
        for task, it in its: yield task.result()


def sink(items):
    for it in items: pass


_log_exc = _logging.getLogger('tdoc-sphinx-exception')
_log_exc.propagate = False


@patch.patch(cli_errors, 'handle_exception')
def _errors_handle_exception(orig, exc, /, *args, **kwargs):
    import bdb
    if _log_exc.handlers \
            and not isinstance(exc, (KeyboardInterrupt, bdb.BdbQuit)):
        _log_exc.error(f"{exc.__class__.__name__}: {exc}", exc_info=exc)
    return orig(exc, *args, **kwargs)


class WarningHandler(logging.WarningStreamHandler):
    terminator = '\0'

    def __init__(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        super().__init__(open(path, 'w', encoding='utf-8', errors='replace'))

    def emit_(self, rec):
        self.stream.write(f'{self.format(rec).strip()}\0')


class WarningSuppressor(logging.WarningSuppressor):
    def __init__(self, app):
        # The base class uses app.config and app._warncount. We don't want it to
        # count warnings, because that's already done by a separate instance. So
        # we pass self as app, provide access to config and provide a dummy
        # _warncount.
        self.config = app.config
        self._warncount = 0
        super().__init__(self)


def setup(app):
    if 'tdoc-local' in app.tags:
        # Set up a logging handler to capture warnings and above and write them
        # to a file.
        h = WarningHandler(app.outdir.parent / util.build_errors)
        h.addFilter(WarningSuppressor(app))
        h.addFilter(logging.OnceFilter())
        h.setLevel(_logging.WARNING)
        _log_exc.addHandler(h)
        logger = _logging.getLogger(logging.NAMESPACE)
        logger.addHandler(h)

    app.set_html_assets_policy('always')  # Ensure MathJax is always available
    app.add_event('tdoc-html-page-config')

    app.add_config_value('license', '', 'html', str)
    app.add_config_value(
        'license_url', lambda c: _license_urls.get(c.license, ''), 'html', str)
    app.add_config_value('tdoc', {}, 'html', dict)
    app.add_config_value('tdoc_api', '', 'html', str)
    app.add_config_value('tdoc_repos', 'https://rc.t-doc.org/', 'html', str)
    app.add_config_value('tdoc_domain_storage', {}, 'html', dict)
    app.add_config_value('tdoc_enable_sab', 'no', 'html',
                         config.ENUM('no', 'cross-origin-isolation', 'sabayon'))
    app.add_config_value('tdoc_source_type', 'md', 'env',
                         config.ENUM('md', 'rst'))

    app.add_html_theme('t-doc', str(_base))
    app.add_message_catalog(_messages, str(_base / 'locale'))

    app.connect('config-inited', on_config_inited)
    app.connect('builder-inited', update_intersphinx, priority=499.9)
    app.connect('builder-inited', set_base_html_context)
    app.connect('builder-inited', configure_templates)
    app.connect('doctree-read', fix_rst_signatures, priority=0)
    app.connect('html-page-context', set_html_context, priority=0)
    app.connect('html-page-context', add_js, priority=499.9)
    app.connect('html-page-context', restore_mathjax, priority=500.1)
    if 'tdoc-local' in app.tags:
        app.connect('html-page-context', add_build_status, priority=500.4)
    app.connect('html-page-context', add_draw_button, priority=500.6)
    app.connect('html-page-context', add_user_button, priority=500.7)
    app.connect('write-started', write_static_files)

    app.add_node(dyn, html=(visit_dyn, depart_dyn))
    app.connect('tdoc-html-page-config', add_dyn_config)

    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


def on_config_inited(app, config):
    cv = config.values['html_title']
    super(cv.__class__, cv).__setattr__('default', lambda c: c.project)
    config.templates_path.append(str(_base / 'templates'))

    # Add exclude patterns for imports.
    if (g := '_import/**') not in config.exclude_patterns:
        config.exclude_patterns.append(g)

    # Add our own static paths, and a default one if it exists.
    app.add_static_dir(_base / 'static')
    app.add_static_dir(_base / 'static.gen')
    if '_static' not in config.html_static_path \
            and (app.confdir / '_static').exists():
        config.html_static_path.append('_static')

    # Override config defaults.
    if config.author and not config.copyright:
        config.copyright = f'%Y {config.author}'

    # Set a default favicon.
    if not config.html_favicon:
        config.html_favicon = str(_base / 'favicon.svg')

    # Override defaults in html_theme_options.
    opts = config.html_theme_options
    opts.setdefault('navbar_persistent', [])
    opts.setdefault('use_sidenotes', True)
    opts.setdefault('path_to_docs', 'docs')
    opts.setdefault('use_download_button', False)

    # Check that MathJax options are in the right config key.
    if config.mathjax3_config is not None:
        raise errors.ConfigError(
            "mathjax3_config: Set MathJax options in mathjax4_config instead")


def update_intersphinx(app):
    if 'tdoc-local' not in app.tags: return
    cl = app.config.intersphinx_cache_limit
    cache_time = time.time() - cl * 24 * 3600 if cl >= 0 else 0
    inv_config = _load._InvConfig.from_config(app.config)
    for name, (uri, locations) in app.config.intersphinx_mapping.values():
        dest = None
        for loc in locations:
            if loc is None:
                loc = posixpath.join(uri, html.INVENTORY_FILENAME)
            if '://' not in loc:
                if dest is None and not pathlib.Path(loc).is_absolute():
                    dest = app.srcdir / loc
                continue
            if dest is None: break
            cur_data = None
            with contextlib.suppress(OSError):
                if dest.stat().st_mtime >= cache_time: break
                cur_data = dest.read_bytes()
            with contextlib.suppress(Exception), \
                    display.progress_message(
                        f"updating intersphinx inventory '{name}'"
                        f" from {_load._get_safe_url(loc)}"):
                data = _load._fetch_inventory_url(
                    target_uri=uri, inv_location=loc, config=inv_config)[0]
                if data != cur_data:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(data)
                break


def set_base_html_context(app):
    # The config is used in domain.html.jinja.
    tdoc = tdoc_config(app)
    app.config.html_context['tdoc'] = util.to_json(tdoc).replace('<', '\\x3c')


def configure_templates(app):
    # Expand badge URLs.
    opts = app.builder.theme_options
    repo_url = opts.get('repository_url', '')
    if (badges := opts.get('tdoc_badges')) is None:
        badges = []
        if repo_url.startswith('https://github.com/'):
            badges.append({'href': '/actions/workflows/publish.yml',
                           'img': '/actions/workflows/publish.yml/badge.svg'})
    badges = [eb for b in badges
              if (eb := expand_badge(b, repo_url)) is not None]
    if badges:
        opts['tdoc_badges'] = badges
        st = app.builder.theme.sidebar_templates
        if 'tdoc-badges.html' not in st:
            try: i = st.index('search-button-field.html')
            except ValueError: i = len(st)
            app.builder.theme.sidebar_templates = \
                (*st[:i], 'tdoc-badges.html', *st[i:])


def expand_badge(badge, repo_url):
    href, img = badge['href'], badge['img']
    if '://' not in href:
        if not repo_url: return
        href = repo_url + href
    if '://' not in img:
        if not repo_url: return
        img = repo_url + img
    return {'href': href, 'img': img}


_dir_sig_md_re = re.compile(r'\{(.+?)\}(.*)$')

@patch.patch(rst, 'parse_directive')
def _rst_parse_directive(orig, d):
    # Add support for Markdown directive signatures.
    if not (sd := d.strip()).startswith('{'): return orig(d)
    if not (m := _dir_sig_md_re.match(sd)): return sd, ''
    pd, pa = m.groups()
    return pd.strip(), ' ' + pas if (pas := pa.strip()) else ''


def fix_rst_signatures(app, doctree):
    if app.config.tdoc_source_type != 'md': return
    # Convert rst signatures to Markdown style.
    for sig in doctree.findall(lambda n: isinstance(n, addnodes.desc_signature)
                                         and n.parent.get('domain') == 'rst'):
        if sig.parent.get('objtype') not in ('directive', 'role'): continue
        name = f'{{{sig['fullname']}}}'
        sig['_toc_name'] = name
        if (n := sig.next_node(addnodes.desc_name)) is not None:
            n.children = [nodes.Text(name)]


def set_html_context(app, page, template, context, doctree):
    context['tdoc_version'] = __version__
    context.setdefault('html_attrs', {})
    if 'tdoc-local' in app.tags: context['html_attrs']['data-tdoc-local'] = ''
    if v := app.config.license: context['license'] = v
    if v := app.config.license_url: context['license_url'] = v


@patch.template('pydata_sphinx_theme/layout.html')
def pydata_sphinx_theme_layout(contents, env):
    # BUG(pydata-sphinx-theme): The layout.html template doesn't allow
    # overriding the <html> tag. Patch the template source at load-time to add
    # attributes from the html_attrs context variable.
    return patch.sub(contents, r'(?m)^(<html[^>]*)(>)$',
                     r'\1{{ html_attrs | default({}) | xmlattr }}\2')


def add_js(app, page, template, context, doctree):
    tdoc = tdoc_config(app, page, doctree, context)

    # Temporarily override mathjax_path and mathjax4_config, then restore them
    # after mathjax.install_mathjax() has run.
    cfg = meta(app.env, page, 'mathjax', {})
    if (out := cfg.get('output', 'svg')) not in ('chtml', 'svg'):
        _log.warning("Invalid mathjax:output: metadata value (allowed: chtml, "
                     f"svg): {out}")
        out = 'svg'
    context['tdoc_mathjax_save'] = (app.config.mathjax_path,
                                    app.config.mathjax4_config)
    mj_url = tdoc['versions'].pop('mathjax')
    if mj_url.startswith('/'): mj_url = f'..{mj_url}'
    mj_cfg = app.config.mathjax4_config = merge_dict(
        copy.deepcopy(app.config.mathjax4_config), cfg)
    app.config.mathjax_path = f'{mj_url}/tex-{out}-nofont.js'
    loader = mj_cfg.setdefault('loader', {})
    exts = mj_cfg.pop('tdoc_tex_extensions', [])
    loader.setdefault('load', []).extend(f'[tex]/{e}' for e in exts)
    mj_cfg.setdefault('tex', {}).setdefault('packages', {}) \
        .setdefault('[+]', []).extend(exts)
    if 'tdoc-local' in app.tags:
        loader.setdefault('paths', {}).setdefault('fonts', '/_cache')

    # Set up early and on-load JavaScript.
    tdoc = util.to_json(tdoc).replace('<', '\\x3c')
    app.add_js_file(None, priority=0, body=f'const tdoc = {tdoc};')
    app.add_js_file('tdoc/early.js', priority=1)
    app.add_js_file('tdoc/load.js', type='module')
    if 'tdoc-local' in app.tags:
        app.add_js_file('tdoc/local.js', type='module')


def restore_mathjax(app, page, template, context, doctree):
    app.config.mathjax_path, app.config.mathjax4_config = \
        context['tdoc_mathjax_save']
    del context['tdoc_mathjax_save']


def tdoc_config(app, page=None, doctree=None, context=None):
    tdoc = {
        'conf': copy.deepcopy(app.config.tdoc),
        'domain_storage': copy.deepcopy(app.config.tdoc_domain_storage),
        'enable_sab': app.config.tdoc_enable_sab,
        'repos': app.config.tdoc_repos,
    }
    if is_local := 'tdoc-local' in app.tags: tdoc['local'] = True
    versions = tdoc['versions'] = meta(app.env, page, 'versions', {}).copy()
    for name, info in deps.info.items():
        if 'cdn' not in info or info.get('exclude_from_js', False): continue
        if '://' not in (v := versions.setdefault(name, info['version'])):
            versions[name] = f'/_cache/{name}@{v}' if is_local \
                             else deps.cdn_url(name, v)
    if v := app.config.tdoc_api: tdoc['api_url'] = v
    app.emit('tdoc-html-page-config', page, tdoc, doctree)
    return tdoc


def add_build_status(app, page, template, context, doctree):
    context["header_buttons"].append({
        'type': 'javascript',
        'javascript': 'tdoc.buildStatus()',
        'icon': 'fa-no-icon tfa',
        'tooltip': _("Build status"),
        'label': 'build-status',
    })


def add_draw_button(app, page, template, context, doctree):
    context["header_buttons"].append({
        'type': 'javascript',
        'javascript': 'tdoc.draw()',
        'icon': 'fa-pen tfa',
        'tooltip': _("Draw"),
        'label': 'draw',
    })


def add_user_button(app, page, template, context, doctree):
    context["header_buttons"].append({
        'type': 'group',
        'icon': 'fa-user tfa',
        'label': 'user',
        'buttons': [{
            'type': 'link',
            'icon': 'fa-user tfa',
            'text': "Not logged in",
            'label': 'user',
        }, {
            'type': 'javascript',
            'javascript': 'tdoc.login()',
            'icon': 'fa-right-to-bracket tfa',
            'text': "Log in",
            'label': 'login',
        }, {
            'type': 'javascript',
            'javascript': 'tdoc.settings()',
            'icon': 'fa-gear tfa',
            'text': "Settings",
            'label': 'settings',
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

    @property
    def reporter(self): return self.inliner.reporter


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


template_re = re.compile(r'(?s)([a-zA-Z0-9_-]+)(?:\((.*)\))?')


class Dyn(docutils.SphinxDirective):
    option_spec = {
        'class': opt_classes,
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

    def json_content(self):
        v = ''.join(f'{line}\n' for line in self.content)
        data = pyjson5.decode(f'{{{v}}}')
        return util.to_json(data) if data else None

    def populate(self, node): pass


class dyn(nodes.General, nodes.Element):
    @classmethod
    def has_type(cls, typ):
        return lambda n: isinstance(n, cls) and n['type'] == typ


def visit_dyn(self, node):
    attrs = {'type': node['type']}
    if v := node.get('name'): attrs['name'] = v
    if v := node.get('style'): attrs['style'] = v
    if v := node.get('args'): attrs['args'] = v
    if (v := node.get('attrs')) is not None: attrs |= v
    self.body.append(self.starttag(node, 'tdoc-dyn', '', **attrs))


def depart_dyn(self, node):
    self.body.append('</tdoc-dyn>\n')


def add_dyn_config(app, page, config, doctree):
    if page is None or doctree is None: return
    dcfg = {}
    for typ in {n['type'] for n in doctree.findall(dyn)}:
        dcfg[typ] = meta(app.env, page, typ, {})
    if dcfg: config['dyn'] = dcfg
