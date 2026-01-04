# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import base64
import contextlib
import functools
import hashlib
from http import HTTPMethod, HTTPStatus
import json
import queue
import secrets
import threading
import time
import traceback
from urllib import parse, request

import jwt

from . import database, logs, store, wsgi

log = logs.logger(__name__)
missing = object()
# TODO(py-3.13): Remove ShutDown
ShutDown = getattr(queue, 'ShutDown', queue.Empty)


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


wsgi.Request.attr('user')
wsgi.Request.attr('read_db')
wsgi.Request.attr('write_db', cache=False)


class Api(wsgi.Dispatcher):
    def __init__(self, *, config, store):
        super().__init__()
        self.config = config
        self.store = store
        self.cache = wsgi.HttpCache()
        self._read_db_pool = store.pool(mode='ro')
        self._write_db_lock = threading.Lock()
        self._write_db = store.connect(mode='rw')
        self.events = self.add_endpoint('events', EventsApi(self))
        self.auth = self.add_endpoint(
            'auth', OidcAuthApi(self, config.sub('oidc')))

    def __enter__(self): return self

    def __exit__(self, typ, value, tb):
        log.debug("Api: stopping")
        self.events.stop()
        log.debug("Api: done")

    @contextlib.contextmanager
    def write_db(self):
        with self._write_db_lock, self._write_db as db:
            yield db

    def member_of(self, wr, db, group):
        return db.users.member_of(wr.required_origin, wr.user, group)

    def pre_request(self, wr):
        wr.attr_handlers('read_db', fget=self._read_db_pool.get,
                         fdel=self._read_db_pool.release)
        wr.attr_handlers('write_db', fget=self.write_db)
        if token := wr.token:
            try:
                with wr.read_db as db: user = db.tokens.authenticate(token)
            except Exception as e:
                log.exception("Authentication failure", event='auth:error')
                raise wsgi.Error(HTTPStatus.UNAUTHORIZED)
            if user is None: raise wsgi.Error(HTTPStatus.UNAUTHORIZED)
            wr.user = user

    def handle_request(self, handler, wr):
        try:
            yield from handler(wr.env, wr.respond, wr)
        except database.client_errors:
            log.exception("Store client error", exc_limit=-1, exc_chain=False,
                          event='store:error:client')
            raise wsgi.Error(HTTPStatus.BAD_REQUEST)
        except database.Error as e:
            log.exception("Store error", exc_limit=-1, exc_chain=False,
                          event='store:error')
            raise wsgi.Error(HTTPStatus.FORBIDDEN,
                             e.args[0] if e.args else None)

    def post_request(self, wr):
        del wr.read_db

    @wsgi.json_endpoint('health', methods=(HTTPMethod.GET,))
    def handle_health(self, wr, req):
        return {}

    @wsgi.json_endpoint('poll')
    def handle_poll(self, wr, req):
        origin = wr.required_origin
        with wr.write_db as db:
            if polls := req.get('open'):
                check(self.member_of(wr, db, 'polls:control'))
                for poll in polls:
                    mode = arg(poll, 'mode', lambda v: v in ('single', 'multi'))
                    expires = None if (exp := poll.get('exp')) is None \
                              else time.time_ns() + exp * 1_000_000
                    db.polls.open(origin, arg(poll, 'id'), mode,
                                  arg(poll, 'answers'), expires)
            if ids := req.get('close'):
                check(self.member_of(wr, db, 'polls:control'))
                db.polls.close(origin, ids)
            if ids := req.get('results'):
                check(self.member_of(wr, db, 'polls:control'))
                db.polls.results(origin, ids, arg(req, 'value'))
            if ids := req.get('solutions'):
                check(self.member_of(wr, db, 'polls:control'))
                db.polls.solutions(origin, ids, arg(req, 'value'))
            if ids := req.get('clear'):
                check(self.member_of(wr, db, 'polls:control'))
                db.polls.clear(origin, ids)
            if 'vote' in req:
                db.polls.vote(origin, *args(req, 'id', 'voter', 'answer',
                                            'vote'))
        return {}

    @wsgi.json_endpoint('solutions')
    def handle_solutions(self, wr, req):
        origin = wr.required_origin
        page = arg(req, 'page')
        show = arg(req, 'show', lambda v: v in ('show', 'hide'))
        with wr.write_db as db:
            check(self.member_of(wr, db, 'solutions:write'))
            db.solutions.set_show(origin, page, show)
        return {}

    @wsgi.json_endpoint('user', require_authn=True)
    def handle_user(self, wr, req):
        origin = wr.required_origin
        with wr.read_db as db: return db.users.info(origin, wr.user)


