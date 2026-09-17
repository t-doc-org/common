# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import collections
import contextlib
from email import utils
import functools
from http import cookies, HTTPMethod, HTTPStatus
import json
import re
import secrets
import sys
import threading
import time
from urllib import parse
from wsgiref import util as wsgiutil

from . import context, logs, util

_log = logs.logger(__name__)
_missing = object()

# A regexp matching a hostname component.
hostname_re = r'(?:[a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9])'

# A regexp matching the status code part of an HTTP status.
status_code_re = re.compile(r'^(\d{3}) ')


def http_status(status):
    return f'{status} {status.phrase}'


class Error(Exception):
    def __init__(self, status=HTTPStatus.INTERNAL_SERVER_ERROR, msg=None,
                 headers=()):
        super().__init__(status, msg)
        self.headers = headers

    @property
    def status(self): return self.args[0]

    @property
    def message(self): return self.args[1]


def cors(origins=(), methods=(), headers=(), max_age=None, credentials=False):
    achs = []
    if origins == '*':
        def allow_origin(origin): return [('Access-Control-Allow-Origin', '*')]
    elif isinstance(origins, str):
        achs.append(('Vary', 'Origin'))
        pat = re.compile(origins)
        def allow_origin(origin):
            return [('Access-Control-Allow-Origin', origin)] \
                   if pat.fullmatch(origin) else []
    else:
        achs.append(('Vary', 'Origin'))
        def allow_origin(origin):
            return [('Access-Control-Allow-Origin', origin)] \
                   if origin in origins else []
    if methods:
        achs.append(('Access-Control-Allow-Methods', ','.join(methods)))
    if headers:
        achs.append(('Access-Control-Allow-Headers', ','.join(headers)))
    if max_age is not None:
        achs.append(('Access-Control-Max-Age', str(max_age)))
    acac = [('Access-Control-Allow-Credentials', 'true')] if credentials else []

    def decorator(fn):
        @functools.wraps(fn)
        def handle(env, respond, wr=None):
            def respond_with_headers(status, headers, exc_info=None):
                return respond(
                    status,
                    headers + allow_origin(env.get('HTTP_ORIGIN', '')) + acac,
                    exc_info)
            if (env['REQUEST_METHOD'] == 'OPTIONS' and
                    env.get('HTTP_ACCESS_CONTROL_REQUEST_METHOD') is not None):
                respond_with_headers(http_status(HTTPStatus.OK), achs)
                return []
            return fn(env, respond_with_headers)
        return handle
    return decorator


_token_cookie = '__Host-Http-tdoc-token'
_token_cookie_attrs = {
    'httponly': True,
    'path': '/',
    'samesite': 'Strict',
    'secure': True,
}
_token_flag_cookie_attrs = {
    'path': '/',
    'samesite': 'Strict',
    'secure': True,
}


def cookie(c, name, value, attrs, *, domain=None, max_age=None):
    c[name] = value
    m = c[name]
    m.update(attrs)
    if domain is not None: m['domain'] = domain
    if max_age is not None: m['max-age'] = max_age
    return m.OutputString()


def origin(url):
    return parse.urlunsplit(parse.urlsplit(url)._replace(
            path='', query='', fragment=''))


def with_hash_params(url, params):
    parts = parse.urlsplit(url)
    parts = parts._replace(fragment='?' + parse.urlencode(params))
    return parse.urlunsplit(parts)


