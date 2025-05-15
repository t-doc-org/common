# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import contextlib
import datetime
import pathlib
import re
import secrets
import sqlite3
import threading
import time


def to_datetime(nsec):
    if nsec is None: return
    return datetime.datetime.fromtimestamp(nsec / 1e9)


def to_nsec(dt, default=None):
    if dt is None: return default
    return int(dt.timestamp() * 1e9)


class Connection(sqlite3.Connection):
    def row(self, sql, params=(), default=None):
        for row in self.execute(sql, params): return row
        return default


class ConnectionPool:
    def __init__(self, store):
        self.store = store
        self.lock = threading.Lock()
        self.connections = []

    def get(self):
        with self.lock:
            if self.connections: return self.connections.pop()
        return self.store.connect(check_same_thread=False)

    def release(self, db):
        with self.lock: self.connections.append(db)


class Store:
    def __init__(self, path, timeout=10):
        self.path = pathlib.Path(path).resolve()
        self.timeout = timeout
        # TODO: Check database version, as separate method

    def connect(self, params='mode=rw', check_same_thread=True):
        # Some pragmas cannot be used or are ineffective within a transaction,
        # and autocommit=False always has a transaction open. Open the
        # connection with autocommit=True, then switch after configuration.
        db = sqlite3.connect(f'{self.path.as_uri()}?{params}', uri=True,
                             timeout=self.timeout, autocommit=True,
                             check_same_thread=check_same_thread,
                             factory=Connection)
        db.execute("pragma journal_mode = wal")
        db.execute("pragma foreign_keys = on")
        db.autocommit = False
        db.create_function(
            'regexp', 2, lambda pat, v: re.search(pat, v) is not None,
            deterministic=True)
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

    def users(self, db, users=''):
        return [(name, uid, to_datetime(created))
                for uid, name, created in db.execute("""
                    select id, name, created from users
                    where name regexp ?
                """, (users,))]

    def create_users(self, db, names):
        now = time.time_ns()
        uids = [secrets.randbelow(1 << 63) for _ in names]
        db.executemany("""
            insert into users (id, name, created) values (?, ?, ?)
        """, [(uid, name, now) for uid, name in zip(uids, names)])
        return uids

    def user_memberships(self, db, origin, users='', transitive=False):
        self.check_origin(db, origin)
        return list(db.execute("""
            select users.name, group_, transitive from user_memberships
            left join users on users.id = user
            where origin = ? and users.name regexp ?
              and (? or not transitive)
        """, (origin, users, transitive)))

    def tokens(self, db, users='', expired=False):
        now = time.time_ns()
        return [(name, uid, token, to_datetime(created), to_datetime(expires))
                for token, uid, name, created, expires in db.execute("""
                    select token, users.id, users.name, user_tokens.created,
                           expires
                    from user_tokens
                    left join users on users.id = user_tokens.user
                    where users.name regexp ?
                      and (? or expires is null or ? < expires)
                """, (users, expired, now))]

    def create_tokens(self, db, users, expires=None):
        now = time.time_ns()
        expires = to_nsec(expires)
        tokens = [secrets.token_urlsafe() for _ in users]
        db.executemany("""
            insert into user_tokens (token, user, created, expires)
                values (?, (select id from users where name = ?), ?, ?)
        """, [(token, user, now, expires)
              for user, token in zip(users, tokens)])
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

    def groups(self, db, groups=''):
        return [g for g, in db.execute("""
                    select distinct group_ from user_memberships
                    where group_ regexp :groups
                    union
                    select distinct group_ from group_memberships
                    where group_ regexp :groups
                    union
                    select distinct member from group_memberships
                    where member regexp :groups
                """, {'groups': groups})]

    def group_members(self, db, origin, groups='', transitive=False):
        self.check_origin(db, origin)
        return list(db.execute("""
            select group_, 'user', users.name, transitive from user_memberships
            left join users on users.id = user
            where origin = :origin and group_ regexp :groups
              and (:transitive or not transitive)
            union all
            select group_, 'group', member, false from group_memberships
            where origin = :origin and group_ regexp :groups
        """, {'origin': origin, 'groups': groups, 'transitive': transitive}))

    def group_memberships(self, db, origin, groups=''):
        self.check_origin(db, origin)
        return list(db.execute("""
            select member, group_ from group_memberships
            where origin = ? and member regexp ?
        """, (origin, groups)))

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
