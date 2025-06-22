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

from . import wsgi

missing = object()
# TODO(py-3.13): Remove Shutdown
Shutdown = getattr(queue, 'Shutdown', queue.Empty)


def arg(data, name, validate=None):
    if (v := data.get(name, missing)) is missing:
        raise wsgi.Error(HTTPStatus.BAD_REQUEST, f"Missing argument '{name}'")
    if validate is not None and not validate(v):
        raise wsgi.Error(HTTPStatus.BAD_REQUEST, f"Invalid argument '{name}'")
    return v


def args(data, *names):
    return tuple(arg(data, n) for n in names)


def check(cond, code=HTTPStatus.FORBIDDEN, msg=None):
    if not cond: raise wsgi.Error(code, msg)


class Api:
    def __init__(self, store, stderr=None, db_pool_size=16):
        if stderr is None: stderr = sys.stderr
        self.stderr = stderr
        self.store = store
        self.pool = store.pool(size=db_pool_size)
        self.events = EventsApi(self)
        self.endpoints = {
            'events': self.events,
            'health': self.handle_health,
            'log': self.handle_log,
            'poll': self.handle_poll,
            'solutions': self.handle_solutions,
            'user': self.handle_user,
        }

    def stop(self):
        self.events.stop()

    def __enter__(self): return self

    def __exit__(self, typ, value, tb):
        self.stop()

    def add_endpoint(self, name, handler):
        self.endpoints[name] = handler

    def print_exception(self, e=None):
        if e is None: e = sys.exception()
        traceback.print_exception(e, file=self.stderr)

    def db(self, env):
        if (db := env.get('tdoc.db')) is not None: return db
        db = env['tdoc.db'] = self.pool.get()
        return db

    def authenticate(self, env):
        user = None
        if token := wsgi.authorization(env):
            with self.db(env) as db:
                user = db.tokens.authenticate(token)
            if user is None: raise wsgi.Error(HTTPStatus.UNAUTHORIZED)
        env['tdoc.user'] = user

    def user(self, env, anon=True):
        user = env['tdoc.user']
        if user is None and not anon: raise wsgi.Error(HTTPStatus.UNAUTHORIZED)
        return user

    def member_of(self, env, db, group):
        return db.users.member_of(wsgi.origin(env), self.user(env), group)

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

    def handle_health(self, env, respond):
        wsgi.method(env, HTTPMethod.GET)
        if env['PATH_INFO']: raise wsgi.Error(HTTPStatus.NOT_FOUND)
        return wsgi.respond_json(respond, {})

    def handle_log(self, env, respond):
        wsgi.method(env, HTTPMethod.POST)
        if env['PATH_INFO']: raise wsgi.Error(HTTPStatus.NOT_FOUND)
        self.check_acl(env, 'log')
        req = wsgi.read_json(env)
        with self.db(env) as db:
            db.execute("""
                insert into log (time, location, session, data)
                    values (?, ?, ?, json(?))
            """, (int(req.get('time', time.time_ns() // 1_000_000)),
                  req['location'], req.get('session'),
                  wsgi.to_json(req['data'])))
        return wsgi.respond_json(respond, {})

    def handle_poll(self, env, respond):
        wsgi.method(env, HTTPMethod.POST)
        if env['PATH_INFO']: raise wsgi.Error(HTTPStatus.NOT_FOUND)
        origin = wsgi.origin(env)
        req = wsgi.read_json(env)
        with self.db(env) as db:
            if polls := req.get('open'):
                check(self.member_of(env, db, 'polls:control'))
                for poll in polls:
                    mode = arg(poll, 'mode', lambda v: v in ('single', 'multi'))
                    expires = None if (exp := poll.get('exp')) is None \
                              else time.time_ns() + exp * 1_000_000
                    db.polls.open(origin, arg(poll, 'id'), mode,
                                  arg(poll, 'answers'), expires)
            if ids := req.get('close'):
                check(self.member_of(env, db, 'polls:control'))
                db.polls.close(origin, ids)
            if ids := req.get('results'):
                check(self.member_of(env, db, 'polls:control'))
                db.polls.results(origin, ids, arg(req, 'value'))
            if ids := req.get('solutions'):
                check(self.member_of(env, db, 'polls:control'))
                db.polls.solutions(origin, ids, arg(req, 'value'))
            if ids := req.get('clear'):
                check(self.member_of(env, db, 'polls:control'))
                db.polls.clear(origin, ids)
            if 'vote' in req:
                if not db.polls.vote(
                        origin, *args(req, 'id', 'voter', 'answer', 'vote')):
                    raise wsgi.Error(HTTPStatus.FORBIDDEN)
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
            db.solutions.set_show(origin, page, show)
        return wsgi.respond_json(respond, {})

    def handle_user(self, env, respond):
        wsgi.method(env, HTTPMethod.POST)
        if env['PATH_INFO']: raise wsgi.Error(HTTPStatus.NOT_FOUND)
        user = self.user(env, anon=False)
        with self.db(env) as db:
            info = db.users.info(wsgi.origin(env), user)
        return wsgi.respond_json(respond, info)


class EventsApi:
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
            'poll': PollObservable,
            'poll/votes': PollVotesObservable,
        }
        self.watchers = {}
        self._stop_watchers = False
        self._last_watcher = None

    def stop(self):
        with self.lock:
            self._stop_watchers = True
            for w in self.watchers.values(): w.stop()

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

    def watchers_must_stop(self):
        with self.lock: return self._stop_watchers

    @property
    def last_watcher(self):
        with self.lock: return self._last_watcher

    @contextlib.contextmanager
    def watcher(self):
        with Watcher(self.watchers_must_stop) as watcher:
            sid = secrets.token_urlsafe(8)
            with self.lock:
                if self._stop_watchers:
                    raise wsgi.Error(HTTPStatus.REQUEST_TIMEOUT)
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
    def __init__(self, must_stop):
        self.must_stop = must_stop
        self.queue = queue.Queue()
        self.lock = threading.Lock()
        self.watches = {}

    def stop(self):
        # TODO(py-3.13): Remove must_stop and this conditional
        if hasattr(self.queue, 'shutdown'):
            self.queue.shutdown(True)

    def send(self, wid, msg):
        self.queue.put((wid, msg))

    def __iter__(self):
        while not self.must_stop():
            try:
                wid, msg = self.queue.get(timeout=1)
                yield b'{"wid":%d,"data":' % wid
                yield msg
                yield b'}\n'
            except queue.Empty:
                yield b'\n'
            except Shutdown:
                return

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


def limit_interval(interval, burst=1):
    interval = int(interval * 1_000_000_000)
    count, prev = 0, time.monotonic_ns()

    def limit():
        nonlocal count, prev
        now = time.monotonic_ns()
        count = count - min(count, (now - prev) // interval) + 1
        if count < burst:
            prev = now
            return 0
        count = burst
        prev = now + interval
        return interval / 1_000_000_000

    return limit


class DbObservable(DynObservable):
    def __init__(self, req, events, data=None, limit=None):
        super().__init__(req, events)
        self._data = data
        self._limit = limit if limit is not None else limit_interval(1, burst=4)
        self._stop = False
        self._poller = threading.Thread(target=self.poll)
        self._poller.start()

    def _msg(self):
        return wsgi.to_json(self._data).encode('utf-8')

    def send_initial_locked(self, watcher, wid):
        if self._data is not None: watcher.send(wid, self._msg())

    @property
    def stopping(self):
        with self.lock: return self._stop

    def stop_locked(self):
        self._stop = True
        self.lock.notify()

    def wake_keys(self, db): return None

    def poll(self):
        try:
            store = self.events.api.store
            with contextlib.closing(store.connect(params='mode=ro')) as db, \
                    store.waker(self.lock, self.wake_keys(db), db,
                                self._limit) as waker:
                while True:
                    queried = False
                    try:
                        with db: data, until = self.query(db)
                        queried = True
                    except Exception:
                        self.print_exception()
                    with self.lock:
                        if queried and data != self._data:
                            self._data = data
                            self.send_locked(self._msg())
                        waker.wait(lambda: self._stop, until)
                        if self._stop: break
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
        super().__init__(req, events)

    def wake_keys(self, db):
        return [db.solutions.show_key(self._origin, self._page)]

    def query(self, db):
        return {'show': db.solutions.get_show(self._origin, self._page)}, None


class PollObservable(DbObservable):
    def __init__(self, req, events, env):
        self._origin = wsgi.origin(env)
        self._id = arg(req, 'id')
        super().__init__(req, events)

    def wake_keys(self, db):
        return [db.polls.poll_key(self._origin, self._id)]

    def query(self, db):
        data = db.polls.poll_data(self._origin, self._id)
        if (exp := data.pop('exp')) is not None and exp <= time.time_ns():
            exp = None
        return data, exp


class PollVotesObservable(DbObservable):
    def __init__(self, req, events, env):
        self._origin = wsgi.origin(env)
        self._voter, self._ids = args(req, 'voter', 'ids')
        self._ids.sort()
        super().__init__(req, events)

    def wake_keys(self, db):
        return [db.polls.voter_key(self._origin, poll, self._voter)
                for poll in self._ids]

    def query(self, db):
        return db.polls.votes_data(self._origin, self._voter, self._ids), None
