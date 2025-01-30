# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import ast
import asyncio
import contextlib
import contextvars
import inspect
import io
import sys
import traceback

from polyscript import xworker
from pyodide.ffi import run_sync

run_id_var = contextvars.ContextVar('run_id', default=None)
run_id = run_id_var.get

tasks = {}
env = {'__name__': '__main__'}

js_input = xworker.sync.input
js_render = xworker.sync.render
js_write = xworker.sync.write


def public(fn):
    """Make a function available in the client code environment."""
    env[fn.__name__] = fn
    return fn


def export(fn):
    """Export a function to JavaScript."""
    setattr(xworker.sync, fn.__name__, fn)
    return fn


def linenos(obj):
    """Return the start and past-the-end lines of an object."""
    lines, start = inspect.getsourcelines(obj)
    return start, start + len(lines)


class ContextProxy:
    """A proxy object that forwards attributes accesses to a context value."""
    __slots__ = ('_ContextProxy__var',)

    def __init__(self, var):
        super().__setattr__('_ContextProxy__var', var)

    def __getattr__(self, name):
        return getattr(self.__var.get(), name)

    def __setattr__(self, name, value):
        return setattr(self.__var.get(), name, value)

    def __delattr__(self, name):
        return delattr(self.__var.get(), name)

    def __dir__(self):
        return self.__var.get().__dir__()


class OutStream(io.RawIOBase):
    """An output stream that forwards writes to JavaScript."""
    def __init__(self, stream):
        self.stream = stream

    def writable(self): return True

    def write(self, data, /):
        size = len(data)
        if size > 0: js_write(run_id(), self.stream, data)
        return size


stdout_var = contextvars.ContextVar(
    'stdout',
    default=io.TextIOWrapper(io.BufferedWriter(OutStream(1)),
                             line_buffering=True))
stderr_var = contextvars.ContextVar(
    'stderr',
    default=io.TextIOWrapper(io.BufferedWriter(OutStream(2)),
                             line_buffering=True))
sys.stdout = ContextProxy(stdout_var)
sys.stderr = ContextProxy(stderr_var)


@public
@contextlib.contextmanager
def redirect(stdout=None, stderr=None):
    stdout_token, stderr_token = None, None
    if stdout is not None: stdout_token = stdout_var.set(stdout)
    if stderr is not None: stderr_token = stderr_var.set(stderr)
    try:
        yield
    finally:
        if stdout_token is not None: stdout_var.reset(stdout_token)
        if stderr_token is not None: stderr_var.reset(stderr_token)


_next_id = 0

@public
def new_id():
    """Generate a unique ID, usable in id= attributes."""
    global _next_id
    v = _next_id
    _next_id += 1
    return f'tdoc-id-{v}'


@public
def render(html, name=''):
    """Render some HTML in an output block."""
    if not isinstance(html, str): html = ''.join(html)
    return js_render(run_id(), html, name).then(lambda res: tuple(res))


@public
async def input_line(prompt=None):
    """Request a single line of text from the user."""
    return await js_input(run_id(), 'line', prompt)


@public
async def input_text(prompt=None):
    """Request a multi-line text from the user."""
    return await js_input(run_id(), 'text', prompt)


@public
async def input_buttons(prompt, labels):
    """Present a list of buttons and wait for the user to click one of them."""
    return await js_input(run_id(), 'buttons', prompt, labels)


@public
async def pause(prompt=None, label="@icon{forward-step}"):
    """Present a button, and wait for the user to click it."""
    await js_input(run_id(), 'buttons-right', prompt, [label])


@public
def input(prompt=None):
    """Synchronously request a single line of text from the user."""
    return run_sync(input_line(prompt))


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
            if (coro := eval(code, e)) is not None: await coro
    except BaseException as e:
        te = traceback.TracebackException.from_exception(e, compact=True)
        # Filter this function out of the stack trace
        for i, fs in enumerate(te.stack):
            if (fs.filename == __file__ and run_start <= fs.lineno < run_end
                    and fs.name == 'run'):
                del te.stack[i]
                break
        te.print()
    finally:
        del tasks[run_id]


run_start, run_end = linenos(run)


@export
def stop(run_id):
    """Stop a running block of client code."""
    if (task := tasks.get(run_id)) is not None:
        task.cancel()
