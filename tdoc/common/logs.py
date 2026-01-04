# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

from collections import abc
import contextlib
import contextvars
import datetime
import functools
import gzip
import json
import logging
from logging import handlers
import os
import queue
import shutil
import threading
import traceback

from . import database, config as _config

# TODO: Allow per-handler filters
# TODO: Allow unset LogRecord fields in formats

globals().update(logging.getLevelNamesMapping())


class Logger(logging.Logger):
    def _log(self, level, msg, args, exc_info=None, extra=None,
             stack_info=False, stacklevel=1, **kwargs):
        if kwargs: args = (kwargs,)
        super()._log(level, msg, args, exc_info=exc_info, extra=extra,
                     stack_info=stack_info, stacklevel=stacklevel + 1)

logging.setLoggerClass(Logger)
logger = logging.getLogger
log = logger(__name__)

ctx = contextvars.ContextVar('ctx', default=None)

def push_ctx(fn, replace=False):
    if not replace and ctx.get() is not None: return
    return ctx.set(fn())


def pop_ctx(token):
    if token is not None: ctx.reset(token)


class CtxFilter(logging.Filter):
    def filter(self, rec):
        if not hasattr(rec, 'ctx'):
            rec.ilevel = rec.levelname[0]
            if (v := ctx.get()) is None: v = threading.current_thread().name
            rec.ctx = v[:20]
        return True


def to_level(v):
    try: return int(v)
    except ValueError: pass
    ln = logging.getLevelName(v.upper())
    if isinstance(ln, int): return ln
    raise ValueError(f"Invalid level: {v}")


def get_kwarg(rec, name, default=None):
    if (args := rec.args) and isinstance(args, abc.Mapping):
        return args.get(name, default)
    return default


def normalize_record(rec):
    if not hasattr(rec, 'message'): rec.message = rec.getMessage()
    if rec.exc_info and not rec.exc_text:
        parts = traceback.format_exception(
            *rec.exc_info, limit=get_kwarg(rec, 'exc_limit', None),
            chain=get_kwarg(rec, 'exc_chain', True))
        if parts and (last := parts[-1])[-1:] == "\n": parts[-1] = last[:-1]
        rec.exc_text = "".join(parts)
        rec.exc_info = None


