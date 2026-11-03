# Copyright 2026 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import asyncio
from collections import abc
from concurrent import futures
import contextlib
import enum
import functools
import json
import re
import secrets
import time

import prometheus_client as pc
from websockets import exceptions, frames, protocol
from websockets.asyncio import server

from . import context, http, logs, util, wsgi

_log = logs.logger(__name__)
_wlog = logs.logger('websockets')
_wlog.setLevel(logs.DISABLED)  # Disable websockets logging by default

globals().update((v.name, v) for v in frames.CloseCode)

websocket_active_connections = pc.Gauge(
    subsystem='websocket', name='active_connections',
    documentation="The number of active websocket connections.")
websocket_rpc_duration = pc.Histogram(
    subsystem='websocket', name='rpc_duration', unit='seconds',
    labelnames=('endpoint', 'status'),
    buckets=[0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5,
             1.0, 2.0, 5.0, 10.0],
    documentation="The duration of websocket RPCs.")
websocket_active_rpcs = pc.Gauge(
    subsystem='websocket', name='active_rpcs',
    labelnames=('endpoint',),
    documentation="The number of active websocket RPCs.")


class Code(enum.IntEnum):
    OK = 0
    CANCELLED = 1
    UNKNOWN = 2
    INVALID_ARGUMENT = 3
    DEADLINE_EXCEEDED = 4
    NOT_FOUND = 5
    ALREADY_EXISTS = 6
    PERMISSION_DENIED = 7
    RESOURCE_EXHAUSTED = 8
    FAILED_PRECONDITION = 9
    ABORTED = 10
    OUT_OF_RANGE = 11
    UNIMPLEMENTED = 12
    INTERNAL = 13
    UNAVAILABLE = 14
    DATA_LOSS = 15
    UNAUTHENTICATED = 16

    @staticmethod
    def from_http(code):
        if (v := _http_to_rpc.get(code)) is not None: return v
        if code.is_success: return Code.OK
        if code.is_server_error: return Code.INTERNAL
        return Code.UNKNOWN

_http_to_rpc = {
    http.OK: Code.OK,
    # Client errors
    http.BAD_REQUEST: Code.INVALID_ARGUMENT,
    http.UNAUTHORIZED: Code.UNAUTHENTICATED,
    http.FORBIDDEN: Code.PERMISSION_DENIED,
    http.NOT_FOUND: Code.NOT_FOUND,
    http.REQUEST_TIMEOUT: Code.DEADLINE_EXCEEDED,
    http.TOO_MANY_REQUESTS: Code.RESOURCE_EXHAUSTED,
    # Server errors
    http.NOT_IMPLEMENTED: Code.UNIMPLEMENTED,
    http.SERVICE_UNAVAILABLE: Code.UNAVAILABLE,
    http.GATEWAY_TIMEOUT: Code.DEADLINE_EXCEEDED,
    http.INSUFFICIENT_STORAGE: Code.RESOURCE_EXHAUSTED,
}

globals().update((v.name, v) for v in Code)


class Error(Exception):
    def __init__(self, code=Code.INTERNAL, message=None):
        try: code = Code(code)
        except ValueError: code = Code.UNKNOWN
        super().__init__(code, message)

    @property
    def code(self): return self.args[0]

    @property
    def message(self): return self.args[1]

    def __str__(self):
        c, m = self.args
        return f"{c.name}: {m}" if m else c.name


def close_str(frame):
    if not (r := frame.reason):
        r = frames.CLOSE_CODE_EXPLANATIONS.get(frame.code, 'unknown')
    return f"{frame.code} {r}"


