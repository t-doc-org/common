# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import contextlib
import datetime
import functools
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


def placeholders(args): return ', '.join('?' * len(args))


class Seqs(dict):
    __slots__ = ()
    mask = (1 << 32) - 1
    mask2 = mask >> 1

    @classmethod
    def newer_than(cls, a, b):
        return b is None or 0 < ((a - b) & cls.mask) <= cls.mask2

    def merge(self, it):
        for key, seq in it:
            if self.newer_than(seq, self.get(key)): self[key] = seq


class Connection(sqlite3.Connection):
    def __enter__(self):
        self._notify = Seqs()
        return super().__enter__()

    def __exit__(self, typ, value, tb):
        res = super().__exit__(typ, value, tb)
        if typ is None and self._notify:
            self._store.notify(self._notify)
        del self._notify
        return res

    def notify(self, *keys):
        for key in keys:
            self._notify[key], = self.row("""
                insert into notifications (key, seq) values (?, 1)
                on conflict do update set seq = (seq + 1) & ?
                returning seq
            """, (key, Seqs.mask))

    def notifications(self, keys):
        return Seqs(self.execute(f"""
            select key, seq from notifications
            where key in ({placeholders(keys)})
        """, keys))

    def row(self, sql, params=(), default=None):
        for row in self.execute(sql, params): return row
        return default

    def meta(self, key, default=None):
        for value, in self.execute(
                "select value from meta where key = ?", (key,)):
            return value
        return default

    @property
    def dev(self):
        return bool(self.meta('dev', False))

    def check_origin(self, origin):
        if not origin and not self.dev:
            raise Exception("No origin specified")

    @functools.cached_property
    def users(self): return Users(self)

    @functools.cached_property
    def tokens(self): return Tokens(self)

    @functools.cached_property
    def groups(self): return Groups(self)

    @functools.cached_property
    def solutions(self): return Solutions(self)

    @functools.cached_property
    def polls(self): return Polls(self)


class DbNamespace:
    def __init__(self, db): self.db = db
    def __getattr__(self, name): return getattr(self.db, name)


class Users(DbNamespace):
    def member_of(self, origin, user, group):
        if user is None: return False
        return bool(self.row("""
            select exists(
                select 1 from user_memberships
                where (origin, user) = (?, ?) and (group_ = ? or group_ = '*')
            )
        """, (origin, user, group))[0])

    def info(self, origin, user):
        name, = self.row("select name from users where id = ?", (user,))
        groups = [g for g, in self.execute("""
            select group_ from user_memberships where (origin, user) = (?, ?)
        """, (origin, user))]
        return {'name': name, 'groups': groups}

    def list(self, users=''):
        return [(name, uid, to_datetime(created))
                for uid, name, created in self.execute("""
                    select id, name, created from users
                    where name regexp ?
                """, (users,))]

    def create(self, names):
        now = time.time_ns()
        uids = [secrets.randbelow(1 << 63) for _ in names]
        self.executemany("""
            insert into users (id, name, created) values (?, ?, ?)
        """, [(uid, name, now) for uid, name in zip(uids, names)])
        return uids

    def memberships(self, origin, users='', transitive=False):
        self.check_origin(origin)
        return list(self.execute("""
            select users.name, group_, transitive from user_memberships
            left join users on users.id = user
            where origin = ? and users.name regexp ?
              and (? or not transitive)
        """, (origin, users, transitive)))


