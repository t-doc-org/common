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
