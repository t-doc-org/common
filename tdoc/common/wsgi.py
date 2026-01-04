# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import contextlib
from email import utils
import functools
from http import HTTPMethod, HTTPStatus
import json
import re
import secrets
import sys
import threading
import time
from urllib import request
from wsgiref import util

from . import logs

log = logs.logger(__name__)
_missing = object()

# A regexp matching a hostname component.
hostname_re = r'(?:[a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9])'


def http_status(status):
    return f'{status} {status.phrase}'


class Error(Exception):
    def __init__(self, status=HTTPStatus.INTERNAL_SERVER_ERROR, msg=None):
        super().__init__(status, msg)

    @property
    def status(self): return self.args[0]

    @property
    def message(self): return self.args[1]


to_json = json.JSONEncoder(separators=(',', ':')).encode
to_json_sorted = json.JSONEncoder(separators=(',', ':'), sort_keys=True).encode


def cors(origins=(), methods=(), headers=(), max_age=None):
    if origins == '*':
        def allow_origin(origin): return [('Access-Control-Allow-Origin', '*')]
    elif isinstance(origins, str):
        pat = re.compile(origins)
        def allow_origin(origin):
            return [('Access-Control-Allow-Origin', origin)] \
                   if pat.fullmatch(origin) else []
    else:
        def allow_origin(origin):
            return [('Access-Control-Allow-Origin', origin)] \
                   if origin in origins else []

    achs = []
    if methods:
        achs.append(('Access-Control-Allow-Methods', ', '.join(methods)))
    if headers:
        achs.append(('Access-Control-Allow-Headers', ', '.join(headers)))
    if max_age is not None:
        achs.append(('Access-Control-Max-Age', str(max_age)))

    def decorator(fn):
        @functools.wraps(fn)
        def handle(env, respond, wr=None):
            def respond_with_allow_origin(status, headers, exc_info=None):
                return respond(
                    status, headers + allow_origin(env.get('HTTP_ORIGIN', '')),
                    exc_info)
            if (env['REQUEST_METHOD'] == 'OPTIONS' and
                    env.get('HTTP_ACCESS_CONTROL_REQUEST_METHOD') is not None):
                respond_with_allow_origin(http_status(HTTPStatus.OK), achs)
                return []
            return fn(env, respond_with_allow_origin)
        return handle
    return decorator


class Request:
    __slots__ = ('env', 'respond')

    def __init__(self, env, respond):
        self.env = env
        self.respond = respond

    method = property(lambda self: self.env['REQUEST_METHOD'])
    path = property(lambda self: self.env['PATH_INFO'])
    query = property(lambda self: self.env['QUERY_STRING'])
    content_type = property(lambda self: self.env.get('CONTENT_TYPE'))
    origin = property(lambda self: self.env.get('HTTP_ORIGIN'))
    remote_addr = property(lambda self: self.env.get('REMOTE_ADDR'))
    file_wrapper = property(lambda self: self.env.get('wsgi.file_wrapper',
                                                      util.FileWrapper))

    @property
    def required_origin(self):
        if (v := self.env.get('HTTP_ORIGIN')) is None:
            raise Error(HTTPStatus.PRECONDITION_FAILED,
                        "Missing Origin: header")
        return v if not self.dev else ''

    @property
    def token(self):
        if (auth := self.env.get('HTTP_AUTHORIZATION')) is None: return ''
        parts = auth.split()
        return parts[1] if len(parts) == 2 and parts[0].lower() == 'bearer' \
               else ''

    def uri(self, **kwargs):
        return util.request_uri(self.env, **kwargs)

    _content_methods = (HTTPMethod.POST, HTTPMethod.PUT, HTTPMethod.PATCH,
                        HTTPMethod.OPTIONS, HTTPMethod.DELETE)

    @property
    def has_content(self):
        return self.env['REQUEST_METHOD'] in self._content_methods \
               and self.env.get('CONTENT_TYPE') is not None

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

    def error(self, status, msg=None, exc_info=None):
        if msg is None: msg = status.description
        body = msg.encode('utf-8')
        self.respond(http_status(status), [
            ('Content-Type', 'text/plain; charset=utf-8'),
            ('Content-Length', str(len(body))),
        ], exc_info)
        return [body]

    def redirect(self, url):
        self.respond(http_status(HTTPStatus.FOUND), [
            ('Content-Type', 'text/plain; charset=utf-8'),
            ('Content-Length', '0'),
            ('Location', url),
        ])
        return []

    def respond_json(self, data):
        body = to_json(data).encode('utf-8')
        self.respond(http_status(HTTPStatus.OK), [
            ('Content-Type', 'application/json'),
            ('Content-Length', str(len(body))),
            ('Cache-Control', 'no-store'),
        ])
        return [body]


