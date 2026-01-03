# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import contextlib
import functools
import json
import secrets
import threading
import time

from . import database, logs

log = logs.logger(__name__)
max_id_len = 64  # Maximum length of globally-unique identifiers
max_voters_per_poll = 100  # Maximum number of voters per poll


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


class Connection(database.Connection):
    def notify(self, *keys):
        raise TypeError("Notification on read-only connection")

    def notifications(self, keys):
        return Seqs(self.execute(f"""
            select key, seq from notifications
            where key in ({database.placeholders(keys)})
        """, keys))

    def check_origin(self, origin):
        if not origin and not self.dev:
            raise Exception("No origin specified")

    @functools.cached_property
    def users(self): return Users(self)

    @functools.cached_property
    def tokens(self): return Tokens(self)

    @functools.cached_property
    def oidc(self): return Oidc(self)

    @functools.cached_property
    def groups(self): return Groups(self)

    @functools.cached_property
    def solutions(self): return Solutions(self)

    @functools.cached_property
    def polls(self): return Polls(self)


class WriteConnection(Connection):
    def __enter__(self):
        self._notify = Seqs()
        return super().__enter__()

    def __exit__(self, typ, value, tb):
        res = super().__exit__(typ, value, tb)
        if typ is None and self._notify:
            self.database.notify(self._notify)
        del self._notify
        return res

    def notify(self, *keys):
        for key in keys:
            self._notify[key], = self.row("""
                insert into notifications (key, seq) values (?, 1)
                on conflict do update set seq = (seq + 1) & ?
                returning seq
            """, (key, Seqs.mask))


