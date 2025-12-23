# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import pathlib
import tomllib


class Config:
    @classmethod
    def load(cls, path):
        if path is None: return cls({})
        with path.open('rb') as f:
            return cls(tomllib.load(f), path)

    def __init__(self, data, path=pathlib.Path()):
        self._data = data
        self._path = path

    def __repr__(self):
        return f'Config(path={self._path}, data={self._data})'

    def get(self, key, default=None):
        v = self._data
        for p in key.split('.'):
            if (v := v.get(p)) is None: return default
        return v

    def set(self, key, value):
        d, k = self._resolve(key)
        d[k] = value

    def setdefault(self, key, value):
        d, k = self._resolve(key)
        return d.setdefault(k, value)

    def _resolve(self, key):
        parts = key.split('.')
        d = self._data
        for p in parts[:-1]: d = d.setdefault(p, {})
        return d, parts[-1]

    def path(self, key, default=None):
        if (v := self.get(key, default)) is not None:
            v = (self._path.parent / v).resolve() if self._path is not None \
                else pathlib.Path(v).resolve()
        return v

    def sub(self, key):
        return Config(self.setdefault(key, {}), self._path)

    def subs(self, key):
        for it in self.setdefault(key, []):
            yield Config(it, self._path)
