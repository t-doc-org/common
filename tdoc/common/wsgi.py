# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

from http import HTTPStatus
import json
import re


def http_status(status):
    return f'{status} {status.phrase}'


def error(respond, status):
    respond(http_status(status), [
        ('Content-Type', 'text/plain; charset=utf-8'),
    ])
    return [status.description.encode('utf-8')]


def method(env, respond, *allowed):
    m = env['REQUEST_METHOD']
    if allowed and m not in allowed:
        return None, error(respond, HTTPStatus.METHOD_NOT_ALLOWED)
    return m, None


def read_json(env):
    data = env['wsgi.input'].read(int(env.get('CONTENT_LENGTH', -1)))
    return json.loads(data)


def respond_json(respond, data):
    body = json.dumps(data, separators=(',', ':')).encode('utf-8')
    respond(http_status(HTTPStatus.OK), [
        ('Content-Type', 'application/json'),
        ('Content-Length', str(len(body))),
        ('Cache-Control', 'no-cache'),
    ])
    return [body]


def cors(origins=(), methods=(), headers=(), max_age=None):
    def allow_origin(origin):
        return [('Access-Control-Allow-Origin', origin)] \
               if re.fullmatch(origin) else []
    if isinstance(origins, str) and origins != '*':
        origins = re.compile(origins)
    if origins == '*' or '*' in origins:
        def allow_origin(origin): return [('Access-Control-Allow-Origin', '*')]
    else:
        origins = re.compile('|'.join(f'(?:{re.escape(o)})' for o in origins))

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