class Tokens(DbNamespace):
    def authenticate(self, token):
        return self.row("""
            select user from user_tokens
            where token = ? and (expires is null or ? < expires)
        """, (token, time.time_ns()), default=(None,))[0]

    def list(self, users='', expired=False):
        now = time.time_ns()
        return [(name, uid, token, to_datetime(created), to_datetime(expires))
                for token, uid, name, created, expires in self.execute("""
                    select token, users.id, users.name, user_tokens.created,
                           expires
                    from user_tokens
                    left join users on users.id = user_tokens.user
                    where users.name regexp ?
                      and (? or expires is null or ? < expires)
                """, (users, expired, now))]

    def create(self, users, expires=None):
        now = time.time_ns()
        expires = to_nsec(expires)
        tokens = [secrets.token_urlsafe() for _ in users]
        self.executemany("""
            insert into user_tokens (token, user, created, expires)
                values (?, (select id from users where name = ?), ?, ?)
        """, [(token, user, now, expires)
              for user, token in zip(users, tokens)])
        return tokens

    def expire(self, tokens, expires=None):
        expires = to_nsec(expires, time.time_ns())
        self.executemany("""
            update user_tokens set expires = ?
            where token = ?
               or exists(select 1 from users where id = user and name = ?)
        """, [(expires, token, token) for token in tokens])


