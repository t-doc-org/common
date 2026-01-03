# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import contextlib
import datetime
import json
import re
import sqlite3
import textwrap
import threading
import time


def to_datetime(nsec):
    if nsec is None: return
    return datetime.datetime.fromtimestamp(nsec / 1e9, datetime.UTC)


def to_nsec(dt, default=None):
    if dt is None: return default
    return int(dt.timestamp() * 1e9)


to_json = json.JSONEncoder(separators=(',', ':')).encode


def placeholders(args): return ', '.join('?' * len(args))


class Error(Exception): pass
client_errors = (sqlite3.DataError, sqlite3.IntegrityError)


class Connection(sqlite3.Connection):
    def __enter__(self):
        db = super().__enter__()
        if self.autocommit == sqlite3.LEGACY_TRANSACTION_CONTROL:
            try:
                db.execute(f"begin {db.isolation_level or ''}")
            except BaseException:
                db.rollback()
                raise
        return db

    def executescript(self, *args, **kwargs):
        # executescript() executes a COMMIT first if autocommit is
        # LEGACY_TRANSACTION_CONTROL and there is a pending transaction.
        raise NotImplementedError("executescript")

    def create(self, sql, params=()):
        sql = textwrap.dedent(sql.lstrip('\n').rstrip())
        if not sql.endswith(';'): sql += ';'
        return self.execute(sql, params)

    def row(self, sql, params=(), default=None):
        for row in self.execute(sql, params): return row
        return default

    def meta(self, key, default=None):
        for value, in self.execute("select value from meta where key = ?",
                                   (key,)):
            return value
        return default

    @property
    def dev(self):
        return bool(self.meta('dev', False))

    def check_foreign_keys(self):
        violations = []
        cursor = self.cursor()
        cursor.row_factory = sqlite3.Row
        for r, i, t, c in self.execute("pragma foreign_key_check"):
            rcs, tcs = [], []
            for row in cursor.execute(f"pragma foreign_key_list({r})"):
                if row['id'] != c: continue
                rcs.append(row['from'])
                tcs.append(row['to'])
            rowid = f"[{i}]" if i is not None else ''
            rcs = ", ".join(rcs)
            tcs = ", ".join(tcs)
            violations.append(f"{r}{rowid} ({rcs}) references {t} ({tcs})")
        if violations:
            raise Exception(
                f"Foreign key check failed:\n  {"\n  ".join(violations)}")

    def check_integrity(self):
        issues = [i for i, in self.execute("PRAGMA integrity_check")]
        if issues == ['ok']: return
        raise Exception(f"Integrity check failed:\n  {"\n  ".join(issues)}")


class ConnNamespace:
    def __init__(self, db): self.db = db
    def __getattr__(self, name): return getattr(self.db, name)


class ConnectionPool:
    def __init__(self, database, size=0, **kwargs):
        self.database = database
        self.size = size
        self.kwargs = kwargs
        self.lock = threading.Lock()
        self.connections = []

    def get(self):
        with self.lock:
            if self.connections: return self.connections.pop()
        return self.database.connect(**self.kwargs)

    def release(self, db):
        with self.lock:
            if self.size <= 0 or len(self.connections) < self.size:
                db.rollback()
                self.connections.append(db)
            else:
                db.close()


