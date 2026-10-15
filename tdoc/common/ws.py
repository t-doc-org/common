# Copyright 2026 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import asyncio
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

    def respond(self, status, text=None):
        if text is None: text = status.description
        return super().respond(status, text)

    @functools.cached_property
    def _log_args(self):
        req = self.request
        return {
            'method': req.method,
            'uri': f'{self.scheme}://{req.headers.get('Host', '')}{req.path}',
            'origin': req.headers.get('Origin'),
        }


class Server(util.AsyncThread):
    def __init__(self, *, host=None, port=0, path=None, perms=0o600,
                 scheme='https', origins=util.no_match, local=False):
        self.host, self.port = host, port
        self.path, self.perms = path, perms
        self.scheme = scheme
        self.origins = re.compile(origins)
        self.local = local
        super().__init__(name='ws.Server')

    async def init(self):
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

    def start_serving(self):
        self.call(self._server.start_serving()).result()

    def process_request(self, conn, req):
        _log.info("%(method)s %(uri)s\norigin=%(origin)s", event='ws:start',
                  **conn._log_args)
        _log.info("Cookies: %(cookies)s", cookies=", ".join(conn.cookies))

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
