#!/usr/bin/env python
# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import json
import os
import pathlib
import sys
from urllib import request
import webbrowser

# TODO: node.js: npm outdated
# TODO: Python: tools/requirements.sh uv, uv lock --upgrade
# TODO: GitHub actions


def main(argv, stdin, stdout, stderr):
    checker = Checker(argv, stdout, stderr)
    checker.check_deps()


class Checker:
    def __init__(self, argv, stdout, stderr):
        self.base = pathlib.Path(argv[0]).parent.resolve().parent
        self.stdout, self.stderr = stdout, stderr
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

    def check_deps(self):
        path = self.base / 'tdoc' / 'common' / 'deps.py'

        mod = type(sys)('tdoc.common.deps')
        code = compile(path.read_text('utf-8'), str(path), 'exec')
        exec(code, mod.__dict__)

        for info in mod.info.values():
            name, version = info['name'], info['version']
            pi = self.npm_package_info(name)
            tag = info['tag']
            tag_version = pi['dist-tags'][tag]
            if version == tag_version: continue
            self.stdout.write(f"{name}\n")
            w1 = max(len('current'), len(tag))
            w2 = max(len(version), len(tag_version))
            self.stdout.write(
                f"  {'current':{w1}}: {version:{w2}} ({pi.time[version]})\n")
            self.stdout.write(
                f"  {tag:{w1}}: {tag_version:{w2}} ({pi.time[tag_version]})\n")
            if self.open:
                for url in info['docs']:
                    if not isinstance(url, str): url = url(name)
                    webbrowser.open_new_tab(url)

    def npm_package_info(self, name):
        with request.urlopen(f'https://registry.npmjs.org/{name}',
                             timeout=30) as f:
            return json.load(f, object_pairs_hook=Namespace)


class Namespace(dict):
    def __getattr__(self, name):
        return self[name]


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
