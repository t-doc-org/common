# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import contextlib
import datetime
import hashlib
from http import HTTPMethod, HTTPStatus
import json
import pathlib
import queue
import secrets
import sqlite3
import sys
import threading
import time
import traceback
from wsgiref import util

from . import wsgi

# TODO: Replace thread-local connection with a connection pool; cache
#       per-request connection in env
# TODO: Degrade gracefully without a database

missing = object()


class ThreadLocal(threading.local):
    def __init__(self, **kwargs):
        super().__init__()
        self.__dict__.update(kwargs)


def fetch_row(db, sql, params=(), default=None):
    for row in db.execute(sql, params): return row
    return default


class Store:
    def __init__(self, path, timeout=10):
        self.path = pathlib.Path(path).resolve()
        self.timeout = timeout
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

    def dev(self, db):
        return bool(self.meta(db, 'dev', 0))

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
                                       to_version=version, dev=self.dev(db))
            return from_version, to_version

    def _check_version(self, version):
        if version is None: return
        for v, _ in self.versions():
            if v == version: return
        raise Exception(f"Invalid store version: {version}")

    def _upgrade(self, db, from_version, to_version, dev):
        now = time.time_ns()
        version = from_version
        for v, fn in self.versions(from_version + 1):
            if to_version is not None and v > to_version: break
            with db:
                fn(db, dev, now)
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

    def tokens(self, db, origin, expired=False):
        if not origin and not self.dev(db):
            raise Exception("No origin specified")
        now = time.time_ns()
        for token, user, created, expires in db.execute("""
                    select token, user, created, expires from user_tokens
                    where origin = ? and (? or expires is null or ? < expires)
                """, (origin, expired, now)):
            created = datetime.datetime.fromtimestamp(created / 1e9)
            if expires is not None:
                expires = datetime.datetime.fromtimestamp(expires / 1e9)
            yield user, token, created, expires

    def create_tokens(self, db, origin, users, expires=None):
        if not origin and not self.dev(db):
            raise Exception("No origin specified")
        now = time.time_ns()
        if expires: expires = int(expires.timestamp() * 1e9)
        tokens = [secrets.token_urlsafe() for _ in users]
        with db:
            db.executemany("""
                insert into user_tokens (origin, token, user, created, expires)
                    values (?, ?, ?, ?, ?)
            """, [(origin, token, user, now, expires)
                  for user, token in zip(users, tokens)])
        return tokens

    def expire_tokens(self, db, origin, tokens, expires=None):
        if not origin and not self.dev(db):
            raise Exception("No origin specified")
        expires = int(expires.timestamp() * 1e9) if expires else time.time_ns()
        with db:
            db.executemany("""
                update user_tokens set expires = ?
                where origin = ? and (token = ? or user = ?)
            """, [(expires, origin, token, token) for token in tokens])

    def version_1(self, db, dev, now):
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
        if not dev: return
        db.execute("insert into auth (token, perms) values ('*', '*')")

    def version_2(self, db, dev, now):
        db.executescript("""
            create table user_tokens (
                origin text not null,
                token text not null,
                user text not null,
                created integer not null,
                expires integer,
                primary key (origin, token)
            ) strict;
            create table group_memberships (
                origin text not null,
                member text not null,
                group_ text not null,
                transitive integer not null,
                primary key (origin, member, group_)
            ) strict;
            create table solutions (
                origin text not null,
                page text not null,
                show text not null,
                primary key (origin, page)
            ) strict;
        """)
        if not dev: return
        db.execute("""
            insert into user_tokens (origin, token, user, created)
                values ('', 'admin', 'admin', ?)
        """, (now,))
        db.execute("""
            insert into group_memberships (origin, member, group_, transitive)
                values ('', 'admin', '*', 0)
        """)


def arg(data, name, validate=None):
    if (v := data.get(name, missing)) is missing:
        raise wsgi.Error(HTTPStatus.BAD_REQUEST, f"Missing argument '{name}'")
    if validate is not None and not validate(v):
        raise wsgi.Error(HTTPStatus.BAD_REQUEST, f"Invalid argument '{name}'")
    return v


def check(cond, code=HTTPStatus.FORBIDDEN, msg=None):
    if not cond: raise wsgi.Error(code, msg)


class Api:
    thread_local = ThreadLocal(db=None)

    def __init__(self, path, stderr=None, db_timeout=10):
        if stderr is None: stderr = sys.stderr
        self.stderr = stderr
        self.store = Store(path, timeout=db_timeout) if path else None
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

    @property
    def db(self):
        if self.store is None:
            raise wsgi.Error(HTTPStatus.NOT_IMPLEMENTED, "No store available")
        if (db := self.thread_local.db) is None:
            db = self.thread_local.db = self.store.connect()
        return db

    def authenticate(self, env):
        user = None
        if token := wsgi.authorization(env):
            origin = wsgi.origin(env)
            with self.db as db:
                user, = fetch_row(db, """
                    select user from user_tokens
                    where origin = ? and token = ?
                      and (expires is null or ? < expires)
                """, (origin, token, time.time_ns()), default=(None,))
            if user is None: raise wsgi.Error(HTTPStatus.UNAUTHORIZED)
        env['tdoc.user'] = user

    def user(self, env, anon=True):
        user = env['tdoc.user']
        if user is None and not anon: raise wsgi.Error(HTTPStatus.UNAUTHORIZED)
        return user

    def groups(self, env, db):
        if (groups := env.get('tdoc.user.groups', missing)) is missing:
            groups = set()
            if (user := self.user(env)) is not None:
                origin = wsgi.origin(env)
                groups.update(g for g, in db.execute("""
                        select group_ from group_memberships
                        where origin = ? and member = ?
                """, (origin, user)))
            env['tdoc.user.groups'] = groups
        return groups

    def member_of(self, env, db, group):
        origin = wsgi.origin(env)
        if (user := self.user(env)) is None: return False
        return bool(fetch_row(db, f"""
            select exists(
                select 1 from group_memberships
                where origin = ? and member = ?
                  and (group_ = ? or group_ = '*')
            )
        """, (origin, user, group))[0])

    def check_acl(self, env, perm):
        token = wsgi.authorization(env)
        with self.db as db:
            for perms, in db.execute(
                    "select perms from auth where token in (?, '*')", (token,)):
                perms = perms.split(',')
                if perm in perms or '*' in perms: return
        raise wsgi.Error(HTTPStatus.FORBIDDEN)

    def __call__(self, env, respond):
        name = util.shift_path_info(env)
        if (handler := self.endpoints.get(name)) is None:
            return (yield from wsgi.error(respond, HTTPStatus.NOT_FOUND))
        self.authenticate(env)
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
        origin = wsgi.origin(env)
        req = wsgi.read_json(env)
        page = arg(req, 'page')
        show = arg(req, 'show', lambda v: v in ('show', 'hide'))
        with self.db as db:
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
        with self.db as db: groups = self.groups(env, db)
        return wsgi.respond_json(
            respond, {'name': user, 'groups': sorted(groups)})


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

    @contextlib.contextmanager
    def watcher(self):
        with Watcher() as watcher:
            sid = secrets.token_urlsafe(8)
            with self.lock:
                while sid in self.watchers:
                    sid = secrets.token_urlsafe(8)
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
            show, = fetch_row(db, """
                select show from solutions where origin = ? and page = ?
            """, (self._origin, self._page), default=(None,))
        return {'show': show}