class EventsApi(wsgi.Dispatcher):
    def __init__(self, api):
        super().__init__()
        self.api = api
        self.lock = threading.Lock()
        self.observables = {}
        self.watchers = {}
        self._stop_watchers = False
        self._last_watcher = None

    def stop(self):
        with self.lock:
            self._stop_watchers = True
            for w in self.watchers.values(): w.stop()

    def add_observable(self, obs):
        with self.lock: self.observables[obs.key] = obs

    def remove_observable(self, obs):
        with self.lock: self.observables.pop(obs.key, None)

    def find_observable(self, req, wr):
        key = Observable.hash(req)
        with self.lock:
            if (obs := self.observables.get(key)) is not None:
                if not obs.stopping: return obs
            if (cls := DynObservable.lookup(req['name'])) is not None:
                obs = cls(req, self, wr)
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

    @wsgi.endpoint('watch', methods=(HTTPMethod.POST,))
    def handle_watch(self, wr):
        req = wr.json
        with self.watcher() as watcher:
            wr.respond(wsgi.http_status(HTTPStatus.OK), [
                ('Content-Type', 'text/plain; charset=utf-8'),
                ('Cache-Control', 'no-store'),
            ])
            resp = {'sid': watcher.sid}
            if failed := self.watch(watcher, req.get('add', []), wr):
                resp['failed'] = failed
            yield wsgi.to_json(resp).encode('utf-8') + b'\n'
            yield from watcher

    @wsgi.json_endpoint('sub')
    def handle_sub(self, wr, req):
        sid = arg(req, 'sid')
        with self.lock: watcher = self.watchers.get(sid)
        if watcher is None:
            raise wsgi.Error(HTTPStatus.BAD_REQUEST, "Unknown stream ID")
        resp = {}
        for wid in req.get('remove', []): watcher.unwatch(wid)
        if failed := self.watch(watcher, req.get('add', []), wr):
            resp['failed'] = failed
        return resp

    def watch(self, watcher, adds, wr):
        failed = []
        for add in adds:
            if (wid := add.get('wid')) is None: continue
            try:
                watcher.watch(wid, self.find_observable(add['req'], wr))
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
            except ShutDown:
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
        return hashlib.sha256(wsgi.to_json_sorted(req).encode('utf-8')).digest()

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
    _observables = {}

    def __init_subclass__(cls, /, **kwargs):
        if (name := kwargs.pop('name', None)) is not None:
            DynObservable._observables[name] = cls
        super().__init_subclass__(**kwargs)

    @classmethod
    def lookup(cls, name): return cls._observables.get(name)

    def __init__(self, req, events):
        super().__init__(req)
        self.events = events

    def unwatch(self, watcher, wid):
        super().unwatch(watcher, wid)
        if self.stopping: self.remove()

    def remove(self):
        self.events.remove_observable(self)


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
        self._poller = threading.Thread(target=self.poll,
                                        name=f'obs:{self.key.hex()}')
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
        log.debug("Start: %(cls)s", cls=self.__class__.__name__,
                  event='obs:start')
        try:
            store = self.events.api.store
            with contextlib.closing(store.connect(mode='ro')) as db, \
                    store.waker(self.lock, self.wake_keys(db), db,
                                self._limit) as waker:
                while True:
                    queried = False
                    try:
                        with db: data, until = self.query(db)
                        queried = True
                    except Exception:
                        log.exception("Exception")
                    with self.lock:
                        if queried and data != self._data:
                            self._data = data
                            self.send_locked(self._msg())
                        waker.wait(lambda: self._stop, until)
                        if self._stop: break
        except Exception:
            with self.lock: self._stop = True
            self.remove()
            log.exception("Uncaught exception", event='obs:exception')
        finally:
            log.debug("Done", event='obs:end')

    def query(self, db):
        raise NotImplementedError()


class SolutionsObservable(DbObservable, name='solutions'):
    def __init__(self, req, events, wr):
        self._origin = wr.required_origin
        self._page = arg(req, 'page')
        super().__init__(req, events)

    def wake_keys(self, db):
        return [db.solutions.show_key(self._origin, self._page)]

    def query(self, db):
        return {'show': db.solutions.get_show(self._origin, self._page)}, None


class PollObservable(DbObservable, name='poll'):
    def __init__(self, req, events, wr):
        self._origin = wr.required_origin
        self._id = arg(req, 'id')
        super().__init__(req, events)

    def wake_keys(self, db):
        return [db.polls.poll_key(self._origin, self._id)]

    def query(self, db):
        data = db.polls.poll_data(self._origin, self._id)
        if (exp := data.pop('exp')) is not None and exp <= time.time_ns():
            exp = None
        return data, exp


