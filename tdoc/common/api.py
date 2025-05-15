# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import contextlib
import hashlib
from http import HTTPMethod, HTTPStatus
import json
import queue
import secrets
import sys
import threading
import time
import traceback
from wsgiref import util

from . import store, wsgi

# TODO: Degrade gracefully without a database

missing = object()


def arg(data, name, validate=None):
    if (v := data.get(name, missing)) is missing:
        raise wsgi.Error(HTTPStatus.BAD_REQUEST, f"Missing argument '{name}'")
    if validate is not None and not validate(v):
        raise wsgi.Error(HTTPStatus.BAD_REQUEST, f"Invalid argument '{name}'")
    return v


def check(cond, code=HTTPStatus.FORBIDDEN, msg=None):
    if not cond: raise wsgi.Error(code, msg)


class Api:
    def __init__(self, path, stderr=None, db_timeout=10):
        if stderr is None: stderr = sys.stderr
        self.stderr = stderr
        if path:
            self.store = store.Store(path, timeout=db_timeout)
            self.pool = store.ConnectionPool(self.store)
        else:
            self.store = None
        self.event = EventApi(self)
        self.endpoints = {
            'event': self.event,
            'log': self.handle_log,
            'solutions': self.handle_solutions,
            'user': self.handle_user,
        }

    def add_endpoint(self, name, handler):
        self.endpoints[name] = handler

    def print_exception(self, e=None):
        if e is None: e = sys.exception()
        traceback.print_exception(file=self.stderr)

    def db(self, env):
        if (db := env.get('tdoc.db')) is not None: return db
        if self.store is None:
            raise wsgi.Error(HTTPStatus.NOT_IMPLEMENTED, "No store available")
        db = env['tdoc.db'] = self.pool.get()
        return db

    def authenticate(self, env):
        user = None
        if token := wsgi.authorization(env):
            with self.db(env) as db:
                user, = db.row("""
                    select user from user_tokens
                    where token = ? and (expires is null or ? < expires)
                """, (token, time.time_ns()), default=(None,))
            if user is None: raise wsgi.Error(HTTPStatus.UNAUTHORIZED)
        env['tdoc.user'] = user

    def user(self, env, anon=True):
        user = env['tdoc.user']
        if user is None and not anon: raise wsgi.Error(HTTPStatus.UNAUTHORIZED)
        return user

    def member_of(self, env, db, group):
        origin = wsgi.origin(env)
        if (user := self.user(env)) is None: return False
        return bool(db.row(f"""
            select exists(
                select 1 from user_memberships
                where origin = ? and user = ? and (group_ = ? or group_ = '*')
            )
        """, (origin, user, group))[0])

    def check_acl(self, env, perm):
        token = wsgi.authorization(env)
        with self.db(env) as db:
            for perms, in db.execute(
                    "select perms from auth where token in (?, '*')", (token,)):
                perms = perms.split(',')
                if perm in perms or '*' in perms: return
        raise wsgi.Error(HTTPStatus.FORBIDDEN)

    def __call__(self, env, respond):
        name = util.shift_path_info(env)
        if (handler := self.endpoints.get(name)) is None:
            return (yield from wsgi.error(respond, HTTPStatus.NOT_FOUND))
        try:
            try:
                self.authenticate(env)
                yield from handler(env, respond)
            except wsgi.Error as e:
                return (yield from wsgi.error(respond, e.status, e.message,
                                              exc_info=sys.exc_info()))
        finally:
            if (db := env.get('tdoc.db')) is not None: self.pool.release(db)

    def handle_log(self, env, respond):
        wsgi.method(env, HTTPMethod.POST)
        if env['PATH_INFO']: raise wsgi.Error(HTTPStatus.NOT_FOUND)
        self.check_acl(env, 'log')
        req = wsgi.read_json(env)
        with self.db(env) as db:
            db.execute("""
                insert into log (time, location, session, data)
                    values (?, ?, ?, json(?))
            """, (int(req.get('time', time.time_ns() // 1000000)),
                  req['location'], req.get('session'),
                  wsgi.to_json(req['data'])))
        return wsgi.respond_json(respond, {})

    def handle_solutions(self, env, respond):
        wsgi.method(env, HTTPMethod.POST)
        if env['PATH_INFO']: raise wsgi.Error(HTTPStatus.NOT_FOUND)
        origin = wsgi.origin(env)
        req = wsgi.read_json(env)
        page = arg(req, 'page')
        show = arg(req, 'show', lambda v: v in ('show', 'hide'))
        with self.db(env) as db:
            check(self.member_of(env, db, 'solutions:write'))
            db.execute("""
                insert or replace into solutions (origin, page, show)
                    values (?, ?, ?)
            """, (origin, page, show))
        return wsgi.respond_json(respond, {})

    def handle_user(self, env, respond):
        wsgi.method(env, HTTPMethod.POST)
        if env['PATH_INFO']: raise wsgi.Error(HTTPStatus.NOT_FOUND)
        user = self.user(env, anon=False)
        origin = wsgi.origin(env)
        with self.db(env) as db:
            name, = db.row("select name from users where id = ?", (user,))
            groups = [g for g, in db.execute("""
                select group_ from user_memberships
                where origin = ? and user = ?
            """, (origin, user))]
        return wsgi.respond_json(
            respond, {'name': name, 'groups': groups})


class EventApi:
    def __init__(self, api):
        self.api = api
        self.endpoints = {
            'sub': self.handle_sub,
            'watch': self.handle_watch,
        }
        self.lock = threading.Lock()
        self.observables = {}
        self.dyn_observables = {
            'solutions': SolutionsObservable,
        }
        self.watchers = {}
        self._last_watcher = None

    def __call__(self, env, respond):
        name = util.shift_path_info(env)
        if (handler := self.endpoints.get(name)) is None:
            raise wsgi.Error(HTTPStatus.NOT_FOUND)
        return handler(env, respond)

    def add_observable(self, obs):
        with self.lock: self.observables[obs.key] = obs

    def remove_observable(self, obs):
        with self.lock: self.observables.pop(obs.key, None)

    def find_observable(self, req, env):
        key = Observable.hash(req)
        with self.lock:
            if (obs := self.observables.get(key)) is not None:
                if not obs.stopping: return obs
            if (typ := self.dyn_observables.get(req['name'])) is not None:
                obs = typ(req, self, env)
                self.observables[obs.key] = obs
                return obs
        raise Exception("Observable not found")

    @property
    def last_watcher(self):
        with self.lock: return self._last_watcher

    @contextlib.contextmanager
    def watcher(self):
        with Watcher() as watcher:
            sid = secrets.token_urlsafe(8)
            with self.lock:
                while sid in self.watchers:
                    sid = secrets.token_urlsafe(8)
                watcher.sid = sid
                self.watchers[sid] = watcher
                self._last_watcher = None
            try:
                yield watcher
            finally:
                with self.lock:
                    del self.watchers[sid]
                    if not self.watchers:
                        self._last_watcher = time.time_ns()

    def handle_watch(self, env, respond):
        wsgi.method(env, HTTPMethod.POST)
        if env['PATH_INFO']: raise wsgi.Error(HTTPStatus.NOT_FOUND)
        req = wsgi.read_json(env)
        with self.watcher() as watcher:
            respond(wsgi.http_status(HTTPStatus.OK), [
                ('Content-Type', 'text/plain; charset=utf-8'),
                ('Cache-Control', 'no-store'),
            ])
            resp = {'sid': watcher.sid}
            if failed := self.watch(watcher, req.get('add', []), env):
                resp['failed'] = failed
            yield wsgi.to_json(resp).encode('utf-8') + b'\n'
            yield from watcher

    def handle_sub(self, env, respond):
        wsgi.method(env, HTTPMethod.POST)
        if env['PATH_INFO']: raise wsgi.Error(HTTPStatus.NOT_FOUND)
        req = wsgi.read_json(env)
        sid = arg(req, 'sid')
        with self.lock: watcher = self.watchers.get(sid)
        if watcher is None:
            raise wsgi.Error(HTTPStatus.BAD_REQUEST, "Unknown stream ID")
        resp = {}
        for wid in req.get('remove', []): watcher.unwatch(wid)
        if failed := self.watch(watcher, req.get('add', []), env):
            resp['failed'] = failed
        return wsgi.respond_json(respond, resp)

    def watch(self, watcher, adds, env):
        failed = []
        for add in adds:
            if (wid := add.get('wid')) is None: continue
            try:
                watcher.watch(wid, self.find_observable(add['req'], env))
            except Exception:
                failed.append(wid)
        return failed


class Watcher:
    def __init__(self):
        self.queue = queue.SimpleQueue()
        self.lock = threading.Lock()
        self.watches = {}

    def send(self, wid, msg):
        self.queue.put((wid, msg))

    def __iter__(self):
        while True:
            try:
                wid, msg = self.queue.get(timeout=1)
                yield b'{"wid":%d,"data":' % wid
                yield msg
                yield b'}\n'
            except queue.Empty:
                yield b'\n'

    def __enter__(self): return self

    def __exit__(self, typ, value, tb):
        with self.lock:
            watches, self.watches = self.watches, {}
        for wid, obs in watches.items(): obs.unwatch(self, wid)

    def watch(self, wid, obs):
        with self.lock:
            if wid in self.watches: return
            self.watches[wid] = obs
        obs.watch(self, wid)

    def unwatch(self, wid):
        with self.lock: obs = self.watches.pop(wid, None)
        if obs is not None: obs.unwatch(self, wid)


class Observable:
    @staticmethod
    def hash(req):
        return hashlib.sha256(
            wsgi.to_json(req, sort_keys=True).encode('utf-8')).digest()

    def __init__(self, req):
        self.key = self.hash(req)
        self.lock = threading.Condition(threading.Lock())
        self.watches = set()

    def send_initial_locked(self, watcher, wid): pass

    stopping = False

    def stop_locked(self): pass

    def send_locked(self, msg):
        for watcher, wid in self.watches: watcher.send(wid, msg)

    def watch(self, watcher, wid):
        key = (watcher, wid)
        with self.lock:
            if key in self.watches: return
            self.watches.add(key)
            self.send_initial_locked(watcher, wid)

    def unwatch(self, watcher, wid):
        with self.lock:
            self.watches.discard((watcher, wid))
            if not self.watches: self.stop_locked()


class ValueObservable(Observable):
    def __init__(self, name, value):
        super().__init__({'name': name})
        self._value = value

    def set(self, value):
        with self.lock:
            if value == self._value: return
            self._value = value
            self.send_locked(self._msg())

    def _msg(self):
        return wsgi.to_json(self._value).encode('utf-8')

    def send_initial_locked(self, watcher, wid):
        watcher.send(wid, self._msg())


class DynObservable(Observable):
    def __init__(self, req, events):
        super().__init__(req)
        self.events = events

    def unwatch(self, watcher, wid):
        super().unwatch(watcher, wid)
        if self.stopping: self.remove()

    def remove(self):
        self.events.remove_observable(self)

    def print_exception(self, e=None):
        self.events.api.print_exception(e)


class DbObservable(DynObservable):
    def __init__(self, req, events, data, interval=1):
        super().__init__(req, events)
        self._data = data
        self._interval = interval
        self._stop = False
        self._poller = threading.Thread(target=self.poll)
        self._poller.start()

    def _msg(self):
        return wsgi.to_json(self._data).encode('utf-8')

    def send_initial_locked(self, watcher, wid):
        watcher.send(wid, self._msg())

    @property
    def stopping(self):
        with self.lock: return self._stop

    def stop_locked(self):
        self._stop = True
        self.lock.notify()

    def poll(self):
        try:
            with contextlib.closing(self.events.api.store.connect()) as db:
                while True:
                    error = False
                    try:
                        data = self.query(db)
                    except Exception:
                        error = True
                        self.print_exception()
                    with self.lock:
                        if not error and data != self._data:
                            self._data = data
                            self.send_locked(self._msg())
                        if self.lock.wait_for(lambda: self._stop,
                                              self._interval):
                            break
        except Exception:
            with self.lock: self._stop = True
            self.remove()
            self.print_exception()

    def query(self, db):
        raise NotImplementedError()


class SolutionsObservable(DbObservable):
    def __init__(self, req, events, env):
        self._origin = wsgi.origin(env)
        self._page = arg(req, 'page')
        super().__init__(req, events, {'show': None})

    def query(self, db):
        with db:
            show, = db.row("""
                select show from solutions where origin = ? and page = ?
            """, (self._origin, self._page), default=(None,))
        return {'show': show}
