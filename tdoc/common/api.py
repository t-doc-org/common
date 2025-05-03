# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import contextlib
import hashlib
from http import HTTPMethod, HTTPStatus
import pathlib
import queue
import secrets
import sqlite3
import sys
import threading
import time
from wsgiref import util

from . import wsgi


class ThreadLocal(threading.local):
    def __init__(self, **kwargs):
        super().__init__()
        self.__dict__.update(kwargs)


class Api:
    thread_local = ThreadLocal(db=None)

    def __init__(self, path):
        self.path = pathlib.Path(path).resolve() if path else None
        self.event = EventApi(self)
        self.endpoints = {
            'event': self.event,
            'log': self.handle_log,
        }

    def add_endpoint(self, name, handler):
        self.endpoints[name] = handler

    def connect(self, params, timeout=10, autocommit=False):
        return sqlite3.connect(f'{self.path.as_uri()}?{params}', uri=True,
                               timeout=timeout, autocommit=autocommit,
                               check_same_thread=True)

    @contextlib.contextmanager
    def transaction(self, env):
        if (db := self.thread_local.db) is None:
            self.thread_local.db = db = self.connect(
                'mode=rw', timeout=env.get('tdoc.db_timeout', 10))
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise

    def create_store(self, open_acl=False):
        db = self.connect('mode=rwc', autocommit=True)
        try:
            db.execute('pragma journal_mode=WAL')
            db.executescript("""
                create table meta (
                    key text primary key,
                    value any
                ) strict;
                insert into meta values ('version', 1);
                create table auth (
                    token text primary key,
                    perms text not null
                ) strict;
                create table log (
                    time int not null,
                    location text not null,
                    session text,
                    data text
                ) strict;
            """)
            if open_acl:
                db.execute("insert into auth (token, perms) values ('*', '*')")
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def check_acl(self, env, perm):
        token = ''
        if (auth := env.get('HTTP_AUTHORIZATION')) is not None:
            parts = auth.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                token = parts[1]
        with self.transaction(env) as db:
            for perms, in db.execute(
                    "select perms from auth where token in (?, '*')", (token,)):
                perms = perms.split(',')
                if perm in perms or '*' in perms: return
        raise wsgi.Error(HTTPStatus.UNAUTHORIZED)

    def __call__(self, env, respond):
        name = util.shift_path_info(env)
        if (handler := self.endpoints.get(name, None)) is None:
            return (yield from wsgi.error(respond, HTTPStatus.NOT_FOUND))
        try:
            yield from handler(env, respond)
        except wsgi.Error as e:
            return (yield from wsgi.error(respond, e.status, e.message,
                                          exc_info=sys.exc_info()))
        finally:
            if (db := self.thread_local.db) is not None \
                     and not env.get('tdoc.db_cache_per_thread'):
                self.thread_local.db = None
                db.close()

    def handle_log(self, env, respond):
        wsgi.method(env, HTTPMethod.POST)
        if env['PATH_INFO']: raise wsgi.Error(HTTPStatus.NOT_FOUND)
        self.check_acl(env, 'log')
        req = wsgi.read_json(env)
        with self.transaction(env) as db:
            db.execute("""
                insert into log (time, location, session, data)
                    values (?, ?, ?, json(?));
            """, (int(req.get('time', time.time_ns() // 1000000)),
                  req['location'], req.get('session'),
                  wsgi.to_json(req['data'])))
        return wsgi.respond_json(respond, {})


class EventApi:
    def __init__(self, api):
        self.api = api
        self.endpoints = {
            'sub': self.handle_sub,
            'watch': self.handle_watch,
        }
        self.lock = threading.Lock()
        self.observables = {}
        self.watchers = {}

    def __call__(self, env, respond):
        name = util.shift_path_info(env)
        if (handler := self.endpoints.get(name, None)) is None:
            raise wsgi.Error(HTTPStatus.NOT_FOUND)
        return handler(env, respond)

    def add_observable(self, obs):
        with self.lock: self.observables[obs.key] = obs

    def find_observable(self, req):
        key = Observable.hash(req)
        with self.lock:
            if (obs := self.observables.get(key)) is not None: return obs
            # TODO: Create dynamic observable
        raise Exception("Observable not found")

    @contextlib.contextmanager
    def watcher(self):
        with Watcher() as watcher:
            with self.lock:
                while True:
                    sid = secrets.token_urlsafe(20)
                    if sid not in self.watchers: break
                watcher.sid = sid
                self.watchers[sid] = watcher
            try:
                yield watcher
            finally:
                with self.lock: del self.watchers[sid]

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
            if failed := self.watch(watcher, req.get('add', [])):
                resp['failed'] = failed
            yield wsgi.to_json(resp).encode('utf-8') + b'\n'
            yield from watcher

    def handle_sub(self, env, respond):
        wsgi.method(env, HTTPMethod.POST)
        if env['PATH_INFO']: raise wsgi.Error(HTTPStatus.NOT_FOUND)
        req = wsgi.read_json(env)
        if (sid := req.get('sid', None)) is None:
            raise wsgi.Error(HTTPStatus.BAD_REQUEST, "Missing field 'sid'")
        with self.lock:
            if (watcher := self.watchers.get(sid)) is None:
                raise wsgi.Error(HTTPStatus.NOT_FOUND, "Unknown stream ID")
        resp = {}
        for wid in req.get('remove', []): watcher.unwatch(wid)
        if failed := self.watch(watcher, req.get('add', [])):
            resp['failed'] = failed
        return wsgi.respond_json(respond, resp)

    def watch(self, watcher, adds):
        failed = []
        for add in adds:
            if (wid := add.get('wid')) is None: continue
            try:
                watcher.watch(wid, self.find_observable(add['req']))
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
        self.lock = threading.Lock()
        self.watches = set()

    def send_initial_locked(self, watcher, wid): pass

    def send_locked(self, msg):
        for watcher, wid in self.watches: watcher.send(wid, msg)

    def watch(self, watcher, wid):
        key = (watcher, wid)
        with self.lock:
            if key in self.watches: return
            self.watches.add(key)
            self.send_initial_locked(watcher, wid)

    def unwatch(self, watcher, wid):
        with self.lock: self.watches.discard((watcher, wid))


class ValueObservable(Observable):
    def __init__(self, name, value):
        super().__init__({'name': name})
        self._value = value

    def set(self, value):
        with self.lock:
            if value == self._value: return
            self._value = value
            self.send_locked(self._msg())

    def send_initial_locked(self, watcher, wid):
        watcher.send(wid, self._msg())

    def _msg(self):
        return wsgi.to_json(self._value).encode('utf-8')
