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

# TODO: Move Store to a separate module
# TODO: Replace thread-local connection with a connection pool; cache
#       per-request connection in env
# TODO: Degrade gracefully without a database

missing = object()


class ThreadLocal(threading.local):
    def __init__(self, **kwargs):
        super().__init__()
        self.__dict__.update(kwargs)


def to_datetime(nsec):
    if nsec is None: return
    return datetime.datetime.fromtimestamp(nsec / 1e9)


def to_nsec(dt, default=None):
    if dt is None: return default
    return int(dt.timestamp() * 1e9)


def fetch_row(db, sql, params=(), default=None):
    for row in db.execute(sql, params): return row
    return default


class Store:
    def __init__(self, path, timeout=10):
        self.path = pathlib.Path(path).resolve()
        self.timeout = timeout
        # TODO: Check database version, as separate method

    def connect(self, params='mode=rw'):
        # Some pragmas cannot be used or are ineffective within a transaction,
        # and autocommit=False always has a transaction open. Open the
        # connection with autocommit=True, then switch after configuration.
        db = sqlite3.connect(f'{self.path.as_uri()}?{params}', uri=True,
                             timeout=self.timeout, autocommit=True,
                             check_same_thread=True)
        db.execute("pragma journal_mode = wal")
        db.execute("pragma foreign_keys = on")
        db.autocommit = False
        return db

    def meta(self, db, key, default=None):
        for value, in db.execute(
                "select value from meta where key = ?", (key,)):
            return value
        return default

    def dev(self, db):
        return bool(self.meta(db, 'dev', False))

    def create(self, version=None, dev=False):
        self._check_version(version)
        if self.path.exists():
            raise Exception("Store database already exists")
        with contextlib.closing(self.connect('mode=rwc')) as db:
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

    def users(self, db):
        return [(name, uid, to_datetime(created))
                for uid, name, created in db.execute("""
                    select id, name, created from users
                """)]

    def create_users(self, db, names):
        now = time.time_ns()
        db.executemany("""
            insert into users (id, name, created) values (?, ?, ?)
        """, [(secrets.randbelow(1 << 63), n, now) for n in names])
        uids = [fetch_row(db, "select id from users where name = ?",
                          (n,))[0]
                for n in names]
        return uids

    def user_memberships(self, db, origin, user, transitive=False):
        self.check_origin(db, origin)
        return list(db.execute("""
            select group_, transitive from user_memberships
            left join users on users.id = user
            where origin = ? and users.name = ?
              and (? or not transitive)
        """, (origin, user, transitive)))

    def tokens(self, db, expired=False):
        now = time.time_ns()
        return [(name, uid, token, to_datetime(created), to_datetime(expires))
                for token, uid, name, created, expires in db.execute("""
                    select token, users.id, users.name, user_tokens.created,
                           expires
                    from user_tokens
                    left join users on users.id = user_tokens.user
                    where ? or expires is null or ? < expires
                """, (expired, now))]

    def create_tokens(self, db, users, expires=None):
        now = time.time_ns()
        expires = to_nsec(expires)
        tokens = [secrets.token_urlsafe() for _ in users]
        # TODO: Use subquery instead of resolving users upfront
        uids = []
        for user in users:
            for uid, in db.execute(
                "select id from users where name = ?", (user,)): break
            else:
                raise Exception(f"Unknown user: {user}")
            uids.append(uid)
        db.executemany("""
            insert into user_tokens (token, user, created, expires)
                values (?, ?, ?, ?)
        """, [(token, uid, now, expires)
              for uid, token in zip(uids, tokens)])
        return tokens

    def expire_tokens(self, db, tokens, expires=None):
        expires = to_nsec(expires, time.time_ns())
        db.executemany("""
            update user_tokens set expires = ?
            where token = ?
               or exists(select 1 from users where id = user and name = ?)
        """, [(expires, token, token) for token in tokens])

    def check_origin(self, db, origin):
        if not origin and not self.dev(db):
            raise Exception("No origin specified")

    def groups(self, db):
        return [g for g, in db.execute("""
                    select distinct group_ from user_memberships
                    union
                    select distinct group_ from group_memberships
                    union
                    select distinct member from group_memberships
                """)]

    def group_members(self, db, origin, group=None, transitive=False):
        # TODO: Make group a regexp
        self.check_origin(db, origin)
        return list(db.execute("""
            select group_, 'user', users.name, transitive from user_memberships
            left join users on users.id = user
            where origin = :origin
              and (:group is null or group_ = :group)
              and (:transitive or not transitive)
            union all
            select group_, 'group', member, false from group_memberships
            where origin = :origin
              and (:group is null or group_ = :group)
        """, {'origin': origin, 'group': group, 'transitive': transitive}))

    def group_memberships(self, db, origin, group):
        self.check_origin(db, origin)
        return [g for g, in db.execute("""
                    select group_ from group_memberships
                    where origin = ? and member = ?
                """, (origin, group))]

    def modify_groups(self, db, origin, groups, add_users=None, add_groups=None,
                      remove_users=None, remove_groups=None):
        self.check_origin(db, origin)
        if add_users:
            db.executemany("""
                insert or replace into user_memberships
                    (origin, user, group_, transitive)
                    values (?, (select id from users where name = ?), ?, false)
            """, [(origin, name, group) for name in add_users
                  for group in groups])
        if remove_users:
            db.executemany("""
                delete from user_memberships
                where origin = ?
                  and user in (select id from users where name = ?)
                  and group_ = ?
            """, [(origin, name, group) for name in remove_users
                  for group in groups])
        if add_groups:
            db.executemany("""
                insert or ignore into group_memberships (origin, member, group_)
                    values (?, ?, ?)
            """, [(origin, name, group) for name in add_groups
                  for group in groups])
        if remove_groups:
            db.executemany("""
                delete from group_memberships
                where origin = ? and member = ? and group_ = ?
            """, [(origin, name, group) for name in remove_groups
                  for group in groups])
        self.compute_transitive_memberships(db, origin)

    def compute_transitive_memberships(self, db, origin):
        items = list(db.execute("""
            select user, group_ from user_memberships
            where origin = ? and not transitive
        """, (origin,)))
        gm = {}
        for member, group in db.execute("""
                    select member, group_ from group_memberships
                    where origin = ?
                """, (origin,)):
            gm.setdefault(member, []).append(group)
        trans = set()
        while items:
            uid, group = it = items.pop()
            if it in trans: continue
            trans.add(it)
            items.extend((uid, g) for g in gm.get(group, []))
        db.execute("""
            delete from user_memberships where origin = ? and transitive
        """, (origin,))
        db.executemany("""
            insert or ignore into
                user_memberships (origin, user, group_, transitive)
                values (?, ?, ?, true)
        """, [(origin, uid, group) for uid, group in trans])

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
        db.execute("insert into meta values ('dev', ?)", (bool(dev),))
        if not dev: return
        db.execute("insert into auth (token, perms) values ('*', '*')")

    def version_2(self, db, dev, now):
        db.executescript("""
-- Convert the meta table to "without rowid".
alter table meta rename to _meta;
create table meta (
    key text primary key,
    value any
) strict, without rowid;
insert into meta select * from _meta;
drop table _meta;

-- Create tables for user management.
create table users (
    id integer primary key,
    name text not null unique,
    created integer not null
) strict;
create table user_tokens (
    token text primary key,
    user integer not null,
    created integer not null,
    expires integer,
    foreign key (user) references users(id)
) strict, without rowid;

-- Create tables for group management.
create table user_memberships (
    origin text not null,
    user integer not null,
    group_ text not null,
    transitive integer not null,
    primary key (origin, user, group_),
    foreign key (user) references users(id)
) strict, without rowid;
create table group_memberships (
    origin text not null,
    member text not null,
    group_ text not null,
    primary key (origin, member, group_)
) strict, without rowid;

-- Create table for solutions state management.
create table solutions (
    origin text not null,
    page text not null,
    show text not null,
    primary key (origin, page)
) strict, without rowid;
""")
        if not dev: return
        db.execute("""
insert into users (id, name, created) values (1, 'admin', ?)
""", (now,))
        db.execute("""
insert into user_tokens (token, user, created) values ('admin', 1, ?)
""", (now,))
        db.execute("""
insert into user_memberships (origin, user, group_, transitive)
    values ('', 1, '*', false)
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
            with self.db as db:
                user, = fetch_row(db, """
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
        return bool(fetch_row(db, f"""
            select exists(
                select 1 from user_memberships
                where origin = ? and user = ? and (group_ = ? or group_ = '*')
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
        origin = wsgi.origin(env)
        with self.db as db:
            name, = fetch_row(db, """
                select name from users where id = ?
            """, (user,))
            groups = [g for g, in db.execute("""
                select group_ from user_memberships
                where origin = ? and user = ?
            """, (origin, user))]
        return wsgi.respond_json(
            respond, {'id': user, 'name': name, 'groups': groups})


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
