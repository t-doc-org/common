# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import collections
from collections import abc
import contextlib
from email import utils
import functools
import json
import re
import secrets
import sys
from urllib import parse
from wsgiref import util as wsgiutil

from . import context, http, logs, util

_log = logs.logger(__name__)


def cors(origins=util.no_match, methods=(), headers=(), max_age=None,
         credentials=False):
    achs = []
    if origins == '*':
        def allow_origin(origin): return [('Access-Control-Allow-Origin', '*')]
    else:
        achs.append(('Vary', 'Origin'))
        pat = re.compile(origins)
        def allow_origin(origin):
            return [('Access-Control-Allow-Origin', origin)] \
                   if pat.fullmatch(origin) else []
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
                respond_with_headers(http.status(http.OK), achs)
                return []
            return fn(env, respond_with_headers)
        return handle
    return decorator


class Request:
    __slots__ = ('env', '_respond', '_post', 'status', 'local', 'domain',
                 'user', 'response_headers', '_read_db', '_write_db')

    def __init__(self, env, respond):
        self.env = env
        self._respond = respond
        self._post = []
        self.status = None
        self.local = False
        self.domain = self.user = self.response_headers = None
        self._read_db = self._write_db = None

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
            raise http.Error(http.FORBIDDEN, "Missing Origin: header")
        return v if not self.local else ''

    @property
    def token(self):
        if (v := http.cookie_token(self.env.get('HTTP_COOKIE'))) is not None:
            return v
        if (auth := self.env.get('HTTP_AUTHORIZATION')) is not None:
            parts = auth.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer': return parts[1]
        return ''

    def uri(self, include_query=True):
        return wsgiutil.request_uri(self.env, include_query)

    _content_methods = (http.POST, http.PUT, http.PATCH, http.OPTIONS,
                        http.DELETE)

    @property
    def has_content(self):
        return self.env['REQUEST_METHOD'] in self._content_methods \
               and self.env.get('CONTENT_TYPE') is not None

    def respond(self, status, headers, exc_info=None):
        if self.status is None: self.status = status
        self._respond(http.status(status), headers, exc_info)

    def post(self, fn): self._post.append(fn)

    def run_post(self):
        post = self._post
        while post: post.pop()()

    @property
    def read_db(self): return self._read_db()

    @property
    def write_db(self): return self._write_db()

    @property
    def json(self):
        if (v := self.env.get('tdoc.input.json')) is not None: return v
        if self.env.get('CONTENT_TYPE') != 'application/json':
            raise http.Error(http.UNSUPPORTED_MEDIA_TYPE)
        try:
            data = self.env['wsgi.input'].read(
                int(self.env.get('CONTENT_LENGTH', -1)))
            v = self.env['tdoc.input.json'] = json.loads(data)
            return v
        except Exception as e:
            raise http.Error(http.BAD_REQUEST)

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
        return http.token_cookie_headers(token, domain, suffix)

    def set_token_cookie(self, token):
        self.add_response_headers(*self.token_cookie_headers(token))

    def error(self, status, msg=None, exc_info=None, headers=()):
        if msg is None: msg = http.message(status)
        body = msg.encode()
        self.respond(status, [
            ('Cache-Control', 'no-store'),
            ('Content-Type', 'text/plain; charset=utf-8'),
            ('Content-Length', str(len(body))),
            *headers,
        ], exc_info)
        return [body]

    def redirect(self, url, status=http.FOUND):
        self.respond(status, [
            ('Cache-Control', 'no-store'),
            ('Content-Type', 'text/plain; charset=utf-8'),
            ('Content-Length', '0'),
            ('Location', url),
            *(self.response_headers or ()),
        ])
        return []

    def respond_json(self, data):
        body = util.to_json(data).encode()
        self.respond(http.OK, [
            ('Cache-Control', 'no-store'),
            ('Content-Type', 'application/json'),
            ('Content-Length', str(len(body))),
            *(self.response_headers or ()),
        ])
        return [body]


Trie = lambda: collections.defaultdict(Trie)

