# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

from concurrent import futures
from http import HTTPStatus
import io
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import threading
from urllib import request

from .. import cli, util

# TODO: Handle SIGTERM

tdoc_org = 'https://rc.t-doc.org/hg'
github_org = 'https://github.com/t-doc-org'


def add_commands(parser):
    p = parser.add_parser('test', help="Test-related commands.")
    sp = p.add_subparsers(title="Sub-commands")
    sp.required = True

    p = sp.add_parser('site', help="Run tests on one or more sites.")
    p.set_defaults(handler=cmd_site)
    arg = p.add_argument
    arg('--concurrency', metavar='N', dest='concurrency', type=concurrency,
        default='auto',
        help="The number of sites to test concurrently, 'auto' to auto-detect "
             "the number of CPUs, or 'max' to test all sites concurrently "
             "(default: %(default)s).")
    arg('--interactive', action='store_true', dest='interactive',
        help="Enable interactive site testing.")
    arg('repo', metavar='REPO', nargs='*', help="A site repository to test.")
    cli.add_common_options(p)


def concurrency(v):
    if v in ('auto', 'max'): return v
    return int(concurrency)


def cmd_site(opts):
    cli.require_common(opts)
    os.chdir(opts.common)
    tests = opts.common / '_tmp' / 'tests'
    o = opts.stdout

    cfg = opts.cfg.sub('test.site')
    trusted = cfg.get('trusted', [])
    sandboxed = 'TDOC_SANDBOX' in os.environ
    if not opts.repo:
        opts.repo = cfg.get('sandboxed', []) if sandboxed else trusted
    opts.repo = sorted(set(opts.repo))
    if not opts.repo:
        raise Exception("No site repositories specified")
    elif not sandboxed and (ut := [r for r in opts.repo if r not in trusted]):
        raise Exception(
            "Refusing to test untrusted sites outside of a sandbox: "
            f"{' '.join(ut)}")

    width = max((len(repo) for repo in opts.repo), default=0)
    def label(repo):
        return f"{o.CYAN}{repo:{width}}{o.NORM} {o.LBLACK}|{o.NORM} "

    lock = threading.Lock()
    def write(text):
        with lock: opts.stdout.write(text)

    def on_error(fn, path, e):
        if path == tests: return
        try:
            # Git on Windows sets some files read-only. Set the write bit and
            # try again.
            st = os.stat(path, follow_symlinks=False)
            os.chmod(path, (st.st_mode & 0o777) | stat.S_IWUSR,
                     follow_symlinks=False)
            fn(path)
        except OSError:
            opts.stderr.write(f"ERROR: {fn.__name__}: {path}: {e}\n")
    shutil.rmtree(tests, onexc=on_error)
    tests.mkdir(parents=True, exist_ok=True)
    try:
        write(f"{o.BOLD}Building wheel{o.NORM}\n")
        wheel = build_wheel(tests, opts)

        # Run tests.
        if opts.concurrency == 'auto':
            max_workers = pc if (pc := os.process_cpu_count()) is not None \
                          else c if (c := os.cpu_count()) is not None else None
        elif opts.concurrency == 'max':
            max_workers = len(opts.repo)
        else:
            max_workers = opts.concurrency
        tasks = {}
        with futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
            for repo in opts.repo:
                def test(repo=repo):
                    prefix = label(repo)
                    run_tests(tests, repo, wheel, lambda t: write(prefix + t),
                              opts)
                tasks[repo] = ex.submit(test)

        # Display output of failures.
        for repo in opts.repo:
            if (e := tasks[repo].exception()) is None: continue
            se = str(e)
            eol = "" if se.endswith("\n") else "\n"
            write(f"\n{o.LBLACK}{'=' * 79}{o.NORM}\n"
                  f"{label(repo)}{o.LRED}FAIL{o.NORM}\n"
                  f"{o.LBLACK}{'=' * 79}{o.NORM}\n{se}{eol}")

        # Display summary.
        write("\n")
        for repo in opts.repo:
            t = tasks[repo]
            e = t.exception()
            result = f'{o.LGREEN}PASS{o.NORM}' if e is None \
                     else f'{o.LRED}FAIL{o.NORM}'
            write(f"{label(repo)}{result}\n")
    finally:
        shutil.rmtree(tests, onexc=on_error)
    return 1 if any(t.exception() is not None for t in tasks.values()) else 0


wheel_re = re.compile(r't_doc_common-[^ ]+\.whl')

def build_wheel(tests, opts):
    p = util.run_uv('build', f'--python={sys.executable}', f'--out-dir={tests}',
                    common=opts.common, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, text=True)
    o = opts.stdout
    if (m := wheel_re.search(p.stdout)) is None:
        raise Exception(
            f"{o.BOLD}Failed to determine wheel name from 'uv build' "
            f"output:{o.NORM}\n{p.stdout}")
    wheel = tests / m.group(0)
    if not wheel.is_file(): raise Exception("Wheel not found")
    return wheel


