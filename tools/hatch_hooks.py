# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import contextlib
import fnmatch
import http.client
import io
import json
import os
import pathlib
import re
import shutil
import subprocess
from urllib import parse
import zipfile

from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from hatchling.metadata.plugin.interface import MetadataHookInterface

LICENSES = 'LICENSES.deps.txt'
pyodide_rel = 'https://github.com/t-doc-org/pyodide-packages/releases/download'
pyodide_packages = [
    r'micropip-\d+(?:\.\d+)+.*\.whl',
    r'packaging-\d+(?:\.\d+)+.*\.whl',
    r'sqlite3-\d+(?:\.\d+)+.*\.zip',
]


class HookMixin:
    @property
    def top(self):
        return pathlib.Path(self.root)

    @property
    def node_modules(self):
        return self.top / 'node_modules'

    @property
    def static_gen(self):
        return self.top / 'tdoc' / 'common' / 'static.gen'

    @property
    def package_lock(self):
        with (self.top / 'package-lock.json').open() as f:
            return json.load(f)


class MetadataHook(MetadataHookInterface, HookMixin):
    def update(self, metadata):
        with (self.top / LICENSES).open('w') as out:
            out.write(f"""\
This file lists the dependencies that are partially or fully included in this
package. The licenses of bundled package archives (e.g. *.whl) can be found in
the archives themselves.
""")
            for path in sorted(self.package_lock['packages']):
                if not path: continue
                root = self.top / path
                try:
                    with (root / 'package.json').open() as f:
                        pkg = json.load(f)
                except OSError:
                    continue
                out.write(f"\n---\n\nName: {pkg['name']}\n"
                          f"Version: {pkg['version']}\n"
                          f"License: {pkg['license']}\n")
                if desc := pkg.get('description'):
                    out.write(f"Description: {desc}\n")
                if repo := pkg.get('repository'):
                    if isinstance(repo, str):
                        out.write(f"Repository: {repo}\n")
                    elif url := repo.get('url'):
                        out.write(f"Repository: {url}\n")
                if url := pkg.get('homepage'):
                    out.write(f"Homepage: {url}\n")
                if author := pkg.get('author'):
                    if isinstance(author, str):
                        out.write(f"Author: {author}\n")
                    else:
                        out.write(f"Author: {author['name']}")
                        if email := author.get('email'):
                            out.write(f" <{email}>")
                        if url := author.get('url'):
                            out.write(f" ({url})")
                        out.write("\n")
                try:
                    license = (root / 'LICENSE').read_text('utf-8').strip()
                except OSError:
                    pass
                else:
                    out.write(f"License text:\n===\n\n{license}\n")