class Rpc:
    queue_size = 16

    def __init__(self, conn, rid, req):
        self.conn, self.rid = conn, rid
        self.path = req.pop('$P', None)
        self.queue = asyncio.Queue(self.queue_size)
        self.queue.put_nowait(req)
        self.receive_closed = req.pop('$Z', None) is not None
        if self.receive_closed: self.queue.shutdown()
        self.send_closed = self.cancelled = False

    def __getattr__(self, name): return getattr(self.conn, name)

    def cancel(self, code, msg=None):
        if self.cancelled: return False
        self.receive_closed = self.send_closed = self.cancelled = True
        self.queue.shutdown(True)
        self.task.cancel(f'{code} {msg}' if msg else str(code))
        return True

    @functools.cached_property
    async def reqs(self):
        with contextlib.suppress(asyncio.QueueShutDown):
            while True: yield await self.queue.get()

    async def received(self, req):
        if (code := req.get('$E')) is not None:
            self.cancel(code, req.get('$M'))
            return
        if self.receive_closed: return
        if (last := req.pop('$Z', None)) is None:
            await self.queue.put(req)
            return
        self.receive_closed = True
        if last != 0: await self.queue.put(req)
        self.queue.shutdown()

    async def send(self, resp, final=False):
        if self.send_closed: raise Error(Code.INTERNAL)
        resp['$I'] = self.rid
        if final: resp['$Z'] = 1
        await self.conn.send(resp)
        if final: self.send_closed = True

    async def close_send(self):
        if self.send_closed: return
        self.send_closed = True
        await self.conn.send({'$I': self.rid, '$Z': 0})

    def abort(self, code, msg=None):
        if not self.cancel(code, msg): return
        resp = {'$I': self.rid, '$E': code}
        if msg: resp['$M'] = msg
        @self.conn.workers.run
        async def sender():
            try: await self.conn.send(resp)
            except Exception: pass


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
            return self.respond(e.code, e.message, e.headers)
        except Exception as e:
            _log.exception("Uncaught exception", event='ws:exception',
                           **self._log_args)
            return self.respond(http.INTERNAL_SERVER_ERROR)

    def process_response(self, req, resp):
        if resp.status_code == http.SWITCHING_PROTOCOLS \
                and (hs := self.response_headers):
            for k, v in hs: resp.headers[k] = v

    async def handle_connection(self):
        self.__rpcs = {}
        close_code = NORMAL_CLOSURE
        try:
            async with util.TaskGroup() as workers:
                self.workers = workers
                while True:
                    data = await self.recv()
                    try:
                        req = json.loads(data)
                        if (rid := req.pop('$I', None)) is None: continue
                    except Exception:
                        continue
                    if req.pop('$A', None) is None:
                        if (rpc := self.__rpcs.get(rid)) is not None:
                            await rpc.received(req)
                        continue
                    if (rpc := self.__rpcs.get(rid)) is not None:
                        rpc.abort(http.BAD_REQUEST)
                        continue
                    # TODO: Limit the number of in-progress RPCs
                    rpc = Rpc(self, rid, req)
                    rpc.task = workers.create_task(self.handle_rpc(rpc))
                    self.__rpcs[rid] = rpc
        except* exceptions.ConnectionClosed:
            pass
        except* Exception:
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

    async def handle_rpc(self, rpc):
        code, message, path = Code.INTERNAL, None, None
        start, active = time.monotonic(), None
        cid, log_level = self.id.hex, logs.NOTSET
        token = context.ctx.set('rpc:' + secrets.token_hex(8))
        try:
            # Find the endpoint
            if (path := rpc.path) is None: raise Error(Code.INVALID_ARGUMENT)
            if (endpoint := self.__handler.endpoints.get(path)) is None:
                raise Error(Code.NOT_FOUND)

            # Record the active RPC in metrics.
            (active := websocket_active_rpcs.labels(path)).inc()

            # Log the start of the RPC.
            log_level = getattr(endpoint, '_log_level', logs.NOTSET)
            if log_level != logs.NOTSET:
                lkw = self._log_rpc
                msg = "RPC %(path)s\norigin=%(origin)s remote=%(remote)s"
                if 'user' in lkw: msg += " user=0x%(user)016x"
                _log.log(log_level, msg, event='rpc:start', path=path, cid=cid,
                         rid=rpc.rid, **lkw)

            # Run the endpoint.
            await endpoint(rpc)
            await rpc.close_send()
            code = Code.OK
        except exceptions.ConnectionClosed:
            code, message = Code.UNAVAILABLE, "Connection closed"
            rpc.cancel(code, message)
        except Error as e:
            code, message = e.code, e.message
            rpc.abort(code, message)
        except Exception:
            _log.exception("Uncaught exception", event='rpc:exception')
            code, message = Code.INTERNAL, "Uncaught exception"
            rpc.abort(code, message)
        except asyncio.CancelledError as e:
            code, message = Code.CANCELLED, str(e)
            rpc.abort(code)  # Don't send internal message to client
            raise
        finally:
            del self.__rpcs[rpc.rid]
            if log_level != logs.NOTSET:
                if not message:
                    message = "Completed" if code == Code.OK else "Failed"
                _log.log(log_level, "%(code)s: %(message)s", event='rpc:end',
                         code=code.name, message=message or "", cid=cid,
                         rid=rpc.rid, **lkw)
            if active is not None: active.dec()
            if path is not None:
                websocket_rpc_duration.labels(path, str(code)) \
                    .observe(time.monotonic() - start)
            context.ctx.reset(token)

    def send(self, resp):
        return super().send(util.to_json(resp))

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


def stream_endpoint(name, require_authn=False, log_level=logs.INFO):
    def decorator(fn):
        @functools.wraps(fn)
        async def dfn(self, /, rpc):
            if require_authn and rpc.conn.user is None:
                raise http.Error(http.UNAUTHORIZED)
            await fn(self, rpc)
        dfn._endpoint = name
        dfn._endpoint_type = 'ws'
        dfn._log_level = log_level
        return dfn
    return decorator


def endpoint(name, require_authn=False, log_level=logs.INFO):
    def decorator(fn):
        @stream_endpoint(name, require_authn=require_authn, log_level=log_level)
        @functools.wraps(fn)
        async def dfn(self, /, rpc):
            req = await anext(rpc.reqs)
            # TODO: Don't propagate ExceptionGroup out of dfn
            async with util.TaskGroup() as workers:
                @workers.run
                async def receiver():
                    # We expect not further requests.
                    async for _ in rpc.reqs:
                        raise http.Error(http.INTERNAL_SERVER_ERROR)
                await rpc.send(await fn(self, rpc, req), final=True)
        return dfn

    if getattr(name, '_endpoint_type', None) == 'wsgi':
        fn = name._fn
        require_authn = name._require_authn
        log_level = name._log_level
        name = name._endpoint
        @decorator
        @functools.wraps(fn)
        async def dfn(self, /, ctx, req):
            try:
                return await ctx.blocking(fn, self, ctx, req)
            except http.Error as e:
                raise RpcError(Code.from_http(e.code), e.message) from e
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
