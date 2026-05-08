#!/usr/bin/env python
# Copyright 2026 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import json
import os
import pathlib
import re
import signal
import subprocess
import sys
import tomllib

label_base = 'org.t-doc.sandbox'


def main(argv, stdin, stdout, stderr):
    common = pathlib.Path(argv[0]).parent.resolve().parent
    base = common.parent

    # Parse command-line arguments.
    debug = False
    port = 9000
    ports = 20
    python = run_toml(common)['python']['recommend']
    rebuild = False
    restart = False
    stop = False
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
        elif arg.startswith('--port='):
            port = int(arg[7:])
        elif arg.startswith('--ports='):
            ports = int(arg[8:])
        elif arg.startswith('--python='):
            python = arg[9:]
        elif arg == '--rebuild':
            rebuild = True
        elif arg == '--restart':
            restart = True
        elif arg == '--stop':
            stop = True
        elif arg.startswith('--uid='):
            uid = arg[6:]
        elif arg.startswith('--userns='):
            userns = arg[9:]
        else:
            raise Exception(f"Unknown option: {arg}")
        i += 1

    # Manage image and container.
    name = f't-doc-{python}'
    image = f'localhost/{name}-{port}:latest'
    port_range = f'{port}-{port + ports - 1}'

    idata = list_images(filter=f'reference={image}')
    if idata and label(idata[0], 'port') != str(port):
        rebuild = True
    cdata = list_containers(filter=f'name={re.escape(name)}')
    if cdata and label(cdata[0], 'port_range') != port_range:
        restart = True
    running = bool(cdata)
    if stop or rebuild or restart:
        stop_containers(filter=f'name={re.escape(name)}')
        running = False
        if stop: return 0
    if not running:
        if rebuild or not list_images(filter=f'reference={image}'):
            create_image(common, name=image, python=python, port=port)
            prune_images(filter=[f'label={label_base}.python={python}',
                                 f'label={label_base}.port={port}'])
        start_container(base, common, name=name, image=image, userns=userns,
                        python=python, port_range=port_range)

    # Start a new shell in the container.
    return shell_in_container(name, uid=uid)


def run_toml(common):
    with (common / 'config' / 'run.toml').open('rb') as f:
        return tomllib.load(f)


def list_images(*, filter=()):
    return run_json('podman', 'image', 'list', *filter_args(filter),
                    '--format=json')


def prune_images(*, filter=()):
    run('podman', 'image', 'prune', *filter_args(filter), '--force',
        stdout=subprocess.DEVNULL)


def create_image(common, name, *, python, port):
    run('podman', 'image', 'build',
        f'--tag={name}', '--pull', '--no-cache',
        f'--file={common / 'tools' / 'sandbox.Containerfile'}',
        f'--from=docker.io/python:{python}-slim',
        f'--label={label_base}.port={port}',
        f'--label={label_base}.python={python}',
        f'--env=TDOC_DEFAULT_PORT={port}',
        common / 'tools')


def list_containers(*, filter=()):
    return run_json('podman', 'container', 'list', *filter_args(filter),
                    '--format=json')


def stop_containers(*, filter=()):
    run('podman', 'container', 'stop', '--time=0', *filter_args(filter),
        stdout=subprocess.DEVNULL)


def start_container(base, common, *, name, image, userns, python, port_range):
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
        if (repo / '_data').is_dir(follow_symlinks=False):
            mounts.append(bind(repo, '_data'))
        if repo == common:
            mounts.extend([
                tmpfs(repo, 'dist'),
                tmpfs(repo, 'node_modules'),
                tmpfs(repo, 'tdoc/common/static.gen'),
            ])

    # TODO: Use --init?
    # https://oneuptime.com/blog/post/2026-03-16-run-container-init-process-podman/view

    # Run a script that terminates some duration after the last shell exits.
    run('podman', 'container', 'run',
        f'--name={name}', f'--userns={userns}', '--detach', '--rm', *mounts,
        f'--publish=127.0.0.1:{port_range}:{port_range}/tcp',
        f'--label={label_base}.port_range={port_range}',
        f'--label={label_base}.python={python}',
        image,
        '/usr/local/bin/python', '-P', '-c', """\
import pathlib
import time
delay = 10 * 60
proc = pathlib.Path('/proc')
stop = (now := time.time()) + delay
while now < stop:
    time.sleep(min(stop - now, max(delay / 100, 1)))
    now = time.time()
    if any(p.read_bytes().startswith(b'/bin/bash\\0')
           for p in proc.glob('[0-9]*/cmdline')):
        stop = now + delay
""",
        stdout=subprocess.DEVNULL)


def shell_in_container(name, *, uid):
    return run_long('podman', 'container', 'exec', '--interactive', '--tty',
                    f'--user={uid}', '--workdir=/t-doc',
                    f'--env=CONTAINER_NAME={name}',
                    f'--env=TERM={os.environ['TERM']}',
                    name, '/bin/bash')


def filter_args(filter):
    if isinstance(filter, str): return [f'--filter={filter}']
    return [f'--filter={f}' for f in filter]


def label(data, name):
    if (labels := data.get('Labels')) is None: return
    return labels.get(f'{label_base}.{name}')


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
