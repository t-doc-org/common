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

# TODO: Replace thread-local connection with a connection pool; cache
#       per-request connection in env

missing = object()

def arg(data, name, validate=None):
    if (v := data.get(name, missing)) is missing:
        raise wsgi.Error(HTTPStatus.BAD_REQUEST, f"Missing argument '{name}'")
    if validate is not None and not validate(v):
        raise wsgi.Error(HTTPStatus.BAD_REQUEST, f"Invalid argument '{name}'")
    return v


class ThreadLocal(threading.local):
    def __init__(self, **kwargs):
        super().__init__()
        self.__dict__.update(kwargs)


class Store:
    def __init__(self, path, timeout=10, dev=False):
        self.path = pathlib.Path(path).resolve()
        self.timeout = timeout
        self.dev = dev
        # TODO: Check database version, as separate method

    def connect(self, params='mode=rw', autocommit=False):
        return sqlite3.connect(f'{self.path.as_uri()}?{params}', uri=True,
                               timeout=self.timeout, autocommit=autocommit,
                               check_same_thread=True)

    def meta(self, db, key, default=None):
        for value, in db.execute(
                "select value from meta where key = ?", (key,)):
            return value
        return default

    def create(self, version=None, dev=False):
        self._check_version(version)
        if self.path.exists():
            raise Exception("Store database already exists")
        # WAL cannot be enabled within a transaction, and autocommit=False
        # always has a transaction open. Create the database with
        # autocommit=True as a workaround.
        with contextlib.closing(
                self.connect('mode=rwc', autocommit=True)) as db:
            db.execute("pragma journal_mode=WAL")
        with contextlib.closing(self.connect()) as db:
            return self._upgrade(db, from_version=0, to_version=version,
                                 dev=dev)

    def upgrade(self, version=None):
        self._check_version(version)
        with contextlib.closing(self.connect()) as db:
            from_version = self.meta(db, 'version')
            to_version = self._upgrade(db, from_version=from_version,
                                       to_version=version,
                                       dev=self.meta(db, 'dev', 0))
            return from_version, to_version

    def _check_version(self, version):
        if version is None: return
        for v, _ in self.versions():
            if v == version: return
        raise Exception(f"Invalid store version: {version}")

    def _upgrade(self, db, from_version, to_version, dev):
        version = from_version
        for v, fn in self.versions(from_version + 1):
            if to_version is not None and v > to_version: break
            with db:
                fn(db, dev)
                db.execute("""
                    insert or replace into meta (key, value)
                        values ('version', ?)
                """, (v,))
            version = v
        return version

    def versions(self, version=1):
        while True:
            if (fn := getattr(self, f'version_{version}', None)) is None:
                return
            yield version, fn
            version += 1

    def version_1(self, db, dev):
        db.executescript("""
            create table meta (
                key text primary key,
                value any
            ) strict;
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
        db.execute("insert into meta values ('dev', ?)", (1 if dev else 0,))
        if dev:
            db.execute("insert into auth (token, perms) values ('*', '*')")

    def version_2(self, db, dev):
        db.executescript("""
            create table solutions (
                page text primary key,
                show text not null
            ) strict;
        """)


class Api:
    thread_local = ThreadLocal(db=None)

    def __init__(self, path, db_timeout=10):
        self.store = Store(path, timeout=db_timeout) if path else None
        self.event = EventApi(self)
        self.endpoints = {
            'event': self.event,
            'log': self.handle_log,
            'solutions': self.handle_solutions,
        }

    def add_endpoint(self, name, handler):
        self.endpoints[name] = handler

    @property
    def db(self):
        if self.store is None: raise Exception("No store available")
        if (db := self.thread_local.db) is None:
            db = self.thread_local.db = self.store.connect()
        return db

    def is_dev(self, env):
        return env.get('tdoc.dev', False)

    def origin(self, env):
        return env['HTTP_ORIGIN'] if not self.is_dev(env) else ''

    def check_same_origin(self, env, url):
        if not url.startswith(f'{self.origin(env)}/'):
            raise wsgi.Error(HTTPStatus.FORBIDDEN)

    def check_acl(self, env, perm):
        token = ''
        if (auth := env.get('HTTP_AUTHORIZATION')) is not None:
            parts = auth.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                token = parts[1]
        with self.db as db:
            for perms, in db.execute(
                    "select perms from auth where token in (?, '*')", (token,)):
                perms = perms.split(',')
                if perm in perms or '*' in perms: return
        raise wsgi.Error(HTTPStatus.UNAUTHORIZED)

    def __call__(self, env, respond):
        name = util.shift_path_info(env)
        if (handler := self.endpoints.get(name)) is None:
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
        with self.db as db:
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
        req = wsgi.read_json(env)
        with self.db as db:
            # TODO: Check ACL
            self.check_same_origin(env, page := arg(req, 'page'))
            show = arg(req, 'show', lambda v: v in ('show', 'remove'))
            db.execute("""
                insert or replace into solutions (page, show) values (?, ?)
            """, (page, show))
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
        self.observable_types = {
            'solutions': SolutionsObservable,
        }
        self.watchers = {}

    def __call__(self, env, respond):
        name = util.shift_path_info(env)
        if (handler := self.endpoints.get(name)) is None:
            raise wsgi.Error(HTTPStatus.NOT_FOUND)
        return handler(env, respond)

    def add_observable(self, obs):
        with self.lock: self.observables[obs.key] = obs

    def find_observable(self, req, env):
        key = Observable.hash(req)
        with self.lock:
            if (obs := self.observables.get(key)) is not None: return obs
            if (typ := self.observable_types.get(req['name'])) is not None:
                obs = typ(req, self, env)
                self.observables[obs.key] = obs
                return obs
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
            if failed := self.watch(watcher, req.get('add', []), env):
                resp['failed'] = failed
            yield wsgi.to_json(resp).encode('utf-8') + b'\n'
            yield from watcher

    def handle_sub(self, env, respond):
        wsgi.method(env, HTTPMethod.POST)
        if env['PATH_INFO']: raise wsgi.Error(HTTPStatus.NOT_FOUND)
        req = wsgi.read_json(env)
        sid = arg(req, 'sid')
        with self.lock:
            if (watcher := self.watchers.get(sid)) is None:
                raise wsgi.Error(HTTPStatus.NOT_FOUND, "Unknown stream ID")
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


class DbObservable(Observable):
    def __init__(self, req, events):
        super().__init__(req)
        self.events = events


class SolutionsObservable(DbObservable):
    def __init__(self, req, events, env):
        super().__init__(req, events)
        self._page = arg(req, 'page')
        self.events.api.check_same_origin(env, self._page)
        self._data = {'show': None}
        self._stop = False
        self._poller = threading.Thread(target=self.poll)
        self._poller.start()

    def _msg(self):
        return wsgi.to_json(self._data).encode('utf-8')

    def send_initial_locked(self, watcher, wid):
        watcher.send(wid, self._msg())

    def stop_locked(self):
        self._stop = True
        self.lock.notify()

    def poll(self):
        with contextlib.closing(self.events.api.store.connect()) as db:
            with self.lock: show = self._data['show']
            while True:
                with contextlib.suppress(Exception), db:
                    for show, in db.execute(
                            "select show from solutions where page = ?",
                            (self._page,)): pass
                with self.lock:
                    if show != self._data['show']:
                        self._data['show'] = show
                        self.send_locked(self._msg())
                    if self.lock.wait_for(lambda: self._stop, 1): break