class Database:
    Connection = Connection
    WriteConnection = Connection

    def __init__(self, config, *, mem_name=None):
        self.config = config
        self.mem_name = mem_name
        self.path = config.path('path')
        if self.path is None and not mem_name:
            raise Exception("No database path defined")
        self.timeout = config.get('timeout', 5)
        self.pragma = config.get('pragma', {}).copy()
        # The defaults are based on <https://kerkour.com/sqlite-for-servers>.
        self.pragma.setdefault('synchronous', 'normal')
        self.pragma.setdefault('cache_size', -250000)
        self.pragma.setdefault('temp_store', 'memory')
        self.write_isolation_level = config.get('write_isolation_level',
                                                'immediate')
        self.mem_db = None

    @property
    def exists(self): return self.path is not None and self.path.exists()

    def version(self, db):
        version = db.meta('version')
        latest = max(v for v, _ in self.versions())
        return version, latest

    def check_version(self, on_upgrade=None):
        if self.path is None: return
        if not self.exists:
            if on_upgrade is not None and on_upgrade(self, None, None, None):
                return
            raise Exception(f"Database not found: {self.path}")
        with contextlib.closing(self.connect(mode='rw')) as db:
            with db: version, latest = self.version(db)
            if version == latest: return
            if on_upgrade is not None and on_upgrade(self, db, version, latest):
                return
        raise Exception("Database version mismatch "
                        f"(current: {version}, want: {latest}): {self.path}")

    def __enter__(self):
        if self.path is None:
            self.mem_db = self.connect(mode='ro')
            self.create(dev=True)  # Create in-memory DB
        return self

    def __exit__(self, typ, value, tb):
        if self.mem_db is not None:
            self.mem_db.close()
            self.mem_db = None

    def connect(self, *, mode, path=False, isolation_level=None):
        if path is False: path = self.path
        if isolation_level is None: isolation_level = self.write_isolation_level
        uri = f'{path.as_uri()}?mode={mode}' if path is not None \
              else f'file:{self.mem_name}?mode=memory&cache=shared'
        factory = self.WriteConnection if 'rw' in mode else self.Connection
        # Some pragmas cannot be used or are ineffective within a transaction,
        # and autocommit=False always has a transaction open. Open the
        # connection with autocommit=True, then switch after configuration.
        db = sqlite3.connect(uri, uri=True, timeout=self.timeout,
                             factory=factory, autocommit=True,
                             isolation_level=isolation_level,
                             check_same_thread=False)
        db.database = self
        db.execute("pragma journal_mode = wal")
        db.execute("pragma foreign_keys = on")
        for k, v in self.pragma.items(): db.execute(f"pragma {k} = {v}")
        db.autocommit = sqlite3.LEGACY_TRANSACTION_CONTROL \
                        if 'rw' in mode and db.isolation_level \
                        else False
        db.create_function(
            'regexp', 2, lambda pat, v: re.search(pat, v) is not None,
            deterministic=True)
        return db

    def pool(self, **kwargs):
        kwargs.setdefault('size', self.config.get('pool_size', 16))
        return ConnectionPool(self, **kwargs)

    def backup(self, db, dest):
        if dest.exists(): raise Exception("Backup destination already exists")
        with contextlib.closing(self.connect(path=dest, mode='rwc')) as ddb:
            db.backup(ddb)

    def create(self, version=None, dev=False):
        self._version_valid(version)
        if self.exists: raise Exception(f"Database already exists: {self.path}")
        with contextlib.closing(
                self.connect(mode='rwc', isolation_level='immediate')) as db:
            db.execute("pragma foreign_keys = off")
            with db:
                to_version = self._upgrade(db, from_version=0,
                                           to_version=version, dev=dev)
            return to_version

    def upgrade(self, version=None, on_version=None):
        self._version_valid(version)
        with contextlib.closing(
                self.connect(mode='rw', isolation_level='immediate')) as db:
            db.execute("pragma foreign_keys = off")
            with db:
                from_version = db.meta('version')
                to_version = self._upgrade(db, from_version=from_version,
                                           to_version=version, dev=db.dev,
                                           on_version=on_version)
        return from_version, to_version

    def _version_valid(self, version):
        if version is None: return
        for v, _ in self.versions():
            if v == version: return
        raise Exception(f"Invalid database version: {version}")

    def _upgrade(self, db, from_version, to_version, dev, on_version=None):
        now = time.time_ns()
        version = from_version
        for v, fn in self.versions(from_version + 1):
            if to_version is not None and v > to_version: break
            if on_version is not None: on_version(v)
            # For complex schema upgrades, follow:
            # https://sqlite.org/lang_altertable.html#making_other_kinds_of_table_schema_changes
            fn(db, dev, now)
            db.execute("""
                insert or replace into meta (key, value) values ('version', ?)
            """, (v,))
            db.check_foreign_keys()
            db.check_integrity()
            version = v
        return version

    def versions(self, version=1):
        while True:
            if (fn := getattr(self, f'version_{version}', None)) is None:
                return
            yield version, fn
            version += 1

    def version_1(self, db, dev, now):
        db.create("""
            create table meta (
                key text primary key,
                value any
            ) strict, without rowid
        """)
