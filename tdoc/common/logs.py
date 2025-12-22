# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import contextlib
import contextvars
import datetime
import functools
import gzip
import logging
from logging import handlers
import os
import shutil
import threading
import traceback

from . import config as tconfig

globals().update(logging.getLevelNamesMapping())
logger = logging.getLogger

ctx = contextvars.ContextVar('ctx', default=None)


class CtxFilter(logging.Filter):
    def filter(self, rec):
        rec.ilevel = rec.levelname[0]
        if (v := ctx.get()) is None: v = threading.current_thread().name
        rec.ctx = v[:20]
        return True


class Formatter(logging.Formatter):
    def format(self, rec):
        if rec.exc_info and not rec.exc_text:
            # This needs to be done here instead of formatException(), because
            # the latter doesn't have access to the LogRecord.
            parts = traceback.format_exception(
                *rec.exc_info, limit=getattr(rec, 'exc_limit', None),
                chain=getattr(rec, 'exc_chain', True))
            if parts and (last := parts[-1])[-1:] == "\n": parts[-1] = last[:-1]
            rec.exc_text = "".join(parts)
        return super().format(rec).replace("\n", "\n| ")

    def formatTime(self, rec, datefmt=None):
        dt = datetime.datetime.utcfromtimestamp(rec.created)
        return dt.isoformat(timespec='microseconds')


def compress(src, dst):
    with open(src, 'rb') as inp, gzip.open(dst, 'wb') as out:
        shutil.copyfileobj(inp, out)
    os.remove(src)


@contextlib.contextmanager
def configure(config=None, stderr=None, level=WARNING, stream=False):
    if config is None: config = tconfig.Config({})

    logging.raiseExceptions = False
    logging.lastResort = logging.NullHandler()

    root = logging.getLogger()
    root.setLevel(config.get('level', level))
    ctx_filter = CtxFilter()

    with contextlib.ExitStack() as stack:
        stack.callback(logging.shutdown)

        if stderr is not None and \
                (c := config.sub('stream')).get('enabled', stream):
            sh = logging.StreamHandler(stream=stderr)
            sh.setLevel(c.get('level', NOTSET))
            stack.callback(sh.flush)
            sh.addFilter(ctx_filter)
            sh.setFormatter(Formatter(
                c.get('format', '{ilevel} [{ctx:20}] {message}'), style='{'))
            root.addHandler(sh)

        if (c := config.sub('file')).get('enabled', False) \
                and (path := c.path('path')) is not None:
            fh = handlers.TimedRotatingFileHandler(
                path, encoding='utf-8', utc=True,
                when=c.get('when', 'W6'), interval=c.get('interval', 1),
                backupCount=c.get('keep', 4), )
            if c.get('compress', True):
                fh.namer = lambda n: f'{n}.gz'
                fh.rotator = compress
            fh.setLevel(c.get('level', NOTSET))
            fh.addFilter(ctx_filter)
            fh.setFormatter(Formatter(
                c.get('format', '{asctime} {ilevel} [{ctx:20}] {message}'),
                style='{'))
            root.addHandler(fh)

        yield
