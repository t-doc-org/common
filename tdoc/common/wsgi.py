# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import collections
from email import utils
import functools
import json
import re
import secrets
import sys
import time
from urllib import parse
from wsgiref import util as wsgiutil

import prometheus_client as pc

from . import context, http, logs, util

_log = logs.logger(__name__)

http_request_duration = pc.Histogram(
    subsystem='http', name='request_duration', unit='seconds',
    labelnames=('method', 'endpoint', 'status'),
    buckets=[0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5,
             1.0, 2.0, 5.0, 10.0],
    documentation="The duration of HTTP requests.")
http_active_requests = pc.Gauge(
    subsystem='http', name='active_requests',
    labelnames=('method', 'endpoint'),
    documentation="The number of active HTTP requests.")


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
        def handle(env, respond, ctx=None):
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


class Context(http.Context):
    __slots__ = ('env', '_respond', '_post', 'status')

    def __init__(self, env, respond):
        super().__init__()
        self.env = env
        self._respond = respond
        self._post = []
        self.status = None

    def header(self, name, default=None):
        return self.env.get(f'HTTP_{name.replace('-', '_').upper()}', default)

    server_host = property(lambda self:
        parse.urlsplit(wsgiutil.application_uri(self.env)).hostname)
    server_origin = property(lambda self:
        http.origin(wsgiutil.application_uri(self.env)))
    remote_addr = property(lambda self: self.env.get('REMOTE_ADDR'))

    method = property(lambda self: self.env['REQUEST_METHOD'])
    script = property(lambda self: self.env['SCRIPT_NAME'])
    path = property(lambda self: self.env['PATH_INFO'])
    query = property(lambda self: self.env['QUERY_STRING'])
    content_type = property(lambda self: self.env.get('CONTENT_TYPE'))
    accept = property(lambda self: self.env.get('HTTP_ACCEPT'))
    accept_encoding = property(
        lambda self: self.env.get('HTTP_ACCEPT_ENCODING'))
    file_wrapper = property(lambda self: self.env.get('wsgi.file_wrapper',
                                                      wsgiutil.FileWrapper))
    sec_fetch_site = property(lambda self: self.env.get('HTTP_SEC_FETCH_SITE'))
    csrf = property(lambda self: self.env.get('HTTP_X_CSRF'))

    def uri(self, include_query=False):
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


class Handler(http.Handler, type='wsgi'):
    def __init__(self):
        super().__init__()
        self._pre = []

    def pre(self, fn): self._pre.append(fn)

    def updated(self):
        super().updated()
        trie = Trie()
        for n in self.endpoints:
            node = trie
            for p in n.lstrip('/').split('/'): node = node[p]
            node['']  # Ensure prefix paths match
        self._endpoints_re = re.compile(longest_prefix(trie))

    def endpoint(self, env):
        if (p := env.get('PATH_INFO')) \
                and (m := self._endpoints_re.fullmatch(p)) \
                and (fn := self.endpoints.get(ep := m[1])) is not None:
            env['SCRIPT_NAME'] += ep
            env['PATH_INFO'] = m[2]
            return fn

    def handle(self, env, respond):
        start, ep = time.monotonic(), None
        ctx = Context(env, respond)
        @ctx.post
        def record_duration():
            if ep is None: return
            http_request_duration \
                .labels(ctx.method, ep, str(s) if (s := ctx.status) else '0') \
                .observe(time.monotonic() - start)

        log_level, log_query, log_args = logs.NOTSET, False, None
        token = context.ctx.set('req:' + secrets.token_hex(8))
        try:
            # Find the endpoint
            if (endpoint := self.endpoint(ctx.env)) is None:
                raise http.Error(http.NOT_FOUND)

            # Run pre-request handlers. This includes authentication.
            for fn in self._pre: fn(ctx)

            # Record the active request in metrics.
            ep = ctx.script or '/'
            (active := http_active_requests.labels(ctx.method, ep)).inc()
            ctx.post(active.dec)

            # Log the start of the request.
            log_level = getattr(endpoint, '_log_level', logs.NOTSET)
            log_query = getattr(endpoint, '_log_query', True)
            if log_level != logs.NOTSET:
                log_args = self._log_args(ctx, log_query)
                msg = "%(method)s %(uri)s\n" \
                      "origin=%(origin)s remote=%(remote)s"
                if 'user' in log_args: msg += " user=0x%(user)016x"
                _log.log(log_level, msg, event='req:start', **log_args)

            # Run the endpoint.
            yield from endpoint(ctx)
        except http.Error as e:
            yield from ctx.error(e.code, e.message, exc_info=sys.exc_info(),
                                headers=e.headers)
        except Exception as e:
            if log_args is None: log_args = self._log_args(ctx, log_query)
            _log.exception("Uncaught exception", event='req:exception',
                           **log_args)
            yield from ctx.error(http.INTERNAL_SERVER_ERROR,
                                exc_info=sys.exc_info())
        finally:
            if log_level != logs.NOTSET:
                st = ctx.status
                if log_args is None: log_args = self._log_args(ctx, log_query)
                _log.log(log_level, "%(code)s %(phrase)s", event='req:end',
                         code=int(st) if st else 0,
                         phrase=st.phrase if st else 'status unknown',
                         **log_args)
            ctx.run_post()
            context.ctx.reset(token)

    @staticmethod
    def _log_args(ctx, include_query):
        kwargs = {'method': ctx.method,
                  'uri': ctx.uri(include_query=include_query),
                  'origin': ctx.origin, 'remote': ctx.remote_addr}
        if (v := ctx.user) is not None: kwargs['user'] = v
        return kwargs


def endpoint(name, methods=None, final=True, require_authn=False,
             csrf=True, log_level=logs.INFO, log_query=True):
    if methods is None: raise TypeError("Missing methods")
    if isinstance(methods, http.Method): methods = (methods,)
    def decorator(fn):
        @functools.wraps(fn)
        def dfn(self, /, ctx):
            if final and ctx.path: raise http.Error(http.NOT_FOUND)
            if ctx.method not in methods:
                raise http.Error(http.METHOD_NOT_ALLOWED, headers=[
                    ('Allow', ','.join(methods)),
                ])
            if require_authn and ctx.user is None:
                raise http.Error(http.UNAUTHORIZED)
            if csrf and (ctx.sec_fetch_site not in ('same-origin', 'same-site')
                         or ctx.csrf is None):
                raise http.Error(http.FORBIDDEN)
            return fn(self, ctx)
        dfn._endpoint = name
        dfn._endpoint_type = 'wsgi'
        dfn._require_authn = require_authn
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
        def dfn(self, /, ctx):
            return ctx.respond_json(
                fn(self, ctx, ctx.json if ctx.has_content else None))
        dfn._fn = fn
        return dfn
    return decorator
