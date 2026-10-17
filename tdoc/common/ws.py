# Copyright 2026 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import asyncio
from concurrent import futures
import contextlib
import functools
from http import cookies, HTTPStatus
import re

from websockets import exceptions, protocol
from websockets.asyncio import server

from . import context, logs, util, wsgi

_log = logs.logger(__name__)
_wlog = logs.logger('websockets')
_wlog.setLevel(logs.DISABLED)  # Disable websockets logging by default


class Connection(server.ServerConnection):
    domain = user = None
    _read_db = _write_db = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._post = []

    @property
    def local(self): return self.server.thread.local

    @property
    def scheme(self): return self.server.thread.scheme

    @property
    def origin(self):
        if (v := self.request.headers.get('Origin')) is None:
            raise wsgi.Error(HTTPStatus.FORBIDDEN, "Missing Origin: header")
        return v if not self.local else ''

    @property
    def cookies(self):
        return cookies.SimpleCookie(self.request.headers.get('Cookie', ''))

    @property
    def token(self):
        t = wsgi.cookie_token(self.request.headers.get('Cookie', ''))
        return t if t is not None else ''

    def post(self, fn): self._post.append(fn)

    def run_post(self):
        post = self._post
        while post: post.pop()()

    @property
    def read_db(self): return self._read_db()

    @property
    def write_db(self): return self._write_db()

    async def handshake(self, process_request, process_response, server_header):
        try:
            await super().handshake(process_request, process_response,
                                    server_header)
        finally:
            if self.protocol.state is not protocol.OPEN:
                resp = self.response
                _log.info("%(status)s", event="ws:end",
                          status=f'{resp.status_code} {resp.reason_phrase}',
                          **self._log_args)
                self.run_post()

    def respond(self, status, text=None):
        if text is None: text = status.description
        return super().respond(status, text)

    @functools.cached_property
    def _log_args(self):
        req = self.request
        kwargs = {
            'method': req.method,
            'uri': f'{self.scheme}://{req.headers.get('Host', '')}{req.path}',
            'origin': req.headers.get('Origin'),
        }
        if (v := self.user) is not None: kwargs['user'] = v
        return kwargs

    def blocking(self, fn):
        return self.loop.run_in_executor(None, fn)


class Server(util.AsyncThread):
    def __init__(self, *, host=None, port=0, path=None, perms=0o600,
                 scheme='https', origins=util.no_match, threads=None,
                 local=False):
        self.host, self.port = host, port
        self.path, self.perms = path, perms
        self.scheme = scheme
        self.origins = re.compile(origins)
        self.threads = threads
        self.local = local
        super().__init__(name='ws.Server')

    async def init(self):
        self.loop.set_default_executor(
            futures.ThreadPoolExecutor(max_workers=self.threads,
                                       thread_name_prefix='websocket'))
        addr = dict(path=self.path, unix=True) if self.path is not None \
               else dict(host=self.host, port=self.port)
        if self.path is not None: self.path.unlink(missing_ok=True)
        self._server = await server.serve(
            handler=self.handle_connection, start_serving=False,
            create_connection=Connection, origins=[self.origins],
            process_request=self.process_request, server_header=None, **addr)
        self._server.thread = self
        async def handler(connection):
            token = context.ctx.set(f'wsc:{connection.id.hex}')
            try:
                return await orig_handler(connection)
            finally:
                context.ctx.reset(token)
        orig_handler, self._server.handler = self._server.handler, handler
        if self.path is not None:
            self.path.chmod(self.perms)
        elif self.port == 0 and len(socks := self._server.server.sockets) == 1:
            self.port = socks[0].getsockname()[1]

    async def async_run(self):
        with contextlib.suppress(asyncio.CancelledError):
            await self._server.serve_forever()

    def start_serving(self, dispatcher):
        self.dispatcher = dispatcher
        self.call(self._server.start_serving()).result()

    async def process_request(self, conn, req):
        try:
            await self.dispatcher.run_pre_ws(conn)
            log_args = conn._log_args
            msg = "%(method)s %(uri)s\norigin=%(origin)s"
            if 'user' in log_args: msg += " user=0x%(user)016x"
            _log.info(msg, event='ws:start', **log_args)
        except wsgi.Error as e:
            return conn.respond(e.status, e.message)
        except Exception as e:
            _log.exception("Uncaught exception", event='ws:exception',
                           **conn._log_args)
            return conn.respond(HTTPStatus.INTERNAL_SERVER_ERROR)

    async def handle_connection(self, conn):
        try:
            with contextlib.suppress(exceptions.ConnectionClosedOK):
                while True:
                    data = await conn.recv()
                    _log.debug("data=%(data)r", data=data)
                    await conn.send(data)
        except Exception as e:
            _log.exception("Uncaught exception", event='ws:exception',
                           **conn._log_args)
        finally:
            _log.info("Connection closed", event="ws:end", **conn._log_args)
            conn.run_post()
