# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

from collections import abc
import contextlib
import contextvars
import datetime
import functools
import gzip
import logging
from logging import handlers
import os
import queue
import shutil
import threading
import traceback

from . import config as _config

# TODO: Allow per-handler filters
# TODO: Add a DB log handler, logging to a separate database

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
        rec.ilevel = rec.levelname[0]
        if (v := ctx.get()) is None: v = threading.current_thread().name
        rec.ctx = v[:20]
        return True


def get_kwarg(rec, name, default=None):
    if (args := rec.args) and isinstance(args, abc.Mapping):
        return args.get(name, default)
    return default


def format_exception(rec):
    if rec.exc_info and not rec.exc_text:
        parts = traceback.format_exception(
            *rec.exc_info, limit=get_kwarg(rec, 'exc_limit', None),
            chain=get_kwarg(rec, 'exc_chain', True))
        if parts and (last := parts[-1])[-1:] == "\n": parts[-1] = last[:-1]
        rec.exc_text = "".join(parts)
        rec.exc_info = None


class Formatter(logging.Formatter):
    def format(self, rec):
        # This needs to be done here instead of formatException(), because the
        # latter doesn't have access to the LogRecord.
        format_exception(rec)
        return super().format(rec).replace("\n", "\n  ")

    def formatTime(self, rec, datefmt=None):
        dt = datetime.datetime.utcfromtimestamp(rec.created)
        return dt.isoformat(timespec='microseconds')


class QueueHandler(handlers.QueueHandler):
    def prepare(self, rec):
        format_exception(rec)
        return rec


def compress(src, dst):
    with open(src, 'rb') as inp, gzip.open(dst, 'wb') as out:
        shutil.copyfileobj(inp, out)
    os.remove(src)


@contextlib.contextmanager
def configure(config=None, stderr=None, level=WARNING, stream=False,
              raise_exc=False):
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
            sh.setFormatter(Formatter(
                c.get('format', '{ilevel} [{ctx:20}] {message}'), style='{'))
            hs.append(sh)

        for c in config.subs('file'):
            if not c.get('enabled', False): continue
            if (path := c.path('path')) is None: continue
            fh = handlers.TimedRotatingFileHandler(
                path, encoding='utf-8', utc=True,
                when=c.get('when', 'W6'), interval=c.get('interval', 1),
                backupCount=c.get('keep', 4), )
            if c.get('compress', True):
                fh.namer = lambda n: f'{n}.gz'
                fh.rotator = compress
            fh.setLevel(c.get('level', NOTSET))
            fh.setFormatter(Formatter(
                c.get('format',
                      '{asctime} {ilevel} [{ctx:20}] [{module}] {message}'),
                style='{'))
            hs.append(fh)

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