class Request:
    __slots__ = ('env', '_respond', '_post', 'status')

    def __init__(self, env, respond):
        self.env = env
        self._respond = respond
        self._post = []
        self.status = None

    method = property(lambda self: self.env['REQUEST_METHOD'])
    script = property(lambda self: self.env['SCRIPT_NAME'])
    path = property(lambda self: self.env['PATH_INFO'])
    query = property(lambda self: self.env['QUERY_STRING'])
    content_type = property(lambda self: self.env.get('CONTENT_TYPE'))
    origin = property(lambda self: self.env.get('HTTP_ORIGIN'))
    accept = property(lambda self: self.env.get('HTTP_ACCEPT'))
    accept_encoding = property(
        lambda self: self.env.get('HTTP_ACCEPT_ENCODING'))
    remote_addr = property(lambda self: self.env.get('REMOTE_ADDR'))
    file_wrapper = property(lambda self: self.env.get('wsgi.file_wrapper',
                                                      wsgiutil.FileWrapper))
    sec_fetch_site = property(lambda self: self.env.get('HTTP_SEC_FETCH_SITE'))
    csrf = property(lambda self: self.env.get('HTTP_X_CSRF'))

    @property
    def required_origin(self):
        if (v := self.env.get('HTTP_ORIGIN')) is None:
            raise Error(HTTPStatus.PRECONDITION_FAILED,
                        "Missing Origin: header")
        return v if not self.local else ''

    @property
    def token(self):
        if (h := self.env.get('HTTP_COOKIE')) is not None:
            c = cookies.SimpleCookie(h)
            if (m := c.get(_token_cookie)) is not None: return m.value
        if (auth := self.env.get('HTTP_AUTHORIZATION')) is not None:
            parts = auth.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer': return parts[1]
        return ''

    def uri(self, include_query=True):
        return wsgiutil.request_uri(self.env, include_query)

    _content_methods = (HTTPMethod.POST, HTTPMethod.PUT, HTTPMethod.PATCH,
                        HTTPMethod.OPTIONS, HTTPMethod.DELETE)

    @property
    def has_content(self):
        return self.env['REQUEST_METHOD'] in self._content_methods \
               and self.env.get('CONTENT_TYPE') is not None

    def respond(self, status, headers, exc_info=None):
        if self.status is None: self.status = status
        self._respond(status, headers, exc_info)

    @property
    def status_code(self):
        return m[1] if (s := self.status) and (m := status_code_re.search(s)) \
               else None

    def post(self, fn): self._post.append(fn)

    def run_post(self):
        post = self._post
        while post:
            try: post.pop()()
            except Exception: pass

    # TODO: Simplify the attr system

    @classmethod
    def attr(cls, name, *, default=None, cache=True):
        gname = f'tdoc.{name}.get'
        if not cache:
            setattr(cls, name, property(lambda self: self.env[gname]()))
            return
        pname = f'tdoc.{name}'
        dname = f'tdoc.{name}.del'
        def fget(self):
            if (v := self.env.get(pname, _missing)) is _missing:
                fn = self.env.get(gname)
                v = self.env[pname] = fn() if fn is not None else default
            return v
        def fset(self, v): self.env[pname] = v
        def fdel(self):
            if (v := self.env.pop(pname, _missing)) is _missing: return
            if (fn := self.env.get(dname)) is not None: fn(v)
        setattr(cls, name, property(fget, fset, fdel))

    def attr_handlers(self, name, fget=None, fdel=None):
        if fget is not None: self.env[f'tdoc.{name}.get'] = fget
        if fdel is not None: self.env[f'tdoc.{name}.del'] = fdel

    @property
    def json(self):
        if (v := self.env.get('tdoc.input.json')) is not None: return v
        if self.env.get('CONTENT_TYPE') != 'application/json':
            raise Error(HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
        try:
            data = self.env['wsgi.input'].read(
                int(self.env.get('CONTENT_LENGTH', -1)))
            v = self.env['tdoc.input.json'] = json.loads(data)
            return v
        except Exception as e:
            raise Error(HTTPStatus.BAD_REQUEST)

    def add_response_headers(self, *headers):
        if (rh := self.response_headers) is None:
            rh = self.response_headers = []
        rh.extend(headers)

    def token_cookie_headers(self, token):
        if self.local:
            domain, suffix = None, ''
        else:
            domain = self.domain
            url = parse.urlsplit(self.uri(include_query=False))
            suffix = f'-{url.hostname}'
        max_age = 400 * 24 * 3600 if token else 0
        c = cookies.SimpleCookie()
        mt = cookie(c, _token_cookie, token or '', _token_cookie_attrs,
                    max_age=max_age)
        mf = cookie(c, f'__Secure-tdoc-token{suffix}', '1',
                    _token_flag_cookie_attrs, domain=domain, max_age=max_age)
        return [('Set-Cookie', mt), ('Set-Cookie', mf)]

    def set_token_cookie(self, token):
        self.add_response_headers(*self.token_cookie_headers(token))

    def error(self, status, msg=None, exc_info=None, headers=()):
        if msg is None: msg = status.description
        body = msg.encode('utf-8')
        self.respond(http_status(status), [
            ('Cache-Control', 'no-store'),
            ('Content-Type', 'text/plain; charset=utf-8'),
            ('Content-Length', str(len(body))),
            *headers,
        ], exc_info)
        return [body]

    def redirect(self, url, status=HTTPStatus.FOUND):
        self.respond(http_status(status), [
            ('Cache-Control', 'no-store'),
            ('Content-Type', 'text/plain; charset=utf-8'),
            ('Content-Length', '0'),
            ('Location', url),
            *(self.response_headers or ()),
        ])
        return []

    def respond_json(self, data):
        body = util.to_json(data).encode('utf-8')
        self.respond(http_status(HTTPStatus.OK), [
            ('Cache-Control', 'no-store'),
            ('Content-Type', 'application/json'),
            ('Content-Length', str(len(body))),
            *(self.response_headers or ()),
        ])
        return [body]


Request.attr('local')
Request.attr('domain')
Request.attr('response_headers')


Trie = lambda: collections.defaultdict(Trie)

def longest_prefix(trie):
    def sub(subs):
        return '|'.join(
            (f'/{re.escape(n)}' if n else '') + (f'(?:{sub(s)})' if s else '')
            for n, s in sorted(subs.items(), key=lambda v: (-len(v[0]), v[0])))
    return f'^({sub(trie) if trie else r'^\b$'})(/.*|)$'


class Dispatcher:
    def __init__(self):
        self._pre, self._post = [], []
        self._endpoints = {}
        self._update_endpoints_re()

    def pre(self, fn): self._pre.append(fn)

    def add(self, endpoints):
        self._endpoints.update(endpoints)
        self._update_endpoints_re()

    def _update_endpoints_re(self):
        trie = Trie()
        for n in self._endpoints:
            node = trie
            for p in n.lstrip('/').split('/'): node = node[p]
        self._endpoints_re = re.compile(longest_prefix(trie))

    def get_handler(self, env):
        if (p := env.get('PATH_INFO')) \
                and (m := self._endpoints_re.fullmatch(p)) \
                and (h := self._endpoints[(ep := m[1])]) is not None:
            env['SCRIPT_NAME'] += ep
            env['PATH_INFO'] = m[2]
            return h

    def __call__(self, env, respond):
        wr = Request(env, respond)
        log_level, log_query, log_args = logs.NOTSET, False, None
        token = context.ctx.set('req:' + secrets.token_hex(8))
        try:
            handler = self.get_handler(wr.env)
            for fn in self._pre: fn(wr)
            if handler is None: raise Error(HTTPStatus.NOT_FOUND)
            log_level = getattr(handler, '_log_level', logs.NOTSET)
            log_query = getattr(handler, '_log_query', True)
            if log_level != logs.NOTSET:
                log_args = self._log_args(wr, log_query)
                msg = "%(method)s %(uri)s\n" \
                      "origin=%(origin)s remote=%(remote)s"
                if 'user' in log_args: msg += " user=0x%(user)016x"
                _log.log(log_level, msg, event='req:start', **log_args)
            yield from handler(wr)
        except Error as e:
            yield from wr.error(e.status, e.message, exc_info=sys.exc_info(),
                                headers=e.headers)
        except Exception as e:
            if log_args is None: log_args = self._log_args(wr, log_query)
            _log.exception("Uncaught exception", event='req:exception',
                           **log_args)
            yield from wr.error(HTTPStatus.INTERNAL_SERVER_ERROR,
                                exc_info=sys.exc_info())
        finally:
            if log_level != logs.NOTSET:
                if log_args is None: log_args = self._log_args(wr, log_query)
                _log.log(log_level, "%(status)s", event='req:end',
                         status=wr.status or '<unknown>', **log_args)
            wr.run_post()
            context.ctx.reset(token)

    @staticmethod
    def _log_args(wr, include_query):
        kwargs = {'method': wr.method,
                  'uri': wr.uri(include_query=include_query),
                  'origin': wr.origin, 'remote': wr.remote_addr}
        if (v := wr.user) is not None: kwargs['user'] = v
        return kwargs


def endpoints(obj):
    for cls in reversed(obj.__class__.__mro__):
        for k, v in cls.__dict__.items():
            if (ep := getattr(v, '_endpoint', False)) is False: continue
            yield (f'/{ep}' if ep else ''), getattr(obj, k)


def sub_endpoints(parent, endpoints):
    for name, fn in endpoints:
        yield f'/{parent}{name}', fn


def wrap_endpoints(wrap):
    def decorator(fn):
        @functools.wraps(fn)
        def dfn(self, /, reg):
            for name, hfn in fn(self, reg):
                yield name, wrap(hfn)
        return dfn
    return decorator


def endpoint(name, methods=None, final=True, require_authn=False,
             csrf=True, log_level=logs.INFO, log_query=True):
    if methods is None: raise TypeError("Missing methods")
    def decorator(fn):
        @functools.wraps(fn)
        def dfn(self, /, wr):
            if final and wr.path: raise Error(HTTPStatus.NOT_FOUND)
            if wr.method not in methods:
                raise Error(HTTPStatus.METHOD_NOT_ALLOWED, headers=[
                    ('Allow', ','.join(methods)),
                ])
            if require_authn and wr.user is None:
                raise Error(HTTPStatus.UNAUTHORIZED)
            if csrf and (wr.sec_fetch_site not in ('same-origin', 'same-site')
                         or wr.csrf is None):
                raise Error(HTTPStatus.FORBIDDEN)
            return fn(self, wr)
        if name is not None: dfn._endpoint = name
        dfn._log_level = log_level
        dfn._log_query = log_query
        return dfn
    return decorator


def json_endpoint(name, methods=(HTTPMethod.POST,), require_authn=False,
                  csrf=True, log_level=logs.INFO, log_query=True):
    def decorator(fn):
        @endpoint(name, methods=methods, require_authn=require_authn, csrf=csrf,
                  log_level=log_level, log_query=log_query)
        @functools.wraps(fn)
        def dfn(self, /, wr):
            return wr.respond_json(
                fn(self, wr, wr.json if wr.has_content else None))
        return dfn
    return decorator


class HttpCache:
    def __init__(self, min_lifetime=10 * 60):
        self.min_lifetime = min_lifetime
        self.lock = threading.Lock()
        self.cache = {}

    def get(self, url, timeout=None):
        with self.lock:
            data, exp = self.cache.get(url, (None, None))
            now = time.time()
            if data is not None and now < exp: return data
            try:
                with util.urlopen(url, timeout=timeout) as f: data = f.read()
                exp = now + self.min_lifetime
                with contextlib.suppress(Exception):
                    if (v := f.headers.get('expires')) is not None:
                        expires = utils.mktime_tz(utils.parsedate_tz(v))
                        if expires > exp: exp = expires
                self.cache[url] = (data, exp)
            except Exception:
                if data is None: raise
            return data
