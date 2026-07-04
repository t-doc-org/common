# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import contextlib
import json
import re
import webbrowser

from .. import cli, deps, util

# TODO: check: Suggest only versions satisfying the cooldown
# TODO: Add support for GitHub actions


def add_commands(parser):
    p = parser.add_parser('deps', help="Commands related to dependencies.")
    sp = p.add_subparsers(title="Sub-commands")
    sp.required = True

    p = sp.add_parser('check', help="Check dependencies for updates.")
    p.set_defaults(handler=cmd_check)
    arg = p.add_argument
    arg('--cooldown', metavar='TIME', dest='cooldown', type='nrel_timestamp',
        default='7d',
        help="Updates more recent than the given relative or absolute time "
             "are highlighted in red (default: %(default)s).")
    arg('--open', action='store_true', dest='open',
        help="Open all URLs in a browser.")
    cli.add_common_options(p)

    p = sp.add_parser('generate', help="Generate requirements files.")
    p.set_defaults(handler=cmd_generate)
    arg = p.add_argument
    arg('name', metavar='NAME', nargs='+',
        help="The requirements files to generate.")
    cli.add_common_options(p)


def cmd_check(opts):
    cli.require_common(opts)
    checker = Checker(opts)
    checker.check_cdn()
    checker.check_node()
    checker.check_python()
    checker.check_requirements()


def format_date(dt):
    return dt.replace(tzinfo=None).date().isoformat()


class Checker:
    def __init__(self, opts):
        self.opts = opts
        self.first_section = True

    def write(self, s): return self.opts.stdout.write(s)

    def section(self, s):
        o = self.opts.stdout
        if not self.first_section: self.write("\n")
        self.write(f"{o.BOLD}{s}{o.NORM}\n{o.BOLD}{'=' * len(s)}{o.NORM}\n")
        self.first_section = False

    def check_cdn(self):
        pkgs = []
        for info in deps.info.values():
            if 'cdn' not in info: continue
            pkg = NpmPackage(info['name'], info['version'])
            pkg.wanted_from_tag(info['tag'])
            pkg.add_urls(info.get('release_urls', ()))
            if pkg.outdated: pkgs.append(pkg)
        if not pkgs: return
        self.section("CDN")
        self.report_packages(pkgs)

    def check_node(self):
        pkgs = []
        for name, info in self.npm_outdated().items():
            pkg = NpmPackage(name, info.current, info.wanted)
            pkg.add_urls()
            if pkg.outdated: pkgs.append(pkg)
        if not pkgs: return
        self.section("npm outdated")
        self.report_packages(pkgs)

    def npm_outdated(self):
        return util.run_json('npm', 'outdated', '--json', cwd=self.opts.common,
                             success=(0, 1))

    uv_update_re = re.compile(r'^Update ([^ ]+) v([^ ]+) -> v([^ ]+)$')

    def check_python(self):
        pkgs = []
        out = util.run_uv('lock', '--upgrade', '--dry-run', '--no-progress',
                          '--color=never', common=self.opts.common,
                          capture_output=True, text=True).stderr
        for line in out.splitlines():
            if (m := self.uv_update_re.fullmatch(line)) is None: continue
            pkg = PythonPackage(m[1], m[2], m[3])
            pkg.add_urls()
            pkgs.append(pkg)
        if not pkgs: return
        self.section("pyproject.toml")
        self.report_packages(pkgs)

    def check_requirements(self):
        for p in sorted((self.opts.common / 'config').glob('[!0-9]*.req')):
            cur_reqs = self.parse_requirements(p.read_text('utf-8'))
            want_reqs = self.parse_requirements(
                util.requirements(only_groups=[p.stem],
                                  common=self.opts.common))
            if want_reqs == cur_reqs: continue
            pkgs = []
            for pn in cur_reqs | want_reqs:
                current, wanted = cur_reqs.get(pn), want_reqs.get(pn)
                if current == wanted: continue
                pkg = PythonPackage(pn, current, wanted)
                pkg.add_urls()
                pkgs.append(pkg)
            if not pkgs: return
            self.section(p.name)
            self.report_packages(pkgs)

    reqs_pkg_version_re = re.compile(r'(?m)^([^\s#=]+)==([^\s;]+)(?:\s|$)')

    def parse_requirements(self, text):
        reqs = {}
        for m in self.reqs_pkg_version_re.finditer(text): reqs[m[1]] = m[2]
        return reqs

    def report_packages(self, pkgs):
        pkgs.sort(key=lambda p: p.name)
        for pkg in pkgs:
            pkg.report(self.opts.stdout, self.opts.open, self.opts.cooldown)


