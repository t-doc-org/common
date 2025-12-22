# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import contextlib
import contextvars
import functools
import logging
import threading
import traceback

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


@contextlib.contextmanager
def configure(config=None, stderr=None, level=logging.WARNING, stream=False,
              stream_format='{ilevel} [{ctx:20}] {message}'):
    if config is None: config = {}
    level = config.get('level', level)
    stream = config.get('stream', stream)
    stream_format = config.get('stream_format', stream_format)

    logging.raiseExceptions = False
    logging.lastResort = logging.NullHandler()

    root = logging.getLogger()
    root.setLevel(level)
    ctx_filter = CtxFilter()

    with contextlib.ExitStack() as stack:
        stack.callback(logging.shutdown)

        if stream and stderr is not None:
            sh = logging.StreamHandler(stream=stderr)
            stack.callback(sh.flush)
            sh.addFilter(ctx_filter)
            sh.setFormatter(Formatter(stream_format, style='{'))
            root.addHandler(sh)

        yield
