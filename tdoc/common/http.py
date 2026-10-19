# Copyright 2026 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import contextlib
from http import cookies, HTTPMethod as Method, HTTPStatus as Status
import re
import threading
import time
# from urllib import parse

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


def with_hash_params(url, params):
    parts = parse.urlsplit(url)
    parts = parts._replace(fragment='?' + parse.urlencode(params))
    return parse.urlunsplit(parts)


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


def cookie_token(cookie):
    if cookie is None: return
    c = cookies.SimpleCookie(cookie)
    if (m := c.get(_token_cookie)) is not None: return m.value


def token_cookie_headers(token, domain, suffix):
    max_age = 400 * 24 * 3600 if token else 0
    c = cookies.SimpleCookie()
    mt = cookie(c, _token_cookie, token or '', _token_cookie_attrs,
                max_age=max_age)
    mf = cookie(c, f'__Secure-tdoc-token{suffix}', '1',
                _token_flag_cookie_attrs, domain=domain, max_age=max_age)
    return [('Set-Cookie', mt), ('Set-Cookie', mf)]


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