class PollVotesObservable(DbObservable, name='poll/votes'):
    def __init__(self, req, events, wr):
        self._origin = wr.required_origin
        self._voter, self._ids = args(req, 'voter', 'ids')
        self._ids.sort()
        super().__init__(req, events)

    def wake_keys(self, db):
        return [db.polls.voter_key(self._origin, poll, self._voter)
                for poll in self._ids]

    def query(self, db):
        return db.polls.votes_data(self._origin, self._voter, self._ids), None


class OidcAuthApi(wsgi.Dispatcher):
    def __init__(self, api, config):
        super().__init__()
        self.api = api
        self.config = config

    @functools.cached_property
    def issuers(self):
        issuers = self.config.get('issuers', [])
        return {self.discovery(i)['issuer']: i
                for i in issuers if i.get('enabled', True)}

    def issuer(self, issuer):
        if (info := self.issuers.get(issuer)) is None:
            raise wsgi.Error(HTTPStatus.BAD_REQUEST)
        return info, self.discovery(info)

    def discovery(self, info):
        return json.loads(self.api.cache.get(info['discovery'], timeout=10))

    @wsgi.json_endpoint('info')
    def handle_info(self, wr, req):
        issuers = self.issuers
        resp = {'issuers': [{'issuer': i, 'label': info.get('label', i)}
                            for i, info in issuers.items()]}
        if wr.user is not None:
            iids = [(i, self.discovery(i)) for i in issuers.values()]
            resp['logins'] = logins = []
            with wr.read_db as db:
                for id_token, updated in db.oidc.logins(wr.user):
                    if (info := issuers.get(id_token['iss'])) is None: continue
                    logins.append({
                        'email': id_token['email'],
                        'issuer': info['label'],
                        'updated': updated.timestamp(),
                        'iss': id_token['iss'],
                        'sub': id_token['sub'],
                    })
            logins.sort(key=lambda i: (i['email'], i['issuer']))
        return resp

    @wsgi.json_endpoint('update', require_authn=True)
    def handle_update(self, wr, req):
        if remove := req.get('remove'):
            iss, sub = args(remove, 'iss', 'sub')
            with wr.write_db as db:
                db.oidc.remove_login(wr.user, iss, sub)
                count = sum(1 for id_token, _ in db.oidc.logins(wr.user)
                            if id_token['iss'] in self.issuers)
                if count < 1:
                    raise wsgi.Error(HTTPStatus.FORBIDDEN,
                                     "At least one login is required")
        return {}

    def get_key(self, disc, token):
        header = jwt.get_unverified_header(token)
        alg, kid = header['alg'], header['kid']
        if alg not in self.config.get('token_algorithms', ()):
            raise wsgi.Error(HTTPStatus.FORBIDDEN,
                             f"Unsupported signing algorithm: {alg}")
        resp = json.loads(self.api.cache.get(disc['jwks_uri'], timeout=10))
        for key in resp['keys']:
            if key['kid'] == kid and key['alg'] == alg: return jwt.PyJWK(key)
        raise wsgi.Error(HTTPStatus.FORBIDDEN, "No verification key found")

    def verify_id_token(self, disc, token, audience, nonce):
        key = self.get_key(disc, token)
        try:
            info = jwt.decode(token, key, issuer=disc['issuer'],
                              audience=audience, options={'strict_aud': True})
        except jwt.exceptions.InvalidTokenError as e:
            raise wsgi.Error(HTTPStatus.FORBIDDEN, str(e))
        if info['nonce'] != nonce:
            raise wsgi.Error(HTTPStatus.FORBIDDEN, "Nonce mismatch")
        return info

    @wsgi.json_endpoint('login')
    def handle_login(self, wr, req):
        token = wr.token

        # Handle "log in as" in dev mode.
        if wr.dev and (ruser := req.get('user')):
            with wr.write_db as db:
                try:
                    uid = db.users.uid(ruser)
                except Exception as e:
                    raise wsgi.Error(HTTPStatus.BAD_REQUEST, str(e))
                if (token := db.tokens.find(uid)) is None:
                    token, = db.tokens.create([uid])
            return {'token': token}

        # Handle OIDC login.
        issuer, cnonce, href = args(req, 'issuer', 'cnonce', 'href')
        href_origin = parse.urlunparse(parse.urlparse(href)._replace(
            path='', params='', query='', fragment=''))
        if href_origin != wr.env.get('HTTP_ORIGIN'):
            raise wsgi.Error(HTTPStatus.BAD_REQUEST, "Origin mismatch: href")
        info, disc = self.issuer(issuer)
        state, nonce = secrets.token_urlsafe(), secrets.token_urlsafe()
        # Create the PKCE challenge as per RFC7636
        # <https://datatracker.ietf.org/doc/html/rfc7636>.
        verifier = secrets.token_urlsafe(32)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(
            verifier.encode('ascii')).digest()).decode('ascii').rstrip('=')
        with wr.write_db as db:
            db.oidc.create_state(state, {
                'issuer': issuer, 'cnonce': cnonce, 'nonce': nonce,
                'verifier': verifier, 'user': wr.user, 'token': token,
                'href': href,
            })
        auth = wr.uri().rsplit('/', 1)[0]
        parts = parse.urlparse(disc['authorization_endpoint'])
        parts = parts._replace(query=parse.urlencode({
            'client_id': info['client_id'],
            'code_challenge': challenge,
            'code_challenge_method': 'S256',
            'nonce': nonce,
            'redirect_uri': f'{auth}/redirect',
            'response_type': 'code',
            'scope': 'openid profile email',
            'state': state,
            **({'prompt': 'select_account'} if wr.user is not None else {}),
        }))
        return {'redirect': parse.urlunparse(parts)}

    @wsgi.endpoint('redirect', methods=(HTTPMethod.GET,), log_query=False)
    def handle_redirect(self, wr):
        qs = parse.parse_qs(wr.query)
        href = None
        with wr.write_db as db:
            if (state := qs.get('state')) is not None:
                data = db.oidc.state(state[0])
            if data is None:
                raise wsgi.Error(HTTPStatus.BAD_REQUEST, "Bad state")
            href = data['href']
            try:
                params = self._handle_redirect(wr, qs, db, data)
            except Exception as e:
                params = {'auth_error': str(e)}
        parts = parse.urlparse(href)
        parts = parts._replace(fragment='?' + parse.urlencode(params))
        return wr.redirect(parse.urlunparse(parts))

    def _handle_redirect(self, wr, qs, db, state):
        if (err := self.get_error(qs)) is not None:
            raise Exception(err or "Unknown ID issuer error")
        if (code := qs.get('code')) is None: raise Exception("Missing code")

        # Get the ID token from the issuer.
        info, disc = self.issuer(state['issuer'])
        data = parse.urlencode({
            'code': code[0],
            'code_verifier': state['verifier'],
            'client_id': info['client_id'],
            'client_secret': info['client_secret'],
            'redirect_uri': wr.uri(include_query=False),
            'grant_type': 'authorization_code',
        }).encode('utf-8')
        req = request.Request(disc['token_endpoint'], data, headers={
            'Content-Type': 'application/x-www-form-urlencoded',
        })
        with request.urlopen(req, timeout=10) as f: resp = json.load(f)

        # Validate the ID token.
        if (id_token := resp.get('id_token')) is None:
            raise Exception("No id_token returned")
        id_token = self.verify_id_token(disc, id_token, info['client_id'],
                                        state['nonce'])

        # Find the user for the returned identity, if it exists.
        user, _, _ = db.oidc.user(id_token)

        # If the user is logged in, we're adding a new identity or updating an
        # existing one. Check that the identity isn't associated with another
        # user, and remove the existing token, as a new one will be generated.
        if (state_user := state.get('user')) is not None:
            if user is not None and user != state_user:
                raise Exception(
                    "This identity is already associated with another user")
            user = state_user
            if (t := state.get('token')) is not None: db.tokens.remove([t])

        # If the user isn't logged in, and the identity's domain is allowlisted,
        # create a new user.
        if user is None and (hd := id_token.get('hd')) is not None \
                and hd in info.get('create_users_for_domains', []):
            if (email := id_token.get('email')) is None:
                raise Exception(
                    "This identity doesn't specify an email address")
            if not id_token.get('email_verified', False):
                raise Exception(
                    "This identity's email address hasn't been verified")
            user, = db.users.create([email])

        # If we've found or created a user, add or update the identity and
        # generate a new token.
        if user is None: raise Exception("Not authorized")
        db.oidc.add_login(user, id_token)
        token, = db.tokens.create([user])
        return {'token': token, 'cnonce': state['cnonce']}

    def get_error(self, qs):
        if (err := qs.get('error')) is None: return
        err = err[0]
        if (desc := qs.get('error_description')) is not None:
            err = f"{err}: {desc[0]}"
        return err

    @wsgi.json_endpoint('logout', require_authn=True)
    def handle_logout(self, wr, req):
        token = wr.token
        with wr.write_db as db:
            # Remove the token if the user has at least one login.
            count = sum(1 for id_token, _ in db.oidc.logins(wr.user)
                        if id_token['iss'] in self.issuers)
            if count > 0: db.tokens.remove([token])
        return {}
