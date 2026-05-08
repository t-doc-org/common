#!/usr/bin/env python
# Copyright 2026 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import contextlib
import json
import os
import pathlib
import signal
import subprocess
import sys
import tomllib

# TODO: Add --rebuild
# TODO: Add --stop
# TODO: Add --default-port


def main(argv, stdin, stdout, stderr):
    common = pathlib.Path(argv[0]).parent.resolve().parent
    base = common.parent

    # Parse command-line arguments.
    debug = False
    python = run_toml(common)['python']['recommend']
    uid = 1000
    userns = 'nomap'
    i = 1
    while True:
        if i >= len(argv) or not (arg := argv[i]).startswith('--'):
            argv = argv[:1] + argv[i:]
            break
        elif arg == '--':
            argv = argv[:1] + argv[i + 1:]
            break
        elif arg == '--debug':
            debug = True
        elif arg.startswith('--python='):
            python = arg[9:]
        elif arg.startswith('--uid='):
            uid = arg[6:]
        elif arg.startswith('--userns='):
            userns = arg[9:]
        else:
            raise Exception(f"Unknown option: {arg}")
        i += 1

    # Manage image and container.
    name = f't-doc-{python}'
    if not list_containers(f'name={name}'):
        if not list_images(f'reference={name}'):
            create_image(common, name=name, python=python)
        start_container(base, common, name=name, image=name, userns=userns)

    # Start a new shell in the container.
    return shell_in_container(name, uid=uid)


def run_toml(common):
    with (common / 'config' / 'run.toml').open('rb') as f:
        return tomllib.load(f)


def list_images(filter):
    return run_json('podman', 'image', 'list', f'--filter={filter}',
                    '--format=json')


def create_image(common, name, *, python):
    run('podman', 'build', f'--tag={name}',
        f'--file={common / 'tools' / 'sandbox.Containerfile'}',
        f'--from=docker.io/python:{python}-slim',
        common / 'tools')


def list_containers(filter):
    return run_json('podman', 'container', 'list', f'--filter={filter}',
                    '--format=json')


def start_container(base, common, *, name, image, userns):
    mounts = [f'--mount=type=bind,src={base},dst=/t-doc,ro=true']
    for repo in sorted(base.iterdir()):
        if not (repo / 'run.py').is_file() \
                and (repo / 'docs' / 'conf.py').is_file():
            continue
        mounts.extend([
            tmpfs(repo, '_build'),
            tmpfs(repo, '_cache'),
            tmpfs(repo, '_tmp'),
            tmpfs(repo, '_venv'),
        ])
        # TODO: Use writable_by_other()
        if (repo / '_data').is_dir(follow_symlinks=False):
            mounts.append(bind(repo, '_data'))
        if repo == common:
            mounts.extend([
                tmpfs(repo, 'dist'),
                tmpfs(repo, 'node_modules'),
                tmpfs(repo, 'tdoc/common/static.gen'),
            ])
    # TODO: Poll for open sessions, terminate 1h after last session
    # TODO: Use --init?
    # https://oneuptime.com/blog/post/2026-03-16-run-container-init-process-podman/view
    return run('podman', 'run', f'--name={name}', f'--userns={userns}', '--rm',
               '--detach', *mounts,
               '--publish=127.0.0.1:9000-9019:9000-9019/tcp',
               f'localhost/{image}:latest',
               '/bin/sleep', 'infinity')


def shell_in_container(name, *, uid):
    return run_long('podman', 'exec', '--interactive', '--tty',
                    f'--user={uid}', '--workdir=/t-doc',
                    f'--env=TERM={os.environ['TERM']}',
                    f'--env=CONTAINER_NAME={name}',
                    name, '/bin/bash')


def writable_by_other(path):
    with contextlib.suppress(OSError):
        st = path.stat(follow_symlinks=False)
        return stat.S_ISDIR(st.st_mode) \
               and stat.S_IMODE(st.st_mode) & stat.S_IWOTH
    return False


def tmpfs(repo, name):
    (repo / name).mkdir(exist_ok=True)
    return f'--mount=type=tmpfs,dst=/t-doc/{repo.name}/{name},' \
           'notmpcopyup,tmpfs-mode=1777'


def bind(repo, name):
    return f'--mount=type=bind,src={repo / name},' \
           f'dst=/t-doc/{repo.name}/{name},ro=false'


def run(*args, **kwargs):
    p = subprocess.run(args, stdin=subprocess.DEVNULL, **kwargs)
    if p.returncode != 0: raise Exception(p.stderr)
    return p.stdout


def run_json(*args, **kwargs):
    return json.loads(run(*args, capture_output=True, text=True, **kwargs))


def run_long(*args, **kwargs):
    with subprocess.Popen(args) as p:
        signal.signal(signal.SIGTERM, lambda *args: p.terminate())
        try:  # Do the same as subprocess.run()
            p.communicate()
        except BaseException:
            p.kill()
            raise
    return p.poll()


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv, sys.stdin, sys.stdout, sys.stderr))
    except SystemExit:
        raise
    except KeyboardInterrupt:
        sys.exit(1)
    except BaseException as e:
        if '--debug' in sys.argv: raise
        sys.stderr.write(f'\nERROR: {e}\n')
        sys.exit(1)
