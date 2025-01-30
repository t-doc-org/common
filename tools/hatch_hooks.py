# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import contextlib
import fnmatch
import json
import os
import pathlib
import shutil
import subprocess

from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from hatchling.metadata.plugin.interface import MetadataHookInterface

LICENSES = 'LICENSES.deps.txt'


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


class MetadataHook(MetadataHookInterface, HookMixin):
    def update(self, metadata):
        with (self.top / 'package-lock.json').open() as f:
            packages = json.load(f)
        with (self.top / LICENSES).open('w') as out:
            out.write(f"""\
This file lists the dependencies that are partially or fully included in this
package. The licenses of bundled package archives (e.g. *.whl) can be found in
the archives themselves.
""")
            for path in sorted(packages['packages']):
                if not path: continue
                root = self.top / path
                try:
                    with (root / 'package.json').open() as f:
                        pkg = json.load(f)
                except OSError:
                    continue
                out.write(f"\n---\n\nName: {pkg['name']}\n"
                          f"Version: {pkg['version']}\n"
                          f"License: {pkg['license']}\n"
                          f"Description: {pkg['description']}\n")
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
                    license = (root / 'LICENSE').read_text().strip()
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
