# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

from http import HTTPStatus
import json
import re


def http_status(status):
    return f'{status} {status.phrase}'


def error(respond, status, msg=None, exc_info=None):
    if msg is None: msg = status.description
    body = msg.encode('utf-8')
    respond(http_status(status), [
        ('Content-Type', 'text/plain; charset=utf-8'),
        ('Content-Length', str(len(body))),
    ], exc_info)
    return [body]


class Error(Exception):
    def __init__(self, status=HTTPStatus.INTERNAL_SERVER_ERROR, msg=None):
        super().__init__(status, msg)

    @property
    def status(self): return self.args[0]

    @property
    def message(self): return self.args[1]


def is_dev(env):
    return env.get('tdoc.dev', False)


def method(env, *allowed):
    m = env['REQUEST_METHOD']
    if allowed and m not in allowed: raise Error(HTTPStatus.METHOD_NOT_ALLOWED)
    return m


def origin(env):
    if (v := env.get('HTTP_ORIGIN')) is None:
        raise Error(HTTPStatus.PRECONDITION_FAILED, "Missing Origin: header")
    return v if not is_dev(env) else ''


def authorization(env):
    if (auth := env.get('HTTP_AUTHORIZATION')) is None: return ''
    parts = auth.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer': return ''
    return parts[1]


def to_json(data, sort_keys=False):
    return json.dumps(data, separators=(',', ':'), sort_keys=sort_keys)


def read_json(env):
    try:
        data = env['wsgi.input'].read(int(env.get('CONTENT_LENGTH', -1)))
        return json.loads(data)
    except Exception as e:
        raise Error(HTTPStatus.BAD_REQUEST)


def respond_json(respond, data):
    body = to_json(data).encode('utf-8')
    respond(http_status(HTTPStatus.OK), [
        ('Content-Type', 'application/json'),
        ('Content-Length', str(len(body))),
        ('Cache-Control', 'no-store'),
    ])
    return [body]


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
        def handle(env, respond):
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
