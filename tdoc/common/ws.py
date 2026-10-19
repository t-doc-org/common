# Copyright 2026 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import asyncio
from concurrent import futures
import contextlib
import contextvars
import functools
import json
import re
import secrets

from websockets import exceptions, frames, protocol
from websockets.asyncio import server

from . import context, http, logs, util, wsgi

_log = logs.logger(__name__)
_wlog = logs.logger('websockets')
_wlog.setLevel(logs.DISABLED)  # Disable websockets logging by default

globals().update((v.name, v) for v in frames.CloseCode)

req_id = contextvars.ContextVar('req_id')


def close_str(frame):
    if not (r := frame.reason):
        r = frames.CLOSE_CODE_EXPLANATIONS.get(frame.code, 'unknown')
    return f"{frame.code} {r}"


class Connection(server.ServerConnection):
    domain = user = None
    _read_db = _write_db = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._post = []
        self.local = self.server.thread.local
        self.scheme = self.server.thread.scheme
        self.dispatcher = self.server.thread.dispatcher

    @property
    def remote_addr(self):
        if (rah := self.server.thread.remote_addr_header) \
                and (hs := self.request.headers.get_all(rah)):
            return hs[0]
        if isinstance(ra := self.remote_address, tuple): return ra[0]
        return ra

    @property
    def required_origin(self):
        if not (v := self.request.headers.get_all('Origin')):
            raise http.Error(http.FORBIDDEN, "Missing Origin: header")
        return v[0] if not self.local else ''

    @property
    def token(self):
        t = http.cookie_token(self.request.headers.get('Cookie', ''))
        return t if t is not None else ''

    def post(self, fn): self._post.append(fn)

    def run_post(self):
        post = self._post
        while post: post.pop()()

    @property
    def read_db(self): return self._read_db()

    @property
    def write_db(self): return self._write_db()

    def respond(self, status, text=None, headers=()):
        if text is None: text = http.message(status)
        resp = super().respond(status, text)
        resp.headers.update(headers)
        return resp

    def blocking(self, fn):
        return self.loop.run_in_executor(None, fn)

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

    async def process_request(self, req):
        try:
            await self.dispatcher.run_pre_ws(self)
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
            if not rclose: rclose = frames.Close(ABNORMAL_ABNORMAL_CLOSURE, '')
            if not sclose: sclose = frames.Close(ABNORMAL_ABNORMAL_CLOSURE, '')
            if self.protocol.close_rcvd_then_sent:
                status = f'r:{close_str(rclose)}, s:{close_str(sclose)}'
            else:
                status = f's:{close_str(sclose)}, r:{close_str(rclose)}'
            _log.info("Connection closed: %(status)s", event="ws:end",
                      status=status, **self._log_args)
            self.run_post()

    async def handle_rpc(self, req):
        # TODO: Add metrics
        code, log_level = http.INTERNAL_SERVER_ERROR, logs.NOTSET
        cid, rid = self.id.hex, req_id.get()
        token = context.ctx.set('rpc:' + secrets.token_hex(8))
        try:
            if (path := req.pop('$P', None)) is None:
                raise http.Error(http.BAD_REQUEST)
            if (handler := self.dispatcher.handler_ws(path)) is None:
                raise http.Error(http.NOT_FOUND)
            log_level = getattr(handler, '_log_level', logs.NOTSET)
            if log_level != logs.NOTSET:
                lkw = self._log_rpc
                msg = "RPC start: %(path)s\n" \
                      "origin=%(origin)s remote=%(remote)s"
                if 'user' in lkw: msg += " user=0x%(user)016x"
                _log.log(log_level, msg, event='rpc:start', path=path, cid=cid,
                         rid=rid, **lkw)
            await handler(self, req)
            code = http.OK
        except http.Error as e:
            code = e.code
            await self.send_error(e.code, e.message)
        except exceptions.ConnectionClosedOK:
            code = http.OK
        except exceptions.ConnectionClosedError:
            code = http.INTERNAL_SERVER_ERROR
        except Exception:
            _log.exception("Uncaught exception", event='rpc:exception')
            code = http.INTERNAL_SERVER_ERROR
            await self.send_error(code)
        finally:
            if log_level != logs.NOTSET:
                _log.log(log_level, "RPC end: %(status)s", event='rpc:end',
                         status=f'{code} {code.phrase}', cid=cid, rid=rid,
                         **lkw)
            context.ctx.reset(token)

    def send(self, resp, final=False):
        resp['$I'] = req_id.get()
        if final: resp['$Z'] = 1
        return super().send(util.to_json(resp))

    def send_error(self, code, msg=''):
        resp = {'$E': code}
        if msg: resp['$M'] = msg
        return self.send(resp, final=True)

    @functools.cached_property
    def _log_args(self):
        req = self.request
        kwargs = {
            'method': req.method,
            'uri': f'{self.scheme}://{req.headers.get('Host', '')}{req.path}',
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


def endpoint(name, require_authn=False, log_level=logs.INFO):
    def decorator(fn):
        @functools.wraps(fn)
        async def dfn(self, /, conn, req):
            if require_authn and conn.user is None:
                return await conn.send_error('unauthorized')
            await conn.send(await fn(self, conn, req), final=True)
        dfn._endpoint = name
        dfn._endpoint_type = 'ws'
        dfn._log_level = log_level
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
        super().__init__(name='ws.Server')

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
        self.dispatcher = dispatcher
        self.call(self._server.start_serving()).result()
