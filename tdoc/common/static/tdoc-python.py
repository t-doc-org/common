# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import ast
import asyncio
import contextvars
import io
import platform
import sys
import traceback

from polyscript import xworker

run_id_var = contextvars.ContextVar('run_id', default=None)
tasks = {}
write = xworker.sync.write


def export(fn):
    setattr(xworker.sync, fn.__name__, fn)
    return fn


class OutStream(io.RawIOBase):
    def __init__(self, stream):
        self.stream = stream

    def writable(self): return True

    def write(self, data, /):
        size = len(data)
        if size > 0: write(run_id_var.get(), self.stream, data)
        return size


sys.stdout = io.TextIOWrapper(io.BufferedWriter(OutStream(1)),
                              line_buffering=True)
sys.stderr = io.TextIOWrapper(io.BufferedWriter(OutStream(2)),
                              line_buffering=True)


@export
async def run(run_id, blocks):
    run_id_var.set(run_id)
    tasks[run_id] = asyncio.current_task()
    try:
        blocks = [compile(b, name or '<unnamed>', 'exec',
                          flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
                  for b, name in blocks]
        g = {'__name__': '__main__'}
        for code in blocks:
            if (coro := eval(code, g)) is not None:
                await coro
    except BaseException as e:
        te = traceback.TracebackException.from_exception(e, compact=True)
        for line in te.format():
            # This is a bit primitive, but more sophisticated traceback
            # manipulations have undesirable side-effects.
            if line.startswith('  File "<exec>", line '): continue
            print(line, file=sys.stderr, end='')
    finally:
        del tasks[run_id]


@export
def stop(run_id):
    if (task := tasks.get(run_id)) is not None:
        task.cancel()


xworker.sync.ready(f"{platform.python_implementation()}"
                   f" {'.'.join(platform.python_version_tuple())}"
                   f" on {platform.platform()}")