class Formatter(logging.Formatter):
    def __init__(self, *args, utc=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.utc = utc

    def format(self, rec):
        normalize_record(rec)
        return super().format(rec).replace("\n", "\n  ")

    def formatTime(self, rec, datefmt=None):
        dt = datetime.datetime.fromtimestamp(rec.created, datetime.UTC)
        if not self.utc:
            return dt.astimezone().isoformat(timespec='microseconds')
        return dt.replace(tzinfo=None).isoformat(timespec='microseconds') + 'Z'


class QueueHandler(handlers.QueueHandler):
    def prepare(self, rec): return rec


def compress(src, dst):
    with open(src, 'rb') as inp, gzip.open(dst, 'wb') as out:
        shutil.copyfileobj(inp, out)
    os.remove(src)


default_stream_format = '{ilevel} [{ctx:20}] {message}'
default_file_format = '{asctime} {ilevel} [{ctx:20}] [{module}] {message}'

class DisableHandler(Exception): pass


@contextlib.contextmanager
def configure(config=None, stderr=None, level=WARNING, stream=False,
              raise_exc=False, on_upgrade=None):
    if config is None: config = _config.Config({})
    transport = config.get('transport', 'queue')

    logging.raiseExceptions = raise_exc
    logging.lastResort = logging.NullHandler()

    root = logging.getLogger()
    root.setLevel(config.get('level', level))
    ctx_filter = CtxFilter()

    with contextlib.ExitStack() as stack:
        stack.callback(logging.shutdown)
        hs = []

        if stderr is not None and \
                (c := config.sub('stream')).get('enabled', stream):
            sh = logging.StreamHandler(stream=stderr)
            sh.setLevel(c.get('level', NOTSET))
            stack.callback(sh.flush)
            sh.setFormatter(Formatter(c.get('format', default_stream_format),
                                      style='{'))
            hs.append(sh)

        for c in config.subs('files'):
            if not c.get('enabled', True): continue
            if (path := c.path('path')) is None: continue
            fh = handlers.TimedRotatingFileHandler(
                path, encoding='utf-8', utc=True,
                when=c.get('when', 'W6'), interval=c.get('interval', 1),
                backupCount=c.get('keep', 4), )
            if c.get('compress', True):
                fh.namer = lambda n: f'{n}.gz'
                fh.rotator = compress
            fh.setLevel(c.get('level', NOTSET))
            fh.setFormatter(Formatter(c.get('format', default_file_format),
                                      style='{'))
            hs.append(fh)

        for c in config.subs('databases'):
            if not c.get('enabled', True): continue
            lst = LogStore(c, stderr=stderr)
            try: lst.check_version(on_upgrade)
            except DisableHandler: continue
            stack.enter_context(lst)
            dbh = DatabaseHandler(lst)
            dbh.setLevel(c.get('level', NOTSET))
            hs.append(dbh)

        if not hs:
            pass
        elif transport == 'none':
            for h in hs:
                h.addFilter(ctx_filter)
                root.addHandler(h)
        elif transport == 'queue':
            q = queue.Queue()
            # TODO(py-3.14): Use QueueListener as a context manager
            ql = handlers.QueueListener(q, *hs, respect_handler_level=True)
            ql.start()
            stack.callback(ql.stop)
            qh = QueueHandler(q)
            qh.setLevel(min(h.level for h in hs))
            qh.addFilter(ctx_filter)
            root.addHandler(qh)
        else:
            raise Exception(f"Invalid log transport: {transport}")

        log.debug("Logs: transport=%(transport)s", transport=transport)
        stack.callback(lambda: log.debug("Logs: stopping"))
        yield


class DatabaseHandler(logging.Handler):
    def __init__(self, store):
        super().__init__()
        self.store = store

    def emit(self, rec):
        try:
            normalize_record(rec)
            self.store.log(rec)
        except Exception:
            self.handleError(rec)

    def flush(self):
        self.store.flush()


def safe_time_ns(v):
    try: return int(v * 1e9)
    except Exception: return time.time_ns()


def safe_int(v):
    if v is None: return None
    try: return int(v)
    except Exception: return None


def safe_str(v):
    if v is None: return None
    try: return str(v)
    except Exception: return None


class JSONEncoder(json.JSONEncoder):
    def default(self, v):
        if isinstance(v, set): return tuple(v)
        try: return str(v)
        except Exception: pass
        try: return repr(v)
        except Exception: pass
        return f'<{v.__class__.__name__}>'

to_json = JSONEncoder(skipkeys=True, separators=(',', ':')).encode


class Connection(database.Connection):
    def log(self, recs):
        rows = [(safe_time_ns(r.created), to_json(r.__dict__),
                 safe_int(r.levelno), safe_str(r.message), safe_str(r.msg),
                 to_json(r.args), safe_str(r.exc_text), safe_str(r.stack_info),
                 safe_str(r.name), safe_str(getattr(r, 'ctx', None)),
                 safe_str(r.pathname), safe_int(r.lineno), safe_str(r.funcName))
                for r in recs]
        self.executemany("""
            insert into log (time, record, level, message, msg, args, exception,
                             stack_info, logger, ctx, file, line, function)
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)

    def query(self, *, row_id=None, level=None, begin=None, end=None,
              where=None):
        terms, args = [], []
        def add_term(sql, arg):
            terms.append(sql)
            args.append(arg)
        if row_id is not None: add_term('rowid > ?', row_id)
        if level is not None: add_term('level >= ?', level)
        if begin is not None: add_term('time >= ?', database.to_nsec(begin))
        if end is not None: add_term('time < ?', database.to_nsec(end))
        if where is not None: terms.append(f'({where})')
        terms = f' where {' and '.join(terms)}' if terms else ''
        for rid, rec in self.execute(
                f"select rowid, record from log {terms} order by time", args):
            yield logging.makeLogRecord(json.loads(rec)), rid


class LogStore(database.Database):
    WriteConnection = Connection = Connection

    def __init__(self, config, *, stderr=None, **kwargs):
        super().__init__(config, **kwargs)
        self.stderr = stderr
        self.flush_interval = config.get('flush_interval', 5)
        self.lock = threading.Condition(threading.Lock())
        self.queue = []

    def __enter__(self):
        res = super().__enter__()
        self.db = self.connect(mode='rw')
        self.flusher = threading.Thread(target=self._flush, name='log:flusher')
        with self.lock: self._stop = self._wake = False
        self.flusher.start()
        return res

    def __exit__(self, typ, value, tb):
        with self.lock:
            self._stop = True
            self.lock.notify()
        self.flusher.join()
        self.db.close()
        return super().__exit__(typ, value, tb)

    def log(self, rec):
        with self.lock: self.queue.append(rec)

    def flush(self):
        with self.lock:
            self._wake = True
            self.lock.notify()

    def _flush(self):
        recs = None
        while True:
            with self.lock:
                self.lock.wait_for(lambda: self._stop or self._wake,
                                   timeout=self.flush_interval)
                self._wake = False
                stop = self._stop
                if self.queue: recs, self.queue = self.queue, []
            if recs:
                try:
                    with self.db as db: db.log(recs)
                except Exception as e:
                    if self.stderr is not None:
                        self.stderr.write(
                            f"Failed to insert {len(recs)} log rows: {e}\n")
                recs = None
            if stop: break

    def version_1(self, db, dev, now):
        super().version_1(db, dev, now)
        db.create("""
            create table log (
                time int not null,
                record text not null,
                level int,
                message text,
                msg text,
                args text,
                exception text,
                stack_info text,
                logger text,
                ctx text,
                file text,
                line int,
                function text
            ) strict
        """)
        db.create("create index log_time on log (time)")
