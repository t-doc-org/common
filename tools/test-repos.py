#!/usr/bin/env python
# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

from concurrent import futures
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import sys
import threading


repos = {
    'common': 'https://github.com/t-doc-org/common',
    'informatique': 'https://github.com/t-doc-org/informatique',
    'janm': 'https://github.com/t-doc-org/janm',
    't-doc-org.github.io': 'https://github.com/t-doc-org/t-doc-org.github.io',
}


class Error(Exception): pass


def main(argv, stdin, stdout, stderr):
    base = pathlib.Path(argv[0]).resolve().parent.parent
    os.chdir(base)
    tests = base / 'tmp' / 'tests'

    lock = threading.Lock()
    def write(text):
        with lock: stdout.write(text)

    def on_error(fn, path, e):
        if path == tests: return
        stderr.write(f"ERROR: {fn}: {path}: {e}\n")
    shutil.rmtree(tests, onexc=on_error)
    tests.mkdir(parents=True, exist_ok=True)
    try:
        write("Building wheel\n")
        wheel = build_wheel(tests, )

        # Run tests.
        port = 8000
        tasks = {}
        with futures.ThreadPoolExecutor(max_workers=len(repos)) as ex:
            for repo, url in repos.items():
                def test(repo=repo, port=port):
                    run_tests(tests, repo, url, port, wheel, write)
                tasks[repo] = ex.submit(test)
                port += 1

        # Display output of failures.
        for repo in repos:
            t = tasks[repo]
            if (e := t.exception()) is None: continue
            write(f"\n{'=' * 79}\n{repo}: FAIL\n{e}")

        # Display summary.
        write("\n")
        for repo in repos:
            t = tasks[repo]
            e = t.exception()
            write(f"{repo}: {'PASS' if e is None else 'FAIL'}\n")
    finally:
        shutil.rmtree(tests, onexc=on_error)
    return 1 if any(t.exception() is not None for t in tasks.values()) else 0


wheel_re = re.compile(r't_doc_common-[^ ]+\.whl')

def build_wheel(tests):
    out = run(sys.executable, '-P', '-m', 'build', '--no-isolation',
              '--outdir', tests)
    if (m := wheel_re.search(out)) is None:
        raise Exception("Failed to determine wheel name")
    wheel = tests / m.group(0)
    if not wheel.is_file(): raise Exception("Wheel not found")
    return wheel


def run_tests(tests, repo, url, port, wheel, write):
    repo_dir = tests / repo
    write(f"{repo}: Cloning\n")
    run('git', 'clone', url, repo_dir, '--branch', 'main')
    write(f"{repo}: Building\n")
    env = os.environ.copy()
    env['TDOC_VERSION'] = str(wheel)
    run(repo_dir / 'run.py', 'build', 'html', env=env)


class CommandFailed(Error):
    def __init__(self, e):
        super().__init__(
            f"Command failed with return code {e.returncode}\n"
            f"Command: {shlex.join(str(a) for a in e.cmd)}\n"
            f"Output:\n{e.output}")


def run(*args, **kwargs):
    try:
        return subprocess.run(args, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, check=True, **kwargs).stdout
    except subprocess.CalledProcessError as e:
        raise CommandFailed(e)


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv, sys.stdin, sys.stdout, sys.stderr))
    except SystemExit:
        raise
    except KeyboardInterrupt:
        sys.exit(1)
    except Error as e:
        sys.stderr.write(f'\n{e}\n')
        sys.exit(1)
