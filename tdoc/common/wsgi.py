# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

from http import HTTPStatus
import json as _json


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
    return _json.loads(data)


def respond_json(respond, data):
    body = _json.dumps(data, separators=(',', ':')).encode('utf-8')
    respond(http_status(HTTPStatus.OK), [
        ('Content-Type', 'application/json'),
        ('Content-Length', str(len(body))),
        ('Cache-Control', 'no-cache'),
    ])
    return [body]


def cors(origins=(), methods=(), headers=(), max_age=None):
    achs = []
    if methods:
        achs.append(('Access-Control-Allow-Methods', ', '.join(methods)))
    if headers:
        achs.append(('Access-Control-Allow-Headers', ', '.join(headers)))
    if max_age is not None:
        achs.append(('Access-Control-Max-Age', str(max_age)))

    def decorator(fn):
        def handle(env, respond):
            if '*' in origins:
                ao = [('Access-Control-Allow-Origin', '*')]
            elif (origin := env.get('HTTP_ORIGIN')) in origins:
                ao = [('Access-Control-Allow-Origin', origin)]
            else:
                ao = []

            def respond_with_allow_origin(status, headers, exc_info=None):
                return respond(status, headers + ao, exc_info)

            if (env['REQUEST_METHOD'] == 'OPTIONS' and
                    env.get('HTTP_ACCESS_CONTROL_REQUEST_METHOD') is not None):
                respond_with_allow_origin(http_status(HTTPStatus.OK), achs)
                return []
            return fn(env, respond_with_allow_origin)
        return handle
    return decorator