class Users(database.ConnNamespace):
    def member_of(self, origin, uid, group):
        if uid is None: return False
        return bool(self.row("""
            select exists(
                select 1 from user_memberships
                where (origin, user) = (?, ?) and (group_ = ? or group_ = '*')
            )
        """, (origin, uid, group))[0])

    def info(self, origin, uid):
        name, = self.row("select name from users where id = ?", (uid,))
        groups = [g for g, in self.execute("""
            select group_ from user_memberships where (origin, user) = (?, ?)
        """, (origin, uid))]
        return {'name': name, 'groups': groups}

    def uid(self, name):
        if name.startswith('#'): return int(name[1:])
        uids = [u for u, in self.execute("select id from users where name = ?",
                                         (name,))]
        if len(uids) == 1: return uids[0]
        if not uids: raise database.Error(f"User not found: {name}")
        uids.sort()
        raise database.Error(
            f"Ambiguous user name %r: {" ".join(f"#{u}" for u in uids)}")

    def list(self, name_re=''):
        return [(name, uid, database.to_datetime(created))
                for uid, name, created in self.execute("""
                    select id, name, created from users
                    where name regexp ?
                """, (name_re,))]

    def create(self, names):
        if invalid := [n for n in names if n.startswith('#')]:
            raise database.Error(f"Invalid user names: {" ".join(invalid)}")
        now = time.time_ns()
        uids = [secrets.randbelow(1 << 63) for _ in names]
        self.executemany("""
            insert into users (id, name, created) values (?, ?, ?)
        """, [(uid, name, now) for uid, name in zip(uids, names)])
        return uids

    def memberships(self, origin, name_re='', transitive=False):
        self.check_origin(origin)
        return list(self.execute("""
            select users.name, group_, transitive from user_memberships
            left join users on users.id = user
            where origin = ? and users.name regexp ?
              and (? or not transitive)
        """, (origin, name_re, transitive)))


class Tokens(database.ConnNamespace):
    min_generated_token_len = 16

    def authenticate(self, token):
        return self.row("""
            select user from user_tokens
            where token = ? and (expires is null or ? < expires)
        """, (token, time.time_ns()), default=(None,))[0]

    def find(self, user):
        return self.row("""
            select token from user_tokens
            where user = ? and  (expires is null or ? < expires)
            order by created limit 1
        """, (user, time.time_ns()), default=(None,))[0]

    def list(self, user_re='', expired=False):
        now = time.time_ns()
        return [(name, uid, token, database.to_datetime(created),
                 database.to_datetime(expires))
                for token, uid, name, created, expires in self.execute("""
                    select token, users.id, users.name, user_tokens.created,
                           expires
                    from user_tokens
                    left join users on users.id = user_tokens.user
                    where users.name regexp ?
                      and (? or expires is null or ? < expires)
                """, (user_re, expired, now))]

    def create(self, uids, expires=None):
        now = time.time_ns()
        expires = database.to_nsec(expires)
        tokens = [secrets.token_urlsafe() for _ in uids]
        self.executemany("""
            insert into user_tokens (token, user, created, expires)
                values (?, ?, ?, ?)
        """, [(token, user, now, expires)
              for user, token in zip(uids, tokens)])
        return tokens

    def expire(self, tokens, expires=None):
        expires = database.to_nsec(expires, time.time_ns())
        self.executemany("""
            update user_tokens set expires = ?
            where token = ?
               or exists(select 1 from users where id = user and name = ?)
        """, [(expires, token, token) for token in tokens])

    def remove(self, tokens):
        # Don't remove non-generated tokens.
        self.executemany("delete from user_tokens where token = ?",
                         [(t,) for t in tokens
                          if len(t) >= self.min_generated_token_len])


class Oidc(database.ConnNamespace):
    state_lifetime = 10 * 60 * 1_000_000_000

    def create_state(self, state, data):
        self.execute("""
            insert into oidc_states (state, created, data) values (?, ?, ?)
        """, (state, time.time_ns(), database.to_json(data)))

    def state(self, state):
        data = self.row("select data from oidc_states where state = ?",
                        (state,), default=(None,))[0]
        self.execute("delete from oidc_states where state = ? or created < ?",
                     (state, time.time_ns() - self.state_lifetime))
        return json.loads(data)

    def user(self, id_token):
        return self.row("""
            select user, id_token, updated from oidc_users
            where (issuer, subject) = (?, ?)
        """, (id_token['iss'], id_token['sub']), default=(None, None, None))

    def logins(self, user):
        return [(json.loads(id_token), database.to_datetime(updated))
                for id_token, updated in self.execute("""
                    select id_token, updated from oidc_users
                    where user = ?
                """, (user,))]

    def add_login(self, user, id_token):
        self.execute("""
            insert or replace into oidc_users
                (issuer, subject, user, id_token, updated)
            values (?, ?, ?, ?, ?)
        """, (id_token['iss'], id_token['sub'], user,
              database.to_json(id_token), time.time_ns()))

    def remove_login(self, user, issuer, subject):
        self.execute("""
            delete from oidc_users where (issuer, subject, user) = (?, ?, ?)
        """, (issuer, subject, user))


class Groups(database.ConnNamespace):
    def list(self, name_re=''):
        return [g for g, in self.execute("""
                    select distinct group_ from user_memberships
                    where group_ regexp :name_re
                    union
                    select distinct group_ from group_memberships
                    where group_ regexp :name_re
                    union
                    select distinct member from group_memberships
                    where member regexp :name_re
                """, {'name_re': name_re})]

    def members(self, origin, name_re='', transitive=False):
        self.check_origin(origin)
        return list(self.execute("""
            select group_, 'user', users.name, transitive from user_memberships
            left join users on users.id = user
            where origin = :origin and group_ regexp :name_re
              and (:transitive or not transitive)
            union all
            select group_, 'group', member, false from group_memberships
            where origin = :origin and group_ regexp :name_re
        """, {'origin': origin, 'name_re': name_re, 'transitive': transitive}))

    def memberships(self, origin, name_re=''):
        self.check_origin(origin)
        return list(self.execute("""
            select member, group_ from group_memberships
            where origin = ? and member regexp ?
        """, (origin, name_re)))

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


class Solutions(database.ConnNamespace):
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


class Polls(database.ConnNamespace):
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
        phs = database.placeholders(ids)
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
        if len(voter) > max_id_len: raise database.Error("Invalid voter ID")
        mode, exp, answers = self.row("""
            select mode, expires, answers from polls
            where (origin, id) = (?, ?)
        """, (origin, poll), default=(None, None, 0))
        if mode is None or (exp is not None and time.time_ns() >= exp):
            raise database.Error("Voting is closed")
        if answer < 0 or answer >= answers:
            raise database.Error("Invalid answer")
        self.notify(self.poll_key(origin, poll),
                    self.voter_key(origin, poll, voter))
        if not vote:
            self.execute("""
                delete from poll_votes
                where (origin, poll, voter, answer) = (?, ?, ?, ?)
            """, (origin, poll, voter, answer))
            return
        if mode != 'multi':
            self.execute("""
                delete from poll_votes
                where (origin, poll, voter) = (?, ?, ?) and answer != ?
            """, (origin, poll, voter, answer))
        self.execute("""
            insert or replace into poll_votes
                (origin, poll, voter, answer) values (?, ?, ?, ?)
        """, (origin, poll, voter, answer))
        voters, = self.row("""
            select count(distinct voter) from poll_votes
            where (origin, poll) = (?, ?)
        """, (origin, poll))
        if voters > max_voters_per_poll: raise database.Error("Too many voters")

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
                      and poll in ({database.placeholders(pids)})
                    order by poll, answer
                """, (origin, voter, *pids)):
            votes.setdefault(p, []).append(a)
        return {'votes': votes}


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


class Store(database.Database):
    Connection = Connection
    WriteConnection = WriteConnection

    def __init__(self, config, **kwargs):
        super().__init__(config, **kwargs)
        self.poll_interval = config.get('poll_interval', 1)
        self.lock = threading.Condition(threading.Lock())
        self.wakers = {}
        self._wake = Seqs()

    def __enter__(self):
        log.debug("Store: %(path)s",
                  path=self.path if self.path is not None else ':in-memory:')
        res = super().__enter__()
        self.dispatcher_db = self.mem_db or self.connect(mode='ro')
        self.dispatcher = threading.Thread(target=self.dispatch,
                                           name='store:dispatcher')
        with self.lock: self._stop = False
        self.dispatcher.start()
        return res

    def __exit__(self, typ, value, tb):
        log.debug("Store: stopping")
        with self.lock:
            self._stop = True
            self.lock.notify()
        self.dispatcher.join()
        if self.dispatcher_db != self.mem_db: self.dispatcher_db.close()
        res = super().__exit__(typ, value, tb)
        log.debug("Store: done")
        return res

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
        # TODO: Make more resilient against DB errors
        next_poll = None
        if self.poll_interval > 0:
            poll_interval = int(self.poll_interval * 1_000_000_000)
            next_poll = time.monotonic_ns() + poll_interval
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
                        # TODO: Perform DB query outside of the lock
                        with self.dispatcher_db as db:
                            seqs = db.notifications(list(self.wakers))
                        self._update_waker_seqs(seqs, wakers)
                    next_poll = time.monotonic_ns() + poll_interval
            for w in wakers: w.wake()

    def _update_waker_seqs(self, seqs, updated):
        for key, seq in seqs.items():
            if (ws := self.wakers.get(key)) is not None \
                    and Seqs.newer_than(seq, ws.seq):
                ws.seq = seq
                updated.update(ws)

    def version_1(self, db, dev, now):
        db.create("""
            create table meta (
                key text primary key,
                value any
            ) strict
        """)
        db.create("""
            create table auth (
                token text primary key,
                perms text not null
            ) strict
        """)
        db.create("""
            create table log (
                time int not null,
                location text not null,
                session text,
                data text
            ) strict
        """)
        db.execute("insert into meta values ('dev', ?)", (bool(dev),))
        if not dev: return
        db.execute("insert into auth (token, perms) values ('*', '*')")

    def version_2(self, db, dev, now):
        # Convert the meta table to "without rowid".
        db.create("""
            create table meta_ (
                key text primary key,
                value any
            ) strict, without rowid
        """)
        db.execute("insert into meta_ select * from meta")
        db.execute("drop table meta")
        db.execute("alter table meta_ rename to meta")

        # Create tables for user management.
        db.create("""
            create table users (
                id integer primary key,
                name text not null unique,
                created integer not null
            ) strict
        """)
        db.create("""
            create table user_tokens (
                token text primary key,
                user integer not null,
                created integer not null,
                expires integer,
                foreign key (user) references users (id)
            ) strict, without rowid
        """)

        # Create tables for group management.
        db.create("""
            create table user_memberships (
                origin text not null,
                user integer not null,
                group_ text not null,
                transitive integer not null,
                primary key (origin, user, group_),
                foreign key (user) references users (id)
            ) strict, without rowid
        """)
        db.create("""
            create table group_memberships (
                origin text not null,
                member text not null,
                group_ text not null,
                primary key (origin, member, group_)
            ) strict, without rowid
        """)

        # Create table for solutions state management.
        db.create("""
            create table solutions (
                origin text not null,
                page text not null,
                show text not null,
                primary key (origin, page)
            ) strict, without rowid
        """)

        if not dev: return
        db.execute("""
            insert into users (id, name, created) values (1, 'admin', ?)
        """, (now,))
        db.execute("""
            insert into user_tokens (token, user, created)
                values ('admin', 1, ?)
        """, (now,))
        db.execute("""
            insert into user_memberships (origin, user, group_, transitive)
                values ('', 1, '*', false)
        """)

    def version_3(self, db, dev, now):
        # Create tables for poll state.
        db.create("""
            create table polls (
                origin text not null,
                id text not null,
                mode text,
                answers integer not null default 0,
                expires integer,
                results integer not null default 0,
                solutions integer not null default 0,
                primary key (origin, id)
            ) strict
        """)
        db.create("""
            create table poll_votes (
                origin text not null,
                poll text not null,
                voter text not null,
                answer integer not null,
                primary key (origin, poll, voter, answer),
                foreign key (origin, poll) references polls (origin, id)
            ) strict
        """)

    def version_4(self, db, dev, now):
        db.create("""
            create table notifications (
                key text primary key,
                seq integer not null
            ) strict, without rowid
        """)

    def version_5(self, db, dev, now):
        # Remove the uniqueness constraint on user names.
        db.create("""
            create table users_ (
                id integer primary key,
                name text not null,
                created integer not null
            ) strict
        """)
        db.execute("insert into users_ select * from users")
        db.execute("drop table users")
        db.execute("alter table users_ rename to users")

        # Create tables for OIDC.
        db.create("""
            create table oidc_states (
                state text primary key,
                created integer not null,
                data text not null
            ) strict, without rowid
        """)
        db.create("""
            create table oidc_users (
                issuer text not null,
                subject text not null,
                user integer not null,
                id_token text not null,
                updated integer not null,
                primary key (issuer, subject),
                foreign key (user) references users (id)
            ) strict
        """)
        db.create("create index user_oidcs on oidc_users (user)")

    def version_6(self, db, dev, now):
        # Drop unused tables.
        db.execute("drop table auth")
        db.execute("drop table log")
