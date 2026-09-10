# Copyright 2026 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import contextvars
import functools
import inspect

ctx = contextvars.ContextVar('ctx', default=None)
get = ctx.get


class replace:
    __slots__ = ('value',)

    def __init__(self, value):
        self.value = value

    def __enter__(self):
        if callable(v := self.value): v = v()
        self.token = ctx.set(v)
        return self

    def __exit__(self, typ, value, tb):
        ctx.reset(self.token)

    def __call__(self, fn):
        value = self.value
        if inspect.isgeneratorfunction(fn):
            @functools.wraps(fn)
            def wrapper(*args, **kwargs):
                if callable(v := value): v = v()
                token = ctx.set(v)
                try:
                    return (yield from fn(*args, **kwargs))
                finally:
                    ctx.reset(token)
        else:
            @functools.wraps(fn)
            def wrapper(*args, **kwargs):
                if callable(v := value): v = v()
                token = ctx.set(v)
                try:
                    return fn(*args, **kwargs)
                finally:
                    ctx.reset(token)
        return wrapper


class set:
    __slots__ = ('value', 'token')

    def __init__(self, value):
        self.value = value

    def __enter__(self):
        if get() is not None:
            self.token = None
            return
        if callable(v := self.value): v = v()
        self.token = ctx.set(v)
        return self

    def __exit__(self, typ, value, tb):
        if (t := self.token) is not None: ctx.reset(t)

    def __call__(self, fn):
        value = self.value
        if inspect.isgeneratorfunction(fn):
            @functools.wraps(fn)
            def wrapper(*args, **kwargs):
                if get() is not None: return (yield from fn(*args, **kwargs))
                if callable(v := value): v = v()
                token = ctx.set(v)
                try:
                    return (yield from fn(*args, **kwargs))
                finally:
                    ctx.reset(token)
        else:
            @functools.wraps(fn)
            def wrapper(*args, **kwargs):
                if get() is not None: return fn(*args, **kwargs)
                if callable(v := value): v = v()
                token = ctx.set(v)
                try:
                    return fn(*args, **kwargs)
                finally:
                    ctx.reset(token)
        return wrapper
