#!/usr/bin/env python
# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import functools
import json
import os
import pathlib
import re
import subprocess
import sys
from urllib import request
import webbrowser

# TODO: Python: tools/requirements.sh uv
# TODO: GitHub actions


def main(argv, stdin, stdout, stderr):
    checker = Checker(argv, stdout, stderr)
    checker.check_deps()
    checker.check_node()
    checker.check_python()


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
            pkg = NpmPackage(info['name'], info['version'], urls=info['docs'])
            pkg.wanted_tag(info['tag'])
            if pkg.outdated: pkgs.append(pkg)
        if not pkgs: return
        self.section("deps.py")
        self.report_packages(pkgs)

    def check_node(self):
        pkgs = []
        for name, info in self.npm_outdated().items():
            pkg = NpmPackage(name, info.current, info.wanted)
            # TODO: Get release notes URL from info
            if pkg.outdated: pkgs.append(pkg)
        if not pkgs: return
        self.section("npm outdated")
        self.report_packages(pkgs)

    def npm_outdated(self):
        p = subprocess.run(('npm', 'outdated', '--json'), cwd=self.base,
                           stdin=subprocess.DEVNULL, capture_output=True)
        if p.returncode not in (0, 1): raise Exception(p.stderr)
        return json.loads(p.stdout, object_pairs_hook=Namespace)

    uv_update_re = re.compile('^Update ([^ ]+) v([^ ]+) -> v([^ ]+)$')

    def check_python(self):
        pkgs = []
        out = self.uv('lock', '--upgrade', '--dry-run', '--no-progress',
                      '--color=never', capture_output=True, text=True)[1]
        for line in out.splitlines():
            if (m := self.uv_update_re.fullmatch(line)) is None: continue
            pkg = PythonPackage(m[1], m[2], m[3])
            # TODO: Get release notes URL from info
            pkgs.append(pkg)

        if not pkgs: return
        self.section("Python")
        self.report_packages(pkgs)

    def uv(self, *args, **kwargs):
        p = subprocess.run(('uv', *args), cwd=self.base,
                           stdin=subprocess.DEVNULL, **kwargs)
        if p.returncode != 0: raise Exception(p.stderr)
        return p.stdout, p.stderr

    def report_packages(self, pkgs):
        pkgs.sort(key=lambda p: p.name)
        for pkg in pkgs: pkg.report(self.stdout, self.open)


class Namespace(dict):
    def __getattr__(self, name):
        return self[name]


def fetch_json(url):
    with request.urlopen(url, timeout=30) as f:
        return json.load(f, object_pairs_hook=Namespace)


class Package:
    def __init__(self, name, current, wanted=None, urls=None):
        self.name, self.current, self.wanted = name, current, wanted
        self.urls = [self.versions_url]
        if urls is not None:
            self.urls.extend(u if isinstance(u, str) else u(name) for u in urls)

    @property
    def outdated(self): return self.wanted != self.current

    def report(self, out, open):
        out.write(f"{self.name}\n")
        w = max(len(self.current), len(self.wanted))
        out.write(
            f"  current: {self.current:{w}} ({self.time(self.current)})\n")
        out.write(f"  wanted : {self.wanted:{w}} ({self.time(self.wanted)})\n")
        if open:
            for url in self.urls: webbrowser.open_new_tab(url)


class NpmPackage(Package):
    def wanted_tag(self, tag):
        self.wanted = self.info['dist-tags'][tag]

    def time(self, version): return self.info.time[version]

    @functools.cached_property
    def info(self):
        return fetch_json(f'https://registry.npmjs.org/{self.name}')

    @property
    def versions_url(self):
        return f'https://www.npmjs.com/package/{self.name}?activeTab=versions'


subsec_re = re.compile(r'\.\d{1,6}')


class PythonPackage(Package):
    def time(self, version):
        return max((subsec_re.sub('', p.upload_time_iso_8601)
                    for p in self.info.releases[version]),
                   default="unknown")

    @functools.cached_property
    def info(self):
        return fetch_json(f'https://pypi.org/pypi/{self.name}/json')

    @property
    def versions_url(self):
        return f'https://pypi.org/project/{self.name}/#history'


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
