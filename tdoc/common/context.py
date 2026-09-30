# Copyright 2026 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import contextlib
import contextvars


class Var:
    __slots__ = ('_var', 'get', 'set', 'reset')

    def __init__(self, name, **kwargs):
        self._var = contextvars.ContextVar(name, **kwargs)
        self.get = self._var.get
        self.set = self._var.set
        self.reset = self._var.reset

    @property
    def name(self): return self._var.name

    @contextlib.contextmanager
    def set_default(self, value):
        try:
            self.get()
        except LookupError:
            token = self.set(value)
            try:
                yield
            finally:
                self.reset(token)
        else:
            yield

    @contextlib.contextmanager
    def add(self, *args):
        token = self.set(tuple(sorted(set(self.get(()) + args))))
        try:
            yield
        finally:
            self.reset(token)


ctx = Var('ctx')
tags = Var('tags', default=())