class BuildHook(BuildHookInterface, HookMixin):
    def initialize(self, version, build_data):
        self.app.display_info("Installing node packages")
        npm = shutil.which('npm')
        if npm is None: raise Exception("The 'npm' command cannot be found")
        self.run([npm, 'install'])

        self.app.display_info("Removing generated files")
        shutil.rmtree(self.static_gen, ignore_errors=True)

        self.app.display_info("Generating files")
        os.makedirs(self.static_gen, exist_ok=True)
        self.copytree_node('@drauu/core/dist', 'drauu', globs=['*.mjs'])
        self.copytree_node('mathjax/es5', 'mathjax')
        self.copytree_node('polyscript/dist', 'polyscript', globs=[
            '*.js', '*.js.map',
        ])
        self.copytree_node('pyodide', 'pyodide', globs=[
            'pyodide.asm.*', 'pyodide-lock.json', 'pyodide.mjs',
            'pyodide.mjs.map', 'python_stdlib.zip',
        ])
        self.copy_node('sabayon/dist/sw-listeners.js', 'sabayon-listeners.js')
        self.copytree_node(
            '@sqlite.org/sqlite-wasm/sqlite-wasm/jswasm', 'sqlite', globs=[
                'sqlite3-bundler-friendly.mjs',
                'sqlite3-opfs-async-proxy.js',
                'sqlite3-worker1-bundler-friendly.mjs',
                'sqlite3-worker1-promiser.mjs',
                'sqlite3.wasm',
            ])
        self.run([npm, 'run', 'build'])

        self.app.display_info("Fetching Pyodide packages")
        for name, pkg in self.package_lock['packages'].items():
            if name == 'node_modules/pyodide':
                v = pkg['version']
                break
        else:
            raise Exception('pyodide not found in package-lock.json')
        pat = re.compile('|'.join(pyodide_packages))
        with HttpFile(f'{pyodide_rel}/{v}/pyodide-{v}.zip') as hf, \
                zipfile.ZipFile(hf, mode='r') as zf:
            for zi in zf.infolist():
                if zi.is_dir(): continue
                name = pathlib.Path(zi.filename).name
                if pat.fullmatch(name) is None: continue
                with zf.open(zi) as f:
                    dst = pathlib.Path(self.static_gen / 'pyodide' / name)
                    dst.write_bytes(f.read())

    def copy_node(self, src, dst):
        shutil.copy2(self.node_modules / src, self.static_gen / dst)

    def copytree_node(self, src, dst, globs=('*',), **kwargs):
        def ignore(path, names):
            return [n for n in names
                    if not any(fnmatch.fnmatch(n, p) for p in globs)]
        shutil.copytree(self.node_modules / src, self.static_gen / dst,
                        symlinks=True, dirs_exist_ok=True, ignore=ignore,
                        **kwargs)

    def run(self, args):
        res = subprocess.run(args, cwd=self.root, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True)
        if res.returncode != 0:
            self.app.abort(f"Command failed:\n{res.stdout}")


class HttpFile(io.RawIOBase):
    def __init__(self, url):
        self._offset = 0
        while True:
            parts = parse.urlsplit(url, allow_fragments=False)
            self._req = parse.urlunsplit(('', '') + parts[2:])
            if parts.scheme == 'http':
                cls = http.client.HTTPConnection
            elif parts.scheme == 'https':
                cls = http.client.HTTPSConnection
            else:
                raise ValueError(f"Unsupported URL: {url}")
            conn = cls(parts.netloc)
            try:
                conn.request('HEAD', self._req)
                resp = conn.getresponse()
                resp.read()
                if resp.status == http.HTTPStatus.OK:
                    if resp.headers['Accept-Ranges'] != 'bytes':
                        raise Exception("Range requests unsupported")
                    self._size = int(resp.headers['Content-Length'])
                    self._conn, conn = conn, None
                    break
                elif resp.status in (http.HTTPStatus.MOVED_PERMANENTLY,
                                     http.HTTPStatus.FOUND,
                                     http.HTTPStatus.TEMPORARY_REDIRECT,
                                     http.HTTPStatus.PERMANENT_REDIRECT):
                    url = resp.headers['Location']
                    continue
                raise Exception(f"Request failed: {resp.status} {resp.reason}")
            finally:
                if conn is not None: conn.close()

    def close(self):
        self._conn.close()

    def __enter__(self): return self
    def __exit__(self, typ, value, tb): self.close()

    def read(self, size=-1, /):
        if size == 0: return b''
        elif size < 0: size = self._size - self._offset
        elif self._offset + size > self._size: size = self._size - self._offset
        self._conn.request('GET', self._req, headers={
            'Range': f'bytes={self._offset}-{self._offset + size - 1}',
        })
        resp = self._conn.getresponse()
        data = resp.read()
        if resp.status != http.HTTPStatus.PARTIAL_CONTENT:
            raise Exception(f"Request failed: {resp.status} {resp.reason}")
        self._offset += len(data)
        return data

    def seek(self, offset, whence=os.SEEK_SET, /):
        off = self._offset
        if whence == os.SEEK_SET:
            off = offset
        elif whence == os.SEEK_CUR:
            off += offset
        elif whence == os.SEEK_END:
            off = self._size + offset
        else:
            raise ValueError(f"Invalid whence argument: {whence}")
        self._offset = 0 if off < 0 else self._size if off > self._size else off
        return self._offset

    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self._offset
