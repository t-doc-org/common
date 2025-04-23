# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

from http import HTTPStatus
import json
import re


def http_status(status):
    return f'{status} {status.phrase}'


def error(respond, status, exc_info=None):
    body = status.description.encode('utf-8')
    respond(http_status(status), [
        ('Content-Type', 'text/plain; charset=utf-8'),
        ('Content-Length', str(len(body))),
    ], exc_info)
    return [body]


class Error(Exception):
    def __init__(self, status=HTTPStatus.INTERNAL_SERVER_ERROR):
        super().__init__(status)

    @property
    def status(self): return self.args[0]


def method(env, *allowed):
    m = env['REQUEST_METHOD']
    if allowed and m not in allowed: raise Error(HTTPStatus.METHOD_NOT_ALLOWED)
    return m


def read_json(env):
    data = env['wsgi.input'].read(int(env.get('CONTENT_LENGTH', -1)))
    return json.loads(data)


def respond_json(respond, data):
    body = json.dumps(data, separators=(',', ':')).encode('utf-8')
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