Request.attr('dev')


class Dispatcher:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._endpoints = {}
        for cls in self.__class__.__mro__:
            for k, v in cls.__dict__.items():
                if (ep := getattr(v, '_endpoint', False)) is False: continue
                if ep in self._endpoints: continue
                self._endpoints[ep] = getattr(self, k)

    def add_endpoint(self, name, fn):
        self._endpoints[name] = fn
        return fn

    def get_handler(self, env):
        script_name, path_info = env['SCRIPT_NAME'], env['PATH_INFO']
        if (name := util.shift_path_info(env)) is not None:
            if (h := self._endpoints.get(name)) is not None: return h
            env['SCRIPT_NAME'], env['PATH_INFO'] = script_name, path_info
        if (h := self._endpoints.get('/')) is not None: return h
        raise Error(HTTPStatus.NOT_FOUND)

    def __call__(self, env, respond, wr=None):
        if wr is None: wr = Request(env, respond)
        ctoken = logs.push_ctx(lambda: 'req:' + secrets.token_hex(8))
        log_level = logs.NOTSET
        log_status = '<unknown>'
        try:
            handler = self.get_handler(wr.env)
            try:
                self.pre_request(wr)
                log_level = getattr(handler, '_log_level', logs.NOTSET)
                if log_level != logs.NOTSET:
                    log_query = getattr(handler, '_log_query', True)
                    log.log(log_level,
                            "Start: %(method)s %(uri)s\n"
                            "origin=%(origin)s remote=%(remote)s user=%(user)s",
                            method=wr.method,
                            uri=wr.uri(include_query=log_query),
                            origin=wr.origin, remote=wr.remote_addr,
                            user=wr.user, event='req:start')
                    chained_respond = wr.respond
                    def respond_log(status, headers, exc_info=None):
                        nonlocal log_status
                        log_status = status
                        return chained_respond(status, headers, exc_info)
                    wr.respond = respond_log
                yield from self.handle_request(handler, wr)
            finally:
                self.post_request(wr)
        except Error as e:
            yield from wr.error(e.status, e.message, exc_info=sys.exc_info())
        except Exception as e:
            log.exception("Uncaught exception", event='req:exception')
            yield from wr.error(HTTPStatus.INTERNAL_SERVER_ERROR,
                                exc_info=sys.exc_info())
        finally:
            if log_level != logs.NOTSET:
                log.log(log_level, "Done: %(status)s", status=log_status,
                        event='req:end')
            logs.pop_ctx(ctoken)

    def pre_request(self, wr): pass

    def handle_request(self, handler, wr):
        return handler(wr.env, wr.respond, wr)

    def post_request(self, wr): pass


def endpoint(name, methods=None, final=True, require_authn=False,
             log_level=logs.INFO, log_query=True):
    if methods is None: raise TypeError("Missing methods")
    def decorator(fn):
        @functools.wraps(fn)
        def dfn(self, /, env, respond, wr):
            if final and wr.path: raise Error(HTTPStatus.NOT_FOUND)
            if wr.method not in methods:
                raise Error(HTTPStatus.METHOD_NOT_ALLOWED)
            if require_authn and wr.user is None:
                raise wsgi.Error(HTTPStatus.UNAUTHORIZED)
            return fn(self, wr)
        if name is not None: dfn._endpoint = name
        dfn._log_level = log_level
        dfn._log_query = log_query
        return dfn
    return decorator


def json_endpoint(name, methods=(HTTPMethod.POST,), require_authn=False,
                  log_level=logs.INFO, log_query=True):
    def decorator(fn):
        @endpoint(name, methods=methods, require_authn=require_authn,
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
                with request.urlopen(url, timeout=timeout) as f:
                    data = f.read()
                exp = now + self.min_lifetime
                with contextlib.suppress(Exception):
                    if (v := f.headers.get('expires')) is not None:
                        expires = utils.mktime_tz(utils.parsedate_tz(v))
                        if expires > exp: exp = expires
                self.cache[url] = (data, exp)
            except Exception:
                if data is None: raise
            return data
