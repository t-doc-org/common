# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import itertools
import pathlib
import tomllib

tdoc_toml = 'tdoc.toml'
tdoc_local_toml = 'tdoc.local.toml'


def merge(data, path):
    try:
        with open(path, 'rb') as f:
            merge_dict(data, tomllib.load(f))
        return True
    except OSError:
        return False


def merge_dict(dst, src):
    for k, sv in src.items():
        if isinstance(sv, dict) and isinstance(dv := dst.get(k), dict):
            merge_dict(dv, sv)
        else:
            dst[k] = sv


class Config:
    @classmethod
    def load(cls, path):
        if path is None: return cls({})
        path = path.resolve()
        data = {}
        if not merge(data, path / 'config' / tdoc_toml):
            merge(data, path / '_venv' / tdoc_toml)
        merge(data, path / tdoc_toml)
        merge(data, path / tdoc_local_toml)
        return cls(data, path)

    def __init__(self, data, path=pathlib.Path()):
        self._data = data
        self._path = path

    def __repr__(self):
        return f'Config(path={self._path}, data={self._data})'

    def keys(self): return self._data.keys()
    def values(self): return self._data.values()
    def items(self): return self._data.items()

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

    def as_path(self, v):
        if v is None: return
        return (self._path / v).resolve() if self._path is not None \
                else pathlib.Path(v).resolve()

    def path(self, key, default=None):
        return self.as_path(self.get(key, default))

    def sub(self, key):
        return Config(self.setdefault(key, {}), self._path)

    def subs(self, key):
        for it in self.setdefault(key, []):
            yield Config(it, self._path)