serving_re = re.compile(r'(?m)^Serving at <([^>]+)>$')


def run_tests(tests, repo, wheel, write, opts):
    # Clone the document repository.
    repo_dir = tests / repo
    o = opts.stdout

    def run(*args, cmd=None, **kwargs):
        try:
            return util.run(*args, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, check=True,
                            **kwargs)
        except subprocess.CalledProcessError as e:
            raise Exception(
                f"{o.BOLD}Command failed:{o.NORM} exit status: {e.returncode}\n"
                f"{o.BOLD}Command:{o.NORM}"
                f" {shlex.join(str(a) for a in (cmd or args))}\n"
                f"{o.BOLD}Output:{o.NORM}\n{e.output}")

    write("Cloning\n")
    try:
        util.run('git', 'clone', '--branch=main', f'{github_org}/{repo}',
                 repo_dir, env=os.environ | {'GIT_ASKPASS': 'true'},
                 capture_output=True, check=True)
    except subprocess.CalledProcessError:
        run('hg', 'clone', '--updaterev=main', f'{tdoc_org}/{repo}',
            repo_dir)

    def vrun(*args, out=(), **kwargs):
        p = run(sys.executable, '-P', repo_dir / 'run.py', f'--version={wheel}',
                '--', *args, cwd=repo_dir, cmd=args)
        for regex in out:
            if not re.search(regex, p.stdout, re.MULTILINE):
                raise Exception(
                    f"{o.BOLD}Command:{o.NORM}"
                    f" {shlex.join(str(a) for a in args)}\n"
                    f"{o.BOLD}Regex:{o.NORM} {regex}\n"
                    f"{o.BOLD}Output:{o.NORM}\n{p.stdout}")
        return p.stdout

    # Run CLI tests.
    exercise_cli(repo_dir, write, opts, vrun)

    # Run the local server, wait for it to serve or exit.
    write("Running local server\n")
    args = ['tdoc', 'site', 'serve', '--debug', '--exit-on-failure']
    if opts.interactive: args += ['--exit-on-idle=2', '--open']
    # TODO: Manage server process in a background thread
    error = None
    p = subprocess.Popen(
        (sys.executable, '-P', repo_dir / 'run.py', f'--version={wheel}',
         '--', *args),
        cwd=repo_dir, text=True, bufsize=1, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        out = io.StringIO()
        for line in p.stdout:
            if out is None:
                write(line)
                continue
            out.write(line)
            if (m := serving_re.match(line)) is None: continue
            write(line.replace(m[1], f'{o.LBLUE}{m[1]}{o.NORM}'))
            base = m[1].rstrip('/')
            out = None

            def urlopen(url, json=None, **kwargs):
                data = None
                headers = {}
                if json is not None:
                    data = util.to_json(json).encode('utf-8')
                    headers['Content-Type'] = 'application/json'
                    headers['Content-Length'] = str(len(data))
                req = request.Request(f'{base}{url}', data=data,
                                      headers=headers)
                with request.urlopen(req, **kwargs) as f:
                    data = f.read()
                return HTTPStatus(f.status), f.headers, data

            # Run server tests.
            exercise_server(write, opts, urlopen)
            if not opts.interactive:
                write("Terminating local server\n")
                urlopen('/_api/terminate', json={'rc': 0})
    except BaseException as e:
        error = e
    finally:
        if error is not None:
            write("Killing local server\n")
            p.terminate()
        write("Waiting for local server termination\n")
        if (rc := p.wait()) != 0 and error is None:
            output = f"\n{o.BOLD}Output:{o.NORM}\n{out.getvalue()}" \
                     if out is not None else ""
            raise Exception(
                f"{o.BOLD}Server failed:{o.NORM} exit status: {rc}{output}")
        if error is not None: raise error


def exercise_cli(repo_dir, write, opts, vrun):
    # Get version information. This creates the venv.
    write("Getting version information\n")
    vrun('tdoc', 'version', '--debug')

    # TODO: Exercise deps sub-commands.

    # Build the HTML.
    write("Building HTML\n")
    vrun('tdoc', 'site', 'build', '--debug', 'html')

    # Clean the HTML output.
    write("Cleaning HTML output\n")
    vrun('tdoc', 'site', 'clean', '--debug')

    # Create the log database.
    write("Setting up logging\n")
    (repo_dir / 'tmp').mkdir()
    (repo_dir / 'tdoc.local.toml').write_text("""\
[deployment]
scheme = "http"
domain = "localhost"

[logging]
level = "DEBUG"
format = "{asctime} {leveli} {ctx} {name} {message}"

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
    vrun('tdoc', 'log', 'create', '--debug', '--local', '--version=1', out=[
        r'^Created \(version: 1\): .*log\.sqlite$',
    ])
    vrun('tdoc', 'log', 'upgrade', '--debug', '--version=2', out=[
        r'^Upgrading \(version: 1\): .*log\.sqlite$',
        r'^ *Backing up database to: .*log\.sqlite'
            r'\.\d{4}-\d{2}-\d{2}\.\d{2}-\d{2}-\d{2}\.\d{6}$',
    ])
    # TODO: Upgrade to latest version
    vrun('tdoc', 'log', 'upgrade', '--debug', out=[
        r'^Already up-to-date \(version: \d+\): .*log\.sqlite$',
    ])

    # Create the store.
    write("Creating store\n")
    vrun('tdoc', 'store', 'create', '--debug', '--local', '--version=3', out=[
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
    write("Interacting with store\n")
    vrun('tdoc', 'user', 'create', '--debug', 'test-user')
    vrun('tdoc', 'user', 'list', '--debug', out=[
        r'^admin +0x[0-9a-f]+ +created: ',
        r'^test-user +0x[0-9a-f]+ +created: ',
    ])
    vrun('tdoc', 'group', 'add', '--debug', '--users=test-user', 'users')
    vrun('tdoc', 'group', 'add', '--debug', '--users=admin',
         '--groups=users', 'test-group')
    vrun('tdoc', 'user', 'memberships', '--debug', out=[
        r'^admin +0x[0-9a-f]+ +\*\n +test-group\n',
        r'^test-user +0x[0-9a-f]+ +test-group  \(transitive\)\n +users\n',
    ])
    vrun('tdoc', 'group', 'list', '--debug', out=[
        r'^\*\ntest-group\nusers\n',
    ])
    vrun('tdoc', 'group', 'members', '--debug', out=[
        r'^\* +user +admin\n',
        r'^test-group +group +users\n +user +admin\n'
            r' +user +test-user  \(transitive\)\n',
        r'^users +user +test-user\n',
    ])
    vrun('tdoc', 'group', 'memberships', '--debug', out=[
        r'^users +test-group\n',
    ])
    vrun(
        'tdoc', 'site', 'setup', '--debug', '--origin=http://test',
        '--clone=', '--users=foo,bar', '--groups=users', out=[
            r'^bar +0x[0-9a-f]+ +http://localhost#\?token=[a-zA-Z0-9-_]{43,}\n',
            r'^foo +0x[0-9a-f]+ +http://localhost#\?token=[a-zA-Z0-9-_]{43,}\n',
        ])
    vrun('tdoc', 'user', 'memberships', '--debug', '--origin=http://test', out=[
        r'^admin +0x[0-9a-f]+ +\*\n +test-group\n',
        r'^bar +0x[0-9a-f]+ +test-group  \(transitive\)\n +users\n',
        r'^foo +0x[0-9a-f]+ +test-group  \(transitive\)\n +users\n',
        r'^test-user +0x[0-9a-f]+ +test-group  \(transitive\)\n +users\n',
    ])
    vrun('tdoc', 'group', 'remove', '--debug', '--users=admin,test-user',
         '--groups=users', 'test-group')
    vrun('tdoc', 'repo', 'auth', '--enable', 'test-user')
    vrun('tdoc', 'repo', 'list-users', out=[
        r'^test-user +0x[0-9a-f]+ +access: enabled +password: \[none\]\n',
    ])
    vrun('tdoc', 'token', 'create', '--debug', 'test-user')
    vrun('tdoc', 'token', 'list', '--debug', out=[
        r'^admin +0x[0-9a-f]+ +http://localhost#\?token=admin\n +created: ',
        r'^(test-user +0x[0-9a-f]+'
            r' +http://localhost#\?token=[a-zA-Z0-9-_]{43,}\n'
            r' +created: [^,]*\n){2}',
    ])
    vrun('tdoc', 'token', 'expire', '--debug', '--users', 'test-user')
    vrun('tdoc', 'token', 'list', '--debug', '--expired', out=[
        r'^(test-user +0x[0-9a-f]+'
            r' +http://localhost#\?token=[a-zA-Z0-9-_]{43,}\n'
            r' +created: [^,]*, expires: .*\n){2}',
    ])
    vrun('tdoc', 'store', 'backup', '--debug', out=[
        r'^Backing up to: .*store\.sqlite'
            r'\.\d{4}-\d{2}-\d{2}\.\d{2}-\d{2}-\d{2}\.\d{6}$',
    ])

    # Query the log database.
    write("Querying log database\n")
    vrun(
        'tdoc', 'log', 'query', '--debug', '--utc', '--begin=10m', '--end=0s',
        '--level=info', "--where=record ->> '$.name' = 'tdoc.common.cli'",
        '--format=sub={args[argv][1]}',
        out=[
            r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z '
            r'I main tdoc.common.cli CLI: .* store create .*\n  sub=store\n',
        ])
    vrun('tdoc', 'log', 'backup', '--debug', out=[
        r'^Backing up to: .*log\.sqlite'
            r'\.\d{4}-\d{2}-\d{2}\.\d{2}-\d{2}-\d{2}\.\d{6}$',
    ])


def exercise_server(write, opts, urlopen):
    # Check server health.
    write("Checking local server health\n")
    urlopen('/_api/health')