class Groups(DbNamespace):
    def list(self, groups=''):
        return [g for g, in self.execute("""
                    select distinct group_ from user_memberships
                    where group_ regexp :groups
                    union
                    select distinct group_ from group_memberships
                    where group_ regexp :groups
                    union
                    select distinct member from group_memberships
                    where member regexp :groups
                """, {'groups': groups})]

    def members(self, origin, groups='', transitive=False):
        self.check_origin(origin)
        return list(self.execute("""
            select group_, 'user', users.name, transitive from user_memberships
            left join users on users.id = user
            where origin = :origin and group_ regexp :groups
              and (:transitive or not transitive)
            union all
            select group_, 'group', member, false from group_memberships
            where origin = :origin and group_ regexp :groups
        """, {'origin': origin, 'groups': groups, 'transitive': transitive}))

    def memberships(self, origin, groups=''):
        self.check_origin(origin)
        return list(self.execute("""
            select member, group_ from group_memberships
            where origin = ? and member regexp ?
        """, (origin, groups)))

    def modify(self, origin, groups, add_users=None, add_groups=None,
               remove_users=None, remove_groups=None):
        self.check_origin(origin)
        if add_users:
            self.executemany("""
                insert or replace into user_memberships
                    (origin, user, group_, transitive)
                    values (?, (select id from users where name = ?), ?, false)
            """, [(origin, name, group) for name in add_users
                  for group in groups])
        if remove_users:
            self.executemany("""
                delete from user_memberships
                where origin = ?
                  and user in (select id from users where name = ?)
                  and group_ = ?
            """, [(origin, name, group) for name in remove_users
                  for group in groups])
        if add_groups:
            self.executemany("""
                insert or ignore into group_memberships (origin, member, group_)
                    values (?, ?, ?)
            """, [(origin, name, group) for name in add_groups
                  for group in groups])
        if remove_groups:
            self.executemany("""
                delete from group_memberships
                where (origin, member, group_) = (?, ?, ?)
            """, [(origin, name, group) for name in remove_groups
                  for group in groups])
        self.compute_transitive_memberships(origin)

    def compute_transitive_memberships(self, origin):
        items = list(self.execute("""
            select user, group_ from user_memberships
            where origin = ? and not transitive
        """, (origin,)))
        gm = {}
        for member, group in self.execute("""
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
        self.execute("""
            delete from user_memberships where origin = ? and transitive
        """, (origin,))
        self.executemany("""
            insert or ignore into
                user_memberships (origin, user, group_, transitive)
                values (?, ?, ?, true)
        """, [(origin, uid, group) for uid, group in trans])


class Solutions(DbNamespace):
    @staticmethod
    def show_key(origin, page):
        return f'solutions:{origin}:{page}'

    def set_show(self, origin, page, show):
        self.execute("""
            insert or replace into solutions (origin, page, show)
                values (?, ?, ?)
        """, (origin, page, show))
        self.notify(self.show_key(origin, page))

    def get_show(self, origin, page):
        return self.row("""
            select show from solutions where (origin, page) = (?, ?)
        """, (origin, page), default=(None,))[0]


class Polls(DbNamespace):
    @staticmethod
    def poll_key(origin, poll):
        return f'polls:{origin}:{poll}'

    @staticmethod
    def voter_key(origin, poll, voter):
        return f'polls:{origin}:{poll}:{voter}'

    def open(self, origin, poll, mode, answers, expires=None):
        self.execute("""
            insert into polls
                (origin, id, mode, answers, expires, results, solutions)
                values (:origin, :poll, :mode, :answers, :expires, 0, 0)
            on conflict do update
                set (mode, answers, expires, results, solutions)
                = (:mode, :answers, :expires, 0, 0)
        """, {'origin': origin, 'poll': poll, 'mode': mode,
             'answers': answers, 'expires': expires})
        self.notify(self.poll_key(origin, poll))

    def close(self, origin, ids):
        self.executemany("""
            insert into polls (origin, id, mode) values (?, ?, null)
            on conflict do update set mode = null
        """, [(origin, p) for p in ids])
        self.notify(*(self.poll_key(origin, p) for p in ids))

    def results(self, origin, ids, value):
        value = bool(value)
        self.executemany("""
            insert into polls (origin, id, results)
                values (:origin, :poll, :results)
            on conflict do update set results = :results
        """, [{'origin': origin, 'poll': p, 'results': value} for p in ids])
        self.notify(*(self.poll_key(origin, p) for p in ids))

    def solutions(self, origin, ids, value):
        value = bool(value)
        self.executemany("""
            insert into polls (origin, id, solutions)
                values (:origin, :poll, :solutions)
            on conflict do update set solutions = :solutions
        """, [{'origin': origin, 'poll': p, 'solutions': value} for p in ids])
        self.notify(*(self.poll_key(origin, p) for p in ids))

    def clear(self, origin, ids):
        phs = placeholders(ids)
        args = (origin, *ids)
        voters = list(self.execute(f"""
            select distinct poll, voter from poll_votes
            where origin = ? and poll in ({phs})
        """, args))
        self.execute(f"""
            delete from poll_votes where origin = ? and poll in ({phs})
        """, args)
        self.notify(*(self.poll_key(origin, p) for p in ids),
                    *(self.voter_key(origin, p, v) for p, v in voters))

    def vote(self, origin, poll, voter, answer, vote):
        mode, exp, answers = self.row("""
            select mode, expires, answers from polls
            where (origin, id) = (?, ?)
        """, (origin, poll), default=(None, None, 0))
        if (mode is None or (exp is not None and time.time_ns() >= exp)
                or answer < 0 or answer >= answers):
            return False
        self.notify(self.poll_key(origin, poll),
                    self.voter_key(origin, poll, voter))
        if not vote:
            self.execute("""
                delete from poll_votes
                where (origin, poll, voter, answer) = (?, ?, ?, ?)
            """, (origin, poll, voter, answer))
            return True
        if mode != 'multi':
            self.execute("""
                delete from poll_votes
                where (origin, poll, voter) = (?, ?, ?) and answer != ?
            """, (origin, poll, voter, answer))
        self.execute("""
            insert or replace into poll_votes
                (origin, poll, voter, answer) values (?, ?, ?, ?)
        """, (origin, poll, voter, answer))
        return True

    def poll_data(self, origin, poll, force_results=False):
        mode, exp, results, solutions = self.row("""
            select mode, expires, results, solutions from polls
            where (origin, id) = (?, ?)
        """, (origin, poll), default=(None, None, False, False))
        if exp is not None and time.time_ns() >= exp: mode = None
        voters, votes = self.row("""
            select count(distinct voter), count(*) from poll_votes
            where (origin, poll) = (?, ?)
        """, (origin, poll))
        data = {'open': mode is not None, 'results': bool(results),
                'solutions': bool(solutions), 'voters': voters, 'votes': votes,
                'exp': exp}
        if results or force_results:
            data['answers'] = dict(self.execute("""
                select answer, count(*) from poll_votes
                where (origin, poll) = (?, ?)
                group by answer order by answer
            """, (origin, poll)))
        return data

    def votes_data(self, origin, voter, pids):
        votes = {}
        for p, a in self.execute(f"""
                    select poll, answer from poll_votes
                    where (origin, voter) = (?, ?)
                      and poll in ({placeholders(pids)})
                    order by poll, answer
                """, (origin, voter, *pids)):
            votes.setdefault(p, []).append(a)
        return {'votes': votes}


class ConnectionPool:
    def __init__(self, store, size=None):
        self.store = store
        self.size = size
        self.lock = threading.Lock()
        self.connections = []

    def get(self):
        with self.lock:
            if self.connections: return self.connections.pop()
        return self.store.connect(check_same_thread=False)

    def release(self, db):
        with self.lock:
            if self.size is None or len(self.connections) < self.size:
                db.rollback()
                self.connections.append(db)
            else:
                db.close()


class Waker:
    def __init__(self, cv, limit):
        self.cv = cv
        self.limit = limit
        self._wake = False

    def wait(self, cond, until=None):
        if self.limit is not None and (d := self.limit()) > 0:
            if self.cv.wait_for(cond, d): return
        timeout = None
        if until is not None:
            timeout = until - time.time_ns()
            if timeout <= 0: return
            timeout /= 1_000_000_000
        self.cv.wait_for(lambda: self._wake or cond(), timeout=timeout)
        self._wake = False

    def wake(self):
        with self.cv:
            self._wake = True
            self.cv.notify()


class WakerSet(set):
    __slots__ = ('seq',)

    def __init__(self):
        super().__init__()
        self.seq = None


class Store:
    def __init__(self, path, timeout=10, poll_interval=1):
        self.path = pathlib.Path(path).resolve() if path is not None else None
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.lock = threading.Condition(threading.Lock())
        self.wakers = {}
        self._wake = Seqs()

    def start(self):
        self.dispatcher_db = self.connect(params='mode=ro',
                                          check_same_thread=False)
        if self.path is None: self.create(dev=True)  # Create in-memory DB
        self.dispatcher = threading.Thread(target=self.dispatch)
        with self.lock: self._stop = False
        self.dispatcher.start()

    def stop(self):
        with self.lock:
            self._stop = True
            self.lock.notify()
        self.dispatcher.join()
        self.dispatcher_db.close()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, typ, value, tb):
        self.stop()

    def connect(self, *, path=False, params='mode=rw', check_same_thread=True):
        if path is False: path = self.path
        uri = f'{path.as_uri()}?{params}' if path is not None \
              else 'file:store?mode=memory&cache=shared'
        # Some pragmas cannot be used or are ineffective within a transaction,
        # and autocommit=False always has a transaction open. Open the
        # connection with autocommit=True, then switch after configuration.
        db = sqlite3.connect(uri, uri=True, timeout=self.timeout,
                             factory=Connection, autocommit=True,
                             check_same_thread=check_same_thread)
        db.execute("pragma journal_mode = wal")
        db.execute("pragma foreign_keys = on")
        db.autocommit = False
        db.create_function(
            'regexp', 2, lambda pat, v: re.search(pat, v) is not None,
            deterministic=True)
        db._store = self
        return db

    def pool(self, **kwargs):
        return ConnectionPool(self, **kwargs)

    @contextlib.contextmanager
    def waker(self, cv, keys, db, limit=None):
        w = Waker(cv, limit)
        with self.lock:
            seq_keys = []
            for key in keys:
                ws = self.wakers.get(key)
                if ws is None:
                    ws = self.wakers[key] = WakerSet()
                    seq_keys.append(key)
                ws.add(w)
            if seq_keys:
                with db: seqs = db.notifications(seq_keys)
                for key, seq in seqs.items():
                    self.wakers[key].seq = seq
        try:
            yield w
        finally:
            with self.lock:
                for key in keys:
                    ws = self.wakers[key]
                    ws.remove(w)
                    if not ws: del self.wakers[key]

    def notify(self, seqs):
        with self.lock:
            self._wake.merge(seqs.items())
            self.lock.notify()

    def dispatch(self):
        next_poll = None
        if self.poll_interval is not None:
            poll_interval = int(self.poll_interval * 1_000_000_000)
            next_poll = time.monotonic_ns() + poll_interval
        db = self.dispatcher_db
        while True:
            with self.lock:
                timeout = (next_poll - time.monotonic_ns()) / 1_000_000_000 \
                          if next_poll is not None else None
                self.lock.wait_for(lambda: self._stop or self._wake,
                                   timeout=timeout)
                if self._stop: break
                wakers = set()
                self._update_waker_seqs(self._wake, wakers)
                self._wake.clear()
                if next_poll is not None and time.monotonic_ns() >= next_poll:
                    if self.wakers:
                        with db: seqs = db.notifications(list(self.wakers))
                        self._update_waker_seqs(seqs, wakers)
                    next_poll = time.monotonic_ns() + poll_interval
            for w in wakers: w.wake()

    def _update_waker_seqs(self, seqs, updated):
        for key, seq in seqs.items():
            if (ws := self.wakers.get(key)) is not None \
                    and Seqs.newer_than(seq, ws.seq):
                ws.seq = seq
                updated.update(ws)

    def backup(self, db, dest):
        if dest.exists():
            raise Exception("Backup destination already exists")
        with contextlib.closing(
                self.connect(path=dest, params='mode=rwc')) as ddb:
            db.backup(ddb)

    def create(self, version=None, dev=False):
        self._check_version(version)
        if self.path is not None and self.path.exists():
            raise Exception("Store database already exists")
        with contextlib.closing(self.connect(params='mode=rwc')) as db:
            return self._upgrade(db, from_version=0, to_version=version,
                                 dev=dev)

    def upgrade(self, db, version=None, on_version=None):
        self._check_version(version)
        from_version = db.meta('version')
        to_version = self._upgrade(db, from_version=from_version,
                                   to_version=version, dev=db.dev,
                                   on_version=on_version)
        return from_version, to_version

    def _check_version(self, version):
        if version is None: return
        for v, _ in self.versions():
            if v == version: return
        raise Exception(f"Invalid store version: {version}")

    def _upgrade(self, db, from_version, to_version, dev, on_version=None):
        now = time.time_ns()
        version = from_version
        for v, fn in self.versions(from_version + 1):
            if to_version is not None and v > to_version: break
            if on_version is not None: on_version(v)
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

    def version(self, db):
        version = db.meta('version')
        latest = max(v for v, _ in self.versions())
        return version, latest

    def check_version(self):
        with contextlib.closing(self.connect()) as db, db:
            version, latest = self.version(db)
        if version != latest:
            raise Exception("Store version mismatch "
                            f"(current: {version}, want: {latest})")

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
    foreign key (user) references users (id)
) strict, without rowid;

-- Create tables for group management.
create table user_memberships (
    origin text not null,
    user integer not null,
    group_ text not null,
    transitive integer not null,
    primary key (origin, user, group_),
    foreign key (user) references users (id)
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

    def version_3(self, db, dev, now):
        db.executescript("""
-- Create tables for poll state.
create table polls (
    origin text not null,
    id text not null,
    mode text,
    answers integer not null default 0,
    expires integer,
    results integer not null default 0,
    solutions integer not null default 0,
    primary key (origin, id)
) strict;
create table poll_votes (
    origin text not null,
    poll text not null,
    voter text not null,
    answer integer not null,
    primary key (origin, poll, voter, answer),
    foreign key (origin, poll) references polls (origin, id)
) strict;
""")

    def version_4(self, db, dev, now):
        db.executescript("""
create table notifications (
    key text primary key,
    seq integer not null
) strict, without rowid;
""")
