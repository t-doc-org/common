# Copyright 2026 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import contextlib
import functools
from http import cookies, HTTPMethod as Method, HTTPStatus as Status
import re
import threading
import time
from urllib import parse

from . import logs, util

_log = logs.logger(__name__)


# Import names from other modules.
globals().update((v.name, v) for v in Method)
globals().update((v.name, v) for v in Status)


def status(code): return f'{code} {code.phrase}'
def message(code): return f"{code.phrase}: {code.description}"


class Error(Exception):
    def __init__(self, status=INTERNAL_SERVER_ERROR, msg=None, headers=()):
        super().__init__(status, msg)
        self.headers = headers

    @property
    def code(self): return self.args[0]

    @property
    def message(self): return self.args[1]


# A regexp matching a hostname component.
hostname_re = r'(?:[a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9])'


def origins(scheme, domain):
    return rf'{re.escape(scheme)}://(?:{hostname_re}\.)?{re.escape(domain)}'


def origin(url):
    return parse.urlunsplit(parse.urlsplit(url)._replace(
            path='', query='', fragment=''))


def url_replace(url, **kwargs):
    parts = parse.urlsplit(url)
    parts = parts._replace(**kwargs)
    return parse.urlunsplit(parts)


def with_hash_params(url, params):
    return url_replace(url, fragment='?' + parse.urlencode(params))


class Context:
    __slots__ = ('local', 'domain', 'user', '_cookies', 'response_headers',
                 '_read_db', '_write_db')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.local = False
        self.domain = self.user = self._cookies = self.response_headers = None
        self._read_db = self._write_db = None

    def header(self, name, default=None): raise NotImplementedError()

    def add_headers(self, headers):
        if (rh := self.response_headers) is None:
            rh = self.response_headers = []
        rh.extend(headers)

    origin = property(lambda self: self.header('Origin'))
    server_host = property(lambda self: self.header('Host'))
    server_origin = property(util.not_implemented)
    remote_addr = property(util.not_implemented)

    @property
    def required_origin(self):
        if (v := self.header('Origin')) is None:
            raise Error(http.FORBIDDEN, "Missing Origin: header")
        return v if not self.local else ''

    @property
    def cookies(self):
        if (c := self._cookies) is None:
            c = self._cookies = cookies.SimpleCookie(self.header('Cookie'))
        return c

    @property
    def token(self):
        c = self.cookies
        if c.get(self._has_token) is not None:
            return m.value if (m := c.get(_token_cookie)) is not None \
                   else '<missing>'
        if (auth := self.header('Authorization')) is not None:
            parts = auth.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer': return parts[1]
        return ''

    def token_cookie_headers(self, token):
        max_age = 400 * 24 * 3600 if token else 0
        c = cookies.SimpleCookie()
        mt = cookie(c, _token_cookie, token or '', _token_cookie_attrs,
                    max_age=max_age)
        mp = cookie(c, self._has_token, '1', _has_token_cookie_attrs,
                    domain=None if self.local else self.domain, max_age=max_age)
        return [('Set-Cookie', mt), ('Set-Cookie', mp)]

    def set_token_cookie(self, token):
        self.add_headers(self.token_cookie_headers(token))

    @property
    def _has_token(self):
        suffix = '' if self.local else f'-{self.server_host}'
        return f'__Secure-tdoc-token{suffix}'

    @property
    def read_db(self): return self._read_db()

    @property
    def write_db(self): return self._write_db()


_token_cookie = '__Host-Http-tdoc-token'
_token_cookie_attrs = {
    'httponly': True,
    'path': '/',
    'samesite': 'Strict',
    'secure': True,
}
_has_token_cookie_attrs = {
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


class Cache:
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


class Handler:
    _types = {}

    def __init_subclass__(cls, /, **kwargs):
        if (type := kwargs.pop('type', None)) is not None:
            Handler._types[type] = cls
        super().__init_subclass__(**kwargs)

    def __init__(self):
        self.endpoints = {}
        self.updated()

    def add(self, name, fn): self.endpoints[name] = fn
    def updated(self): pass


class Dispatcher:
    def __init__(self):
        self._handlers = {name: cls() for name, cls in Handler._types.items()}

    def __getitem__(self, type): return self._handlers[type]

    def add(self, endpoints):
        updated = set()
        for name, fn in endpoints:
            try:
                updated.add(handler := self._handlers[fn._endpoint_type])
                handler.add(name, fn)
            except KeyError:
                raise TypeError(f"Unknown endpoint type: {et}")
        for handler in updated: handler.updated()


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
