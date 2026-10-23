# Copyright 2026 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import asyncio
from collections import abc
from concurrent import futures
import contextlib
import contextvars
import functools
import json
import re
import secrets

import prometheus_client as pc
from websockets import exceptions, frames, protocol
from websockets.asyncio import server

from . import context, http, logs, util, wsgi

_log = logs.logger(__name__)
_wlog = logs.logger('websockets')
_wlog.setLevel(logs.DISABLED)  # Disable websockets logging by default

globals().update((v.name, v) for v in frames.CloseCode)

req_id = contextvars.ContextVar('req_id')

websocket_active_connections = pc.Gauge(
    subsystem='websocket', name='active_connections',
    documentation="The number of active websocket connections.")


def close_str(frame):
    if not (r := frame.reason):
        r = frames.CLOSE_CODE_EXPLANATIONS.get(frame.code, 'unknown')
    return f"{frame.code} {r}"


class Connection(http.Context, server.ServerConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        th = self.server.thread
        self.local = th.local
        self.scheme = th.scheme
        self.__handler = th.handler
        self.__disconnected = []

    def header(self, name, default=None):
        return self.request.headers.get(name, default)

    server_host = None
    server_origin = property(lambda self: f'{self.scheme}://{self.server_host}')

    @property
    def remote_addr(self):
        if (rah := self.server.thread.remote_addr_header) \
                and (hs := self.request.headers.get_all(rah)):
            return hs[0]
        if isinstance(ra := self.remote_address, tuple): return ra[0]
        return ra

    def disconnected(self, fn): self.__disconnected.append(fn)

    def run_disconnected(self):
        disconnected = self.__disconnected
        while disconnected: disconnected.pop()()

    def respond(self, status, text=None, headers=()):
        if text is None: text = http.message(status)
        resp = super().respond(status, text)
        resp.headers.update(headers)
        return resp

    def blocking(self, fn, *args):
        return self.loop.run_in_executor(None, fn, *args)

    async def handshake(self, process_request, process_response, server_header):
        try:
            await super().handshake(process_request, process_response,
                                    server_header)
        finally:
            if self.protocol.state is not protocol.OPEN:
                resp = self.response
                _log.info("%(code)s %(phrase)s", event="ws:end",
                          code=int(resp.status_code), phrase=resp.reason_phrase,
                          **self._log_args)
                self.run_disconnected()

    async def process_request(self, req):
        try:
            await self.__handler.run_connected(self)
            self.server_host = req.headers['Host']
            websocket_active_connections.inc()
            self.disconnected(websocket_active_connections.dec)
            log_args = self._log_args
            msg = "%(method)s %(uri)s\norigin=%(origin)s remote=%(remote)s"
            if 'user' in log_args: msg += " user=0x%(user)016x"
            _log.info(msg, event='ws:start', **log_args)
        except http.Error as e:
            return self.respond(e.status, e.message, e.headers)
        except Exception as e:
            _log.exception("Uncaught exception", event='ws:exception',
                           **self._log_args)
            return self.respond(http.INTERNAL_SERVER_ERROR)

    def process_response(self, req, resp):
        if resp.status_code == http.SWITCHING_PROTOCOLS \
                and (hs := self.response_headers):
            for k, v in hs: resp.headers[k] = v

    async def handle_connection(self):
        close_code = NORMAL_CLOSURE
        try:
            async with asyncio.TaskGroup() as workers:
                # TODO: Don't abort workers when exiting block due to exception
                async for data in self:
                    try:
                        req = json.loads(data)
                        rid = req.pop('$I')
                        # TODO: Implement streaming RPCs
                        if req.pop('$A', None) is None: continue
                        if req.pop('$Z', None) is None: continue
                    except Exception:
                        continue
                    token = req_id.set(rid)
                    try:
                        workers.create_task(self.handle_rpc(req))
                    finally:
                        req_id.reset(token)
        except exceptions.ConnectionClosed as e:
            pass
        except Exception as e:
            close_code = INTERNAL_ERROR
            _log.exception("Uncaught exception", event='ws:exception',
                           **self._log_args)
        finally:
            await self.close(close_code)
            rclose, sclose = self.protocol.close_rcvd, self.protocol.close_sent
            if rclose is None: rclose = frames.Close(ABNORMAL_CLOSURE, '')
            if sclose is None: sclose = frames.Close(ABNORMAL_CLOSURE, '')
            ok = rclose.code in frames.OK_CLOSE_CODES \
                 and sclose.code in frames.OK_CLOSE_CODES
            if self.protocol.close_rcvd_then_sent:
                closure = f'r:{close_str(rclose)}, s:{close_str(sclose)}'
            else:
                closure = f's:{close_str(sclose)}, r:{close_str(rclose)}'
            _log.info("Disconnected: %(status)s (%(closure)s)",
                      event="ws:end", status='OK' if ok else 'ERROR',
                      closure=closure, **self._log_args)
            self.run_disconnected()

    async def handle_rpc(self, req):
        # TODO: Add metrics
        code, log_level = http.INTERNAL_SERVER_ERROR, logs.NOTSET
        cid, rid = self.id.hex, req_id.get()
        token = context.ctx.set('rpc:' + secrets.token_hex(8))
        try:
            if (path := req.pop('$P', None)) is None:
                raise http.Error(http.BAD_REQUEST)
            if (endpoint := self.__handler.endpoints.get(path)) is None:
                raise http.Error(http.NOT_FOUND)
            log_level = getattr(endpoint, '_log_level', logs.NOTSET)
            if log_level != logs.NOTSET:
                lkw = self._log_rpc
                msg = "RPC %(path)s\norigin=%(origin)s remote=%(remote)s"
                if 'user' in lkw: msg += " user=0x%(user)016x"
                _log.log(log_level, msg, event='rpc:start', path=path, cid=cid,
                         rid=rid, **lkw)
            await endpoint(self, req)
            code = http.OK
        except http.Error as e:
            if e.headers:
                _log.warning("Ignored headers in RPC error: %(headers)s",
                             str(e.headers))
            code = e.code
            await self.send_error(e.code, e.message)
        except exceptions.ConnectionClosedOK:
            code = http.SERVICE_UNAVAILABLE
        except exceptions.ConnectionClosedError:
            code = http.SERVICE_UNAVAILABLE
        except Exception:
            _log.exception("Uncaught exception", event='rpc:exception')
            code = http.INTERNAL_SERVER_ERROR
            await self.send_error(code)
        finally:
            if log_level != logs.NOTSET:
                _log.log(log_level, "%(code)s %(phrase)s", event='rpc:end',
                         code=int(code), phrase=code.phrase, cid=cid, rid=rid,
                         **lkw)
            context.ctx.reset(token)

    def send(self, resp, final=False):
        resp['$I'] = req_id.get()
        if final: resp['$Z'] = 1
        return super().send(util.to_json(resp))

    def send_error(self, code, msg=''):
        resp = {'$E': code}
        if msg: resp['$M'] = msg
        return self.send(resp)

    @functools.cached_property
    def _log_args(self):
        req = self.request
        kwargs = {
            'method': req.method,
            'uri': f'{self.server_origin}{req.path}',
            'origin': req.headers.get('Origin'), 'remote': self.remote_addr,
        }
        if (v := self.user) is not None: kwargs['user'] = v
        return kwargs

    @functools.cached_property
    def _log_rpc(self):
        req = self.request
        kwargs = {
            'origin': req.headers.get('Origin'), 'remote': self.remote_addr,
        }
        if (v := self.user) is not None: kwargs['user'] = v
        return kwargs


class Handler(http.Handler, type='ws'):
    def __init__(self):
        super().__init__()
        self._connected = []

    def connected(self, fn): self._connected.append(fn)

    async def run_connected(self, conn):
        for fn in self._connected:
            if isinstance(res := fn(conn), abc.Awaitable): await res


def endpoint(name, require_authn=False, log_level=logs.INFO):
    def decorator(fn):
        @functools.wraps(fn)
        async def dfn(self, /, ctx, req):
            if require_authn and ctx.user is None:
                raise http.Error(http.UNAUTHORIZED)
            await ctx.send(await fn(self, ctx, req), final=True)
        dfn._endpoint = name
        dfn._endpoint_type = 'ws'
        dfn._log_level = log_level
        return dfn

    if getattr(name, '_endpoint_type', None) == 'wsgi':
        fn = name._fn
        require_authn = name._require_authn
        log_level = name._log_level
        name = name._endpoint
        @decorator
        @functools.wraps(fn)
        def dfn(self, /, ctx, req):
            return ctx.blocking(fn, self, ctx, req)
        return dfn
    return decorator


class Server(util.AsyncThread):
    def __init__(self, *, host=None, port=0, path=None, perms=0o600,
                 scheme='https', origins=util.no_match,
                 remote_addr_header=None, threads=None, local=False):
        self.host, self.port = host, port
        self.path, self.perms = path, perms
        self.scheme = scheme
        self.origins = re.compile(origins)
        self.remote_addr_header = remote_addr_header
        self.threads = threads
        self.local = local
        super().__init__(name='ws.Server', stop_on_exit=True)

    async def init(self):
        self.loop.set_default_executor(
            futures.ThreadPoolExecutor(max_workers=self.threads,
                                       thread_name_prefix='websocket'))
        addr = dict(path=self.path, unix=True) if self.path is not None \
               else dict(host=self.host, port=self.port)
        if self.path is not None: self.path.unlink(missing_ok=True)
        self._server = await server.serve(
            handler=lambda conn: conn.handle_connection(), start_serving=False,
            create_connection=Connection, origins=[self.origins],
            process_request=lambda conn, req: conn.process_request(req),
            process_response=
                lambda conn, req, resp: conn.process_response(req, resp),
            server_header=None, **addr)
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
        self.handler = dispatcher['ws']
        self.call(self._server.start_serving()).result()
