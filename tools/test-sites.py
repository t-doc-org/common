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
import stat
import subprocess
import sys
import threading

cspace_net = 'ssh://rc.c-space.net//home/rc/hg/t-doc'
github_org = 'https://github.com/t-doc-org'


class Error(Exception): pass


def main(argv, stdin, stdout, stderr):
    base = pathlib.Path(argv[0]).parent.resolve().parent
    os.chdir(base)
    tests = base / 'tmp' / 'tests'

    # Find repository names and URLs.
    repos = argv[1:]
    if not repos:
        repos = [d.name for d in base.parent.iterdir()
                 if (d / 'run.py').exists()
                    and (d / 'docs' / 'conf.py').exists()]
    repos.sort()
    width = max(len(repo) for repo in repos)
    def label(repo): return f"{repo:{width}} | "

    lock = threading.Lock()
    def write(text):
        with lock: stdout.write(text)

    def on_error(fn, path, e):
        if path == tests: return
        try:
            # Git on Windows sets some files read-only. Remove the flag and
            # try again.
            os.chmod(path, stat.S_IREAD | stat.S_IWRITE, follow_symlinks=False)
            fn(path)
        except OSError:
            stderr.write(f"ERROR: {fn.__name__}: {path}: {e}\n")
    shutil.rmtree(tests, onexc=on_error)
    tests.mkdir(parents=True, exist_ok=True)
    try:
        write("Building wheel\n")
        wheel = build_wheel(tests)

        # Run tests.
        tasks = {}
        with futures.ThreadPoolExecutor(max_workers=len(repos)) as ex:
            for repo in repos:
                def test(repo=repo):
                    run_tests(tests, repo, label(repo), wheel, write)
                tasks[repo] = ex.submit(test)

        # Display output of failures.
        for repo in repos:
            t = tasks[repo]
            if (e := t.exception()) is None: continue
            se = str(e)
            eol = "" if se.endswith("\n") else "\n"
            write(f"\n{'=' * 79}\n{label(repo)}FAIL\n{'=' * 79}\n{se}{eol}")

        # Display summary.
        write("\n")
        for repo in repos:
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

def run_tests(tests, repo, label, wheel, write):
    # Clone the document repository.
    repo_dir = tests / repo
    write(f"{label}Cloning\n")
    if repo.endswith('-private'):
        run('hg', 'clone', '--updaterev=main', f'{cspace_net}/{repo}',
            repo_dir)
    else:
        run('git', 'clone', '--branch=main', f'{github_org}/{repo}',
            repo_dir)

    def vrun(*args, wait=True, out=(), **kwargs):
        p = subprocess.Popen(
            (sys.executable, '-P', repo_dir / 'run.py', f'--version={wheel}',
             '--') + args,
            cwd=repo_dir, text=True, bufsize=1, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if not wait: return p
        pout, _ = p.communicate()
        if p.wait() != 0:
            raise Error(f"Command: {shlex.join(args)}\nOutput:\n{pout}")
        for regex in out:
            if not re.search(regex, pout, re.MULTILINE):
                raise Error(f"Command: {shlex.join(args)}\nRegex: {regex}\n"
                            f"Output:\n{pout}")
        return pout

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
    write(f"{label}Setting up logging\n")
    (repo_dir / 'tmp').mkdir()
    (repo_dir / 'local.toml').write_text("""\
[logging]
level = "DEBUG"

[logging.stream]
enabled = true
level = "WARNING"

[[logging.files]]
path = "tmp/t-doc.log"

[[logging.databases]]
path = "tmp/log.sqlite"

[store]
path = "tmp/store.sqlite"
""")
    vrun('tdoc', 'log', 'create', '--debug', '--version=1', out=[
        r'^Created \(version: 1\): .*log\.sqlite$',
    ])
    # TODO: Test a log database upgrade
    vrun('tdoc', 'log', 'upgrade', '--debug', out=[
        r'^Already up-to-date \(version: \d+\): .*log\.sqlite$',
    ])

    # Create the store.
    write(f"{label}Creating store\n")
    vrun('tdoc', 'store', 'create', '--debug', '--dev', '--version=3', out=[
        r'^Created \(version: 3\): .*store\.sqlite$',
    ])
    vrun('tdoc', 'store', 'upgrade', '--debug', '--version=4', out=[
        r'^Upgrading \(version: 3\): .*store\.sqlite$',
        r'^ *Backing up database to: .*store\.sqlite'
            r'\.\d{4}-\d{2}-\d{2}\.\d{2}-\d{2}-\d{2}\.\d{6}$',
    ])
    vrun('tdoc', 'store', 'upgrade', '--debug', out=[
        r'^Upgrading \(version: 4+\): .*store\.sqlite$',
    ])
    vrun('tdoc', 'store', 'upgrade', '--debug', out=[
        r'^Already up-to-date \(version: \d+\): .*store\.sqlite$',
    ])

    # Run commands interacting with the store.
    write(f"{label}Interacting with store\n")
    vrun('tdoc', 'user', 'create', '--debug', 'test-user')
    vrun('tdoc', 'user', 'list', '--debug', out=[
        r'^admin +\([0-9a-f]+\) +created: ',
        r'^test-user +\([0-9a-f]+\) +created: ',
    ])
    vrun('tdoc', 'group', 'add', '--debug', '--users=admin,test-user',
         '--groups=users', 'test-group')
    vrun('tdoc', 'user', 'memberships', '--debug', out=[
        r'^admin +\*\n +test-group\n',
        r'^test-user +test-group\n',
    ])
    vrun('tdoc', 'group', 'list', '--debug', out=[
        r'^\*\ntest-group\nusers\n',
    ])
    vrun('tdoc', 'group', 'members', '--debug', out=[
        r'^\* +user +admin\n',
        r'^test-group +group +users\n +user +admin\n +user +test-user\n',
    ])
    vrun('tdoc', 'group', 'memberships', '--debug', out=[
        r'^users +test-group\n',
    ])
    vrun('tdoc', 'group', 'remove', '--debug', '--users=admin,test-user',
         '--groups=users', 'test-group')

    vrun('tdoc', 'token', 'create', '--debug', 'test-user')
    vrun('tdoc', 'token', 'list', '--debug', out=[
        r'^admin +#\?token=admin\n +created: ',
        r'^(test-user +#\?token=[a-zA-Z0-9-_]{43,}\n +created: .*\n){2}',
    ])
    vrun('tdoc', 'token', 'expire', '--debug', 'test-user')

    vrun('tdoc', 'store', 'backup', '--debug', out=[
        r'^Backing up to: .*store\.sqlite'
            r'\.\d{4}-\d{2}-\d{2}\.\d{2}-\d{2}-\d{2}\.\d{6}$',
    ])

    # Query the log database.
    write(f"{label}Querying log database\n")
    vrun(
        'tdoc', 'log', 'query', '--debug', '--utc', '--begin=10m', '--end=0s',
        '--level=info', "--where=record ->> '$.module' = 'cli'",
        '--format={asctime} {ilevel} {ctx} {module} {message}',
        out=[
            r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z I main cli CLI: .*'
                r' store create ',
        ])
    vrun('tdoc', 'log', 'backup', '--debug', out=[
        r'^Backing up to: .*log\.sqlite'
            r'\.\d{4}-\d{2}-\d{2}\.\d{2}-\d{2}-\d{2}\.\d{6}$',
    ])

    # Run the local server, wait for it to serve or exit.
    write(f"{label}Running local server\n")
    p = vrun('tdoc', 'serve', '--debug', '--exit-on-failure',
             '--exit-on-idle=2', '--open', wait=False)
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