forges = {
    re.compile(r'\bhttps://github\.com/([^/]+/[^/.]+)'): {
        'releases': lambda m: f'https://github.com/{m[1]}/releases',
        'diff': lambda m, c, w: f'https://github.com/{m[1]}/compare/{c}..{w}',
    },
    re.compile(r'\bhttps://code\.haverbeke\.berlin/([^/]+/[^/.]+)'): {
        'releases': lambda m: f'https://code.haverbeke.berlin/{m[1]}/tags',
        'diff': lambda m, c, w:
            f'https://code.haverbeke.berlin/{m[1]}/compare/{c}..{w}',
    },
}


class Package:
    def __init__(self, name, current, wanted=None):
        self.name, self.current, self.wanted = name, current, wanted

    @property
    def outdated(self): return self.wanted != self.current

    @property
    def info(self):
        if (info := self._info_cache.get(self.name)) is not None: return info
        res = self._info_cache[self.name] = util.fetch_json(self.info_url)
        return res

    def add_urls(self, urls=()):
        self.urls = {self.versions_url: None} | {u: None for u in urls}
        self.add_releases_url()
        self.add_diff_url()

    def forge_urls(self, urls):
        fn = deps.info.get(self.name, {}).get('version_tag', lambda v: str(v))
        cur, want = fn(self.current), fn(self.wanted)
        for url in urls:
            for pat, fns in forges.items():
                if (m := pat.search(url)) is not None:
                    return {
                        'releases': fns['releases'](m),
                        'diff': fns['diff'](m, cur, want),
                    }

    def report(self, o, open, cooldown):
        o.write(f"{o.LCYAN}{self.name}{o.NORM}\n")
        w = max(len(self.current), len(self.wanted))
        o.write(f"  current: {o.LGREEN}{self.current:{w}}{o.NORM}"
                f" ({format_date(self.time(self.current))})\n")
        t = self.time(self.wanted)
        color = o.LRED if t > cooldown else o.LMAGENTA
        o.write(f"  wanted : {o.LYELLOW}{self.wanted:{w}}{o.NORM} "
                f"({color}{format_date(t)}{o.NORM})\n")
        for url in self.urls:
            o.write(f"  url: {url}\n")
            if open: webbrowser.open_new_tab(url)


class NpmPackage(Package):
    _info_cache = {}

    @property
    def info_url(self): return f'https://registry.npmjs.org/{self.name}'

    def wanted_from_tag(self, tag):
        self.wanted = self.info['dist-tags'][tag]

    @property
    def versions_url(self):
        return f'https://www.npmjs.com/package/{self.name}?activeTab=versions'

    def add_releases_url(self):
        self._add_forge_url('releases')

    def add_diff_url(self):
        self._add_forge_url('diff')

    def _add_forge_url(self, key):
        for pi in (self.info, self.info.versions.get(self.wanted, ''),
                   self.info.versions.get(self.current, '')):
            if 'repository' not in pi: continue
            if (furls := self.forge_urls([pi.repository.url])) is not None:
                self.urls[furls[key]] = None
                return
        if (furls := self.forge_urls(self.urls)) is not None:
            self.urls[furls[key]] = None

    def time(self, version):
        return util.parse_time(self.info.time[version])


class PythonPackage(Package):
    _info_cache = {}

    @property
    def info_url(self): return f'https://pypi.org/pypi/{self.name}/json'

    def time(self, version):
        return max((util.parse_time(p.upload_time_iso_8601)
                    for p in self.info.releases[version]),
                   default="unknown")

    @property
    def versions_url(self):
        return f'https://pypi.org/project/{self.name}/#history'

    def add_releases_url(self):
        found = self._add_project_url('release') \
                or self._add_project_url('change') \
                or self._add_project_url('news')
        if not (self._add_forge_url('releases') or found):
            self._add_project_url('home')

    def add_diff_url(self):
        self._add_forge_url('diff')

    def _add_project_url(self, label):
        for ul, url in self.info.info.project_urls.items():
            if label in ul.lower():
                self.urls[url] = None
                return True
        return False

    def _add_forge_url(self, key):
        urls = list(self.info.info.get('project_urls', {}).values())
        if u := self.info.info.get('home_page'): urls.append(u)
        if (furls := self.forge_urls(urls)) is not None:
            self.urls[furls[key]] = None
            return True


def cmd_generate(opts):
    cli.require_common(opts)
    for name in opts.name:
        if name[:1].isdigit():
            generate_version_reqs(opts, name)
        else:
            generate_group_reqs(opts, name)


def generate_version_reqs(opts, version):
    reqs = util.requirements(pkgs=[f't-doc-common=={version}'],
                             only_pkgs=['t-doc-common'], common=opts.common)
    reqs += util.requirements(no_project=True, common=opts.common)
    (opts.common / 'config' / f'{version}.req').write_text(reqs, 'utf-8')


def generate_group_reqs(opts, group):
    reqs = util.requirements(only_groups=[group], common=opts.common)
    (opts.common / 'config' / f'{group}.req').write_text(reqs, 'utf-8')
