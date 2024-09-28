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
env = {'__name__': '__main__'}

js_input = xworker.sync.input
js_write = xworker.sync.write


def public(fn):
    """Make a function available in the client code environment."""
    env[fn.__name__] = fn
    return fn


def export(fn):
    """Export a function to JavaScript."""
    setattr(xworker.sync, fn.__name__, fn)
    return fn


class OutStream(io.RawIOBase):
    """An output stream that forwards writes to JavaScript."""
    def __init__(self, stream):
        self.stream = stream

    def writable(self): return True

    def write(self, data, /):
        size = len(data)
        if size > 0: js_write(run_id_var.get(), self.stream, data)
        return size


sys.stdout = io.TextIOWrapper(io.BufferedWriter(OutStream(1)),
                              line_buffering=True)
sys.stderr = io.TextIOWrapper(io.BufferedWriter(OutStream(2)),
                              line_buffering=True)


@public
async def input_line(prompt=None):
    """Request a single line of text from the user."""
    return await js_input(run_id_var.get(), 'line', prompt)


@public
async def input_text(prompt=None):
    """Request a multi-line text from the user."""
    return await js_input(run_id_var.get(), 'text', prompt)


@public
async def input_buttons(prompt, labels):
    """Present a list of buttons and wait for the user to click one of them."""
    return await js_input(run_id_var.get(), 'buttons', prompt, labels)


@public
async def pause(prompt=None, label="@icon{forward-step}"):
    """Present a button, and wait for the user to click it."""
    await js_input(run_id_var.get(), 'buttons-right', prompt, [label])


@export
async def run(run_id, blocks):
    """Run a block of client code."""
    run_id_var.set(run_id)
    tasks[run_id] = asyncio.current_task()
    try:
        e = env.copy()
        for code, name in blocks:
            code = compile(code, name or '<unnamed>', 'exec',
                           flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
            if (coro := eval(code, e)) is not None:
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
    """Stop a running block of client code."""
    if (task := tasks.get(run_id)) is not None:
        task.cancel()


xworker.sync.ready(f"{platform.python_implementation()}"
                   f" {'.'.join(platform.python_version_tuple())}"
                   f" on {platform.platform()}"
                   f" (polyfill: {xworker.polyfill})")
