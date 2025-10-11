#!/usr/bin/env python
# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import functools
import itertools
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import tomllib
from urllib import request
import webbrowser

# TODO: GitHub actions


def main(argv, stdin, stdout, stderr):
    checker = Checker(argv, stdout, stderr)
    checker.check_deps()
    checker.check_node()
    checker.check_python()
    checker.check_requirements()


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

    @functools.cached_property
    def pyproject(self):
        with (self.base / 'pyproject.toml').open('rb') as f:
            return tomllib.load(f)

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
            pkg = NpmPackage(info['name'], info['version'])
            pkg.wanted_tag(info['tag'])
            if (urls := info.get('release_urls')) is not None:
                pkg.urls.extend(urls)
            else:
                pkg.add_releases_url()
            if pkg.outdated: pkgs.append(pkg)
        if not pkgs: return
        self.section("deps.py")
        self.report_packages(pkgs)

    def check_node(self):
        pkgs = []
        for name, info in self.npm_outdated().items():
            pkg = NpmPackage(name, info.current, info.wanted)
            pkg.add_releases_url()
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
            pkg.add_releases_url()
            pkgs.append(pkg)
        if not pkgs: return
        self.section("pyproject.toml")
        self.report_packages(pkgs)

    def check_requirements(self):
        for p in sorted((self.base / 'config').glob('[!0-9]*.req')):
            cur_reqs = self.parse_requirements(p.read_text())
            with tempfile.NamedTemporaryFile('w') as f:
                f.write(f"""\
# /// script
# requires-python = {self.pyproject['project']['requires-python']!r}
# dependencies = [{p.stem!r}]
# ///
""")
                f.flush()
                out = self.uv('export', '--no-header',
                              '--format=requirements.txt', f'--script={f.name}',
                              capture_output=True, text=True)[0]
            want_reqs = self.parse_requirements(out)
            if want_reqs == cur_reqs: continue
            pkgs = []
            for pn in cur_reqs | want_reqs:
                current, wanted = cur_reqs.get(pn), want_reqs.get(pn)
                if current == wanted: continue
                pkg = PythonPackage(pn, current, wanted)
                pkg.add_releases_url()
                pkgs.append(pkg)
            if not pkgs: return
            self.section(p.name)
            self.report_packages(pkgs)

    reqs_pkg_version_re = re.compile(f'(?m)^([^\\s=]+)==([^\\s;]+)(?:\\s|$)')

    def parse_requirements(self, text):
        reqs = {}
        for m in self.reqs_pkg_version_re.finditer(text): reqs[m[1]] = m[2]
        return reqs

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


gh_repo_re = re.compile(r'\bhttps://github\.com/([^/]+/[^/.]+)')
subsec_re = re.compile(r'\.\d{1,6}')


class Package:
    def __init__(self, name, current, wanted=None):
        self.name, self.current, self.wanted = name, current, wanted
        self.urls = [self.versions_url]

    @property
    def outdated(self): return self.wanted != self.current

    @property
    def info(self):
        if (info := self._info_cache.get(self.name)) is not None: return info
        res = self._info_cache[self.name] = fetch_json(self.info_url)
        return res

    def report(self, out, open):
        out.write(f"{self.name}\n")
        w = max(len(self.current), len(self.wanted))
        out.write(
            f"  current: {self.current:{w}} ({self.time(self.current)})\n")
        out.write(f"  wanted : {self.wanted:{w}} ({self.time(self.wanted)})\n")
        for url in self.urls:
            out.write(f"  url: {url}\n")
            if open: webbrowser.open_new_tab(url)


class NpmPackage(Package):
    _info_cache = {}

    @property
    def info_url(self): return f'https://registry.npmjs.org/{self.name}'

    def wanted_tag(self, tag):
        self.wanted = self.info['dist-tags'][tag]

    def add_releases_url(self):
        for pi in (self.info, self.info.versions.get(self.wanted, ''),
                   self.info.versions.get(self.current, '')):
            if (m := gh_repo_re.search(pi.repository.url)) is None: continue
            self.urls.append(f'https://github.com/{m[1]}/releases')
            break

    def time(self, version): return self.info.time[version]

    @property
    def versions_url(self):
        return f'https://www.npmjs.com/package/{self.name}?activeTab=versions'


class PythonPackage(Package):
    _info_cache = {}

    @property
    def info_url(self): return f'https://pypi.org/pypi/{self.name}/json'

    def time(self, version):
        return max((subsec_re.sub('', p.upload_time_iso_8601)
                    for p in self.info.releases[version]),
                   default="unknown")

    def add_releases_url(self):
        if self._add_project_url('release'): return
        if self._add_project_url('change'): return
        if self._add_project_url('news'): return
        for url in itertools.chain(
                self.info.info.get('project_urls', {}).values(),
                [self.info.info.get('home_page', '')]):
            if (m := gh_repo_re.search(url)) is None: continue
            self.urls.append(f'https://github.com/{m[1]}/releases')
            return
        if self._add_project_url('home'): return

    def _add_project_url(self, label):
        for ul, url in self.info.info.project_urls.items():
            if label in ul.lower():
                self.urls.append(url)
                return True
        return False

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
