# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import contextlib
from http import HTTPMethod, HTTPStatus
import json
import pathlib
import sqlite3
import threading
import time
from wsgiref import util

from . import wsgi


class ThreadLocal(threading.local):
    def __init__(self, **kwargs):
        super().__init__()
        self.__dict__.update(kwargs)


class Store:
    thread_local = ThreadLocal(db=None)

    def __init__(self, path):
        self.path = pathlib.Path(path).resolve()

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

    def create(self, open_acl=False):
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

    def check_acl(self, db, token, perm):
        for perms, in db.execute(
                "select perms from auth where token in (?, '*')", (token,)):
            perms = perms.split(',')
            if perm in perms or '*' in perms: return True
        return False

    def __call__(self, env, respond):
        cmd = util.shift_path_info(env)
        if (handler := getattr(self, f'handle_{cmd}', None)) is None:
            return wsgi.error(respond, HTTPStatus.NOT_FOUND)

        # Parse the Authorization header if present.
        token = ''
        if (auth := env.get('HTTP_AUTHORIZATION')) is not None:
            parts = auth.split()
            if len(parts) != 2 or parts[0].lower() != 'bearer':
                return wsgi.error(respond, HTTPStatus.BAD_REQUEST)
            token = parts[1]

        try:
            with self.transaction(env) as db:
                if not self.check_acl(db, token, cmd):
                    return wsgi.error(respond, HTTPStatus.UNAUTHORIZED)
            return handler(env, respond)
        finally:
            if (db := self.thread_local.db) is not None \
                     and not env.get('tdoc.db_cache_per_thread'):
                self.thread_local.db = None
                db.close()

    def handle_log(self, env, respond):
        method, err = wsgi.method(env, respond, HTTPMethod.POST)
        if err is not None: return err
        if env['PATH_INFO']: return wsgi.error(respond, HTTPStatus.NOT_FOUND)
        with self.transaction(env) as db:
            try:
                req = wsgi.read_json(env)
            except Exception as e:
                return wsgi.error(respond, HTTPStatus.BAD_REQUEST)
            db.execute("""
                insert into log (time, location, session, data)
                    values (?, ?, ?, json(?));
            """, (int(req.get('time', time.time_ns() // 1000000)),
                  req['location'], req.get('session'),
                  json.dumps(req['data'], separators=(',', ':'))))
        return wsgi.respond_json(respond, {})