def longest_prefix(trie):
    def sub(subs):
        return '|'.join(
            (f'/{re.escape(n)}' if n else '')
            + (f'(?:{sub(s)})' if len(s) > 1 else '')
            for n, s in sorted(subs.items(), key=lambda v: (-len(v[0]), v[0])))
    return f'^({sub(trie) if trie else util.no_match})(/.*|)$'


class Dispatcher:
    # TODO: Move Dispatcher to a separate dispatch.py
    # TODO: Move websocket handlers here

    def __init__(self):
        self._pre = []
        self._pre_ws = []
        self._endpoints = {}
        self._endpoints_ws = {}
        self._update_endpoints_re()

    def pre(self, fn): self._pre.append(fn)
    def pre_ws(self, fn): self._pre_ws.append(fn)

    async def run_pre_ws(self, conn):
        for fn in self._pre_ws:
            if isinstance(res := fn(conn), abc.Awaitable): await res

    def add(self, endpoints):
        for name, fn in endpoints:
            if (et := fn._endpoint_type) == 'wsgi':
                self._endpoints[name] = fn
            elif et == 'ws':
                self._endpoints_ws[name] = fn
            else:
                raise TypeError(f"Unknown endpoint type: {et}")
        self._update_endpoints_re()

    def _update_endpoints_re(self):
        trie = Trie()
        for n in self._endpoints:
            node = trie
            for p in n.lstrip('/').split('/'): node = node[p]
            node['']  # Ensure prefix paths match
        self._endpoints_re = re.compile(longest_prefix(trie))

    def handler_ws(self, endpoint):
        return self._endpoints_ws.get(endpoint)

    def get_handler(self, env):
        if (p := env.get('PATH_INFO')) \
                and (m := self._endpoints_re.fullmatch(p)) \
                and (h := self._endpoints.get(ep := m[1])) is not None:
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
            if handler is None: raise http.Error(http.NOT_FOUND)
            log_level = getattr(handler, '_log_level', logs.NOTSET)
            log_query = getattr(handler, '_log_query', True)
            if log_level != logs.NOTSET:
                log_args = self._log_args(wr, log_query)
                msg = "%(method)s %(uri)s\n" \
                      "origin=%(origin)s remote=%(remote)s"
                if 'user' in log_args: msg += " user=0x%(user)016x"
                _log.log(log_level, msg, event='req:start', **log_args)
            yield from handler(wr)
        except http.Error as e:
            yield from wr.error(e.code, e.message, exc_info=sys.exc_info(),
                                headers=e.headers)
        except Exception as e:
            if log_args is None: log_args = self._log_args(wr, log_query)
            _log.exception("Uncaught exception", event='req:exception',
                           **log_args)
            yield from wr.error(http.INTERNAL_SERVER_ERROR,
                                exc_info=sys.exc_info())
        finally:
            if log_level != logs.NOTSET:
                st = wr.status
                if log_args is None: log_args = self._log_args(wr, log_query)
                _log.log(log_level, "%(code)s %(phrase)s", event='req:end',
                         code=int(st) if st else 0,
                         phrase=st.phrase if st else 'status unknown',
                         **log_args)
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


def sub_endpoints(endpoints, **parents):
    for name, fn in endpoints:
        if p := parents.get(fn._endpoint_type): name = f'/{p}{name}'
        yield name, fn


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
            if final and wr.path: raise http.Error(http.NOT_FOUND)
            if wr.method not in methods:
                raise http.Error(http.METHOD_NOT_ALLOWED, headers=[
                    ('Allow', ','.join(methods)),
                ])
            if require_authn and wr.user is None:
                raise http.Error(http.UNAUTHORIZED)
            if csrf and (wr.sec_fetch_site not in ('same-origin', 'same-site')
                         or wr.csrf is None):
                raise http.Error(http.FORBIDDEN)
            return fn(self, wr)
        dfn._endpoint = name
        dfn._endpoint_type = 'wsgi'
        dfn._log_level = log_level
        dfn._log_query = log_query
        return dfn
    return decorator


def json_endpoint(name, methods=(http.POST,), require_authn=False,
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
