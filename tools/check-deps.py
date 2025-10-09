#!/usr/bin/env python
# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import functools
import json
import os
import pathlib
import subprocess
import sys
from urllib import request
import webbrowser

# TODO: Python: tools/requirements.sh uv, uv lock --upgrade
# TODO: GitHub actions


def main(argv, stdin, stdout, stderr):
    checker = Checker(argv, stdout, stderr)
    checker.check_deps()
    checker.check_node()


class Checker:
    def __init__(self, argv, stdout, stderr):
        self.base = pathlib.Path(argv[0]).parent.resolve().parent
        self.stdout, self.stderr = stdout, stderr
        self.first_section = True
        self.open = False
        i = 1
        while True:
            if i >= len(argv) or not (arg := argv[i]).startswith('--'):
                argv = argv[:1] + argv[i:]
                break
            elif arg == '--':
                argv = argv[:1] + argv[i + 1:]
                break
            elif arg == '--open':
                self.open = True
            else:
                raise Exception(f"Unknown option: {arg}")
            i += 1

    def write(self, s): return self.stdout.write(s)

    def section(self, s):
        if not self.first_section: self.write("\n")
        self.write(f"{s}\n{'=' * len(s)}\n")
        self.first_section = False

    def check_deps(self):
        path = self.base / 'tdoc' / 'common' / 'deps.py'
        mod = type(sys)('tdoc.common.deps')
        code = compile(path.read_text('utf-8'), str(path), 'exec')
        exec(code, mod.__dict__)
        pkgs = []
        for info in mod.info.values():
            pkg = NpmPackage(info['name'], info['version'], info['docs'])
            pkg.set_wanted(tag=info['tag'])
            pkgs.append(pkg)
        if not pkgs: return
        self.section("deps.py")
        self.report_npm_packages(pkgs)

    def check_node(self):
        pkgs = []
        for name, info in self.npm_outdated().items():
            pkg = NpmPackage(name, info.current)
            pkg.set_wanted(version=info.wanted)
            pkgs.append(pkg)
        if not pkgs: return
        self.section("npm outdated")
        self.report_npm_packages(pkgs)

    def npm_outdated(self):
        p = subprocess.run(('npm', 'outdated', '--json'),
                           stdin=subprocess.DEVNULL, capture_output=True,
                           cwd=self.base)
        if p.returncode != 0 and p.stderr: raise Exception(p.stderr)
        return json.loads(p.stdout, object_pairs_hook=Namespace)

    def report_npm_packages(self, pkgs):
        pkgs.sort(key=lambda p: p.name)
        for pkg in pkgs:
            if not pkg.outdated: continue
            self.write(f"{pkg.name}\n")
            w = max(len(pkg.current), len(pkg.wanted))
            self.write(
                f"  current: {pkg.current:{w}} ({pkg.time(pkg.current)})\n")
            self.write(
                f"  wanted : {pkg.wanted:{w}} ({pkg.time(pkg.wanted)})\n")
            if self.open:
                for url in pkg.urls:
                    webbrowser.open_new_tab(url)


class Namespace(dict):
    def __getattr__(self, name):
        return self[name]


class NpmPackage:
    def __init__(self, name, current, urls=None):
        self.name, self.current = name, current
        self.urls = [self.npmjs_versions]
        if urls is not None:
            self.urls.extend(u if isinstance(u, str) else u(name) for u in urls)

    def set_wanted(self, version=None, tag=None):
        if tag is not None:
            version = self.info['dist-tags'][tag]
        self.wanted = version

    @property
    def outdated(self): return self.wanted != self.current

    def time(self, version): return self.info.time[version]

    @functools.cached_property
    def info(self):
        with request.urlopen(f'https://registry.npmjs.org/{self.name}',
                             timeout=30) as f:
            return json.load(f, object_pairs_hook=Namespace)

    @property
    def npmjs_versions(self):
        return f'https://www.npmjs.com/package/{self.name}?activeTab=versions'


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv, sys.stdin, sys.stdout, sys.stderr))
    except SystemExit:
        raise
    except KeyboardInterrupt:
        sys.exit(1)
    except Exception as e:
        raise
        sys.stderr.write(f'\n{e}\n')
        sys.exit(1)
