#!/usr/bin/env python
# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

from concurrent import futures
import io
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import sys
import threading

github_org = 'https://github.com/t-doc-org'


class Error(Exception): pass


def main(argv, stdin, stdout, stderr):
    base = pathlib.Path(argv[0]).parent.resolve().parent
    os.chdir(base)
    tests = base / 'tmp' / 'tests'

    # Find repository names and URLs.
    names = argv[1:]
    if not names:
        names = [d.name for d in base.parent.iterdir()
                 if (d / 'run.py').exists()
                    and (d / 'docs' / 'conf.py').exists()]
    repos = {n: f'{github_org}/{n}' for n in names}
    width = max(len(repo) for repo in repos)
    def label(repo): return f"{repo:{width}} | "

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
        wheel = build_wheel(tests)

        # Run tests.
        port = 8001
        tasks = {}
        with futures.ThreadPoolExecutor(max_workers=len(repos)) as ex:
            for repo, url in sorted(repos.items()):
                def test(repo=repo, port=port):
                    run_tests(tests, repo, label(repo), url, port, wheel, write)
                tasks[repo] = ex.submit(test)
                port += 1

        # Display output of failures.
        for repo in sorted(repos):
            t = tasks[repo]
            if (e := t.exception()) is None: continue
            se = str(e)
            eol = "" if se.endswith("\n") else "\n"
            write(f"\n{'=' * 79}\n{label(repo)}FAIL\n{'=' * 79}\n{se}{eol}")

        # Display summary.
        write("\n")
        for repo in sorted(repos):
            t = tasks[repo]
            e = t.exception()
            write(f"{label(repo)}{'PASS' if e is None else 'FAIL'}\n")
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


serving_re = re.compile(r'(?m)^Serving at <([^>]+)>$')

def run_tests(tests, repo, label, url, port, wheel, write):
    # Clone the document repository.
    repo_dir = tests / repo
    write(f"{label}Cloning\n")
    run('git', 'clone', url, repo_dir, '--branch', 'main')

    def vrun(*args, wait=True, **kwargs):
        p = subprocess.Popen(
            (repo_dir / 'run.py',) + args,
            cwd=repo_dir, env={**os.environ, 'TDOC_VERSION': str(wheel)},
            text=True, bufsize=1, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if wait:
            out, _ = p.communicate()
            if p.wait() != 0:
                raise Error(f"Command failed: {shlex.join(args)}\n\n{out}")
        return p

    # Get version information. This creates the venv.
    write(f"{label}Getting version information\n")
    vrun('tdoc', 'version', '--debug')

    # Build the HTML.
    write(f"{label}Building HTML\n")
    vrun('tdoc', 'build', '--debug', 'html')

    # Clean the HTML output.
    write(f"{label}Cleaning HTML output\n")
    vrun('tdoc', 'clean', '--debug')

    # Create the store.
    # TODO: Create at version n > 1, then upgrade
    write(f"{label}Creating store\n")
    vrun('tdoc', 'store', 'create', '--debug', '--dev')

    # TODO: Run various commands that access the store

    # Run the local server, wait for it to serve or exit.
    write(f"{label}Running local server\n")
    p = vrun('tdoc', 'serve', '--debug', '--exit-on-failure',
             '--exit-on-idle=2', '--open', f'--port={port}', wait=False)
    try:
        out = io.StringIO()
        for line in p.stdout:
            if out is None:
                write(f"{label}{line}")
                continue
            out.write(line)
            if (m := serving_re.match(line)) is None: continue
            write(f"{label}{line}")
            out = None
    finally:
        write(f"{label}Local server terminated\n")
        if p.wait() == 0: return
        output = f"\n\n{out.getvalue()}" if out is not None else ""
        raise Error(f"The local server has terminated with an error.{output}")


class CommandFailed(Error):
    def __init__(self, e):
        super().__init__(
            f"Command failed with return code {e.returncode}\n"
            f"Command: {shlex.join(str(a) for a in e.cmd)}\n"
            f"\n{e.output}")


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
