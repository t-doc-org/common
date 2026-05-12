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

from .. import cli, util

# TODO: Run sandbox under gVisor

name_base = 't-doc'
default_port = 9000
default_ports = 20

label_base = 'org.t-doc.sandbox'


def add_commands(parser):
    p = parser.add_parser('sandbox', help="Sandbox-related commands.")
    sp = p.add_subparsers(title="Sub-commands")
    sp.required = True

    p = sp.add_parser('build', help="Build a sandbox container image.")
    p.set_defaults(handler=cmd_build)
    add_image_options(p)
    cli.add_common_options(p)

    p = sp.add_parser('shell', help="Start a shell in a sandbox.")
    p.set_defaults(handler=cmd_shell)
    add_container_options(p)
    add_image_options(p)
    cli.add_common_options(p)

    p = sp.add_parser('stop', help="Stop sandbox containers.")
    p.set_defaults(handler=cmd_stop)
    arg = p.add_argument
    arg('--all', action='store_true', dest='all',
        help="Stop all sandbox containers.")
    add_image_options(p)
    cli.add_common_options(p)


def add_image_options(parser):
    arg = parser.add_argument_group("Image options").add_argument
    arg('--python', metavar='VERSION', dest='python', default=None,
        help="The version of Python to install in the sandbox (default: "
             "python.recommend in run.toml). ")


def add_container_options(parser):
    arg = parser.add_argument_group("Container options").add_argument
    arg('--port', metavar='PORT', dest='port', type=int, default=None,
        help="The default port to use for serving in the sandbox "
             f"(default: {default_port}).")
    arg('--ports', metavar='N', dest='ports', type=int, default=None,
        help=f"The number of ports to publish (default: {default_ports}).")
    arg('--uid', metavar='N', dest='uid', type=int, default=1000,
        help="The UID under which to run the shell (default: %(default)s).")
    arg('--userns', metavar='MODE', dest='userns', default='nomap',
        help="The user namespace mode for the sandbox container "
             "(default: %(default)s).")


def set_default_python(opts):
    cli.require_common(opts)
    if opts.python is None:
        run_toml = util.read_toml(opts.common / 'config' / 'run.toml')
        opts.python = run_toml['python']['recommend']


def container_name(opts):
    return f'{name_base}-{opts.python}'


def image_name(opts):
    return f'localhost/{container_name(opts)}:latest'


def port_range(opts):
    port = p if (p := opts.port) is not None else default_port
    ports = p if (p := opts.ports) is not None else default_ports
    return f'{port}-{port + ports - 1}'


def cmd_build(opts):
    set_default_python(opts)
    build_image(opts)
    prune_images(filter=f'label={label_base}.python={opts.python}')


def cmd_shell(opts):
    set_default_python(opts)
    container_filter = f'name=^{re.escape(container_name(opts))}$'
    restart = False
    cdata = list_containers(filter=container_filter)
    running = bool(cdata)
    if (opts.port is not None or opts.ports is not None) \
            and cdata and label(cdata[0], 'port_range') != port_range(opts):
        restart = True
    o = opts.stderr
    if restart:
        o.write(f"{o.BOLD}Port range changed; stopping container{o.NORM}\n")
        stop_containers(filter=container_filter)
        running = False
    if not running:
        if not list_images(filter=f'reference={image_name(opts)}'):
            o.write(f"{o.BOLD}Building image{o.NORM}\n")
            build_image(opts)
            prune_images(filter=f'label={label_base}.python={opts.python}')
        o.write(f"{o.BOLD}Starting container{o.NORM}\n")
        start_container(opts, opts.common.parent)
    shell_in_container(opts)


def cmd_stop(opts):
    set_default_python(opts)
    filter = f'name=^{re.escape(name_base)}-[0-9]+(\\.[0-9]+)*$' if opts.all \
             else f'name=^{re.escape(container_name(opts))}$'
    stop_containers(filter=filter)


def list_images(*, filter=()):
    return util.run_json('podman', 'image', 'list', *filter_args(filter),
                         '--format=json')


def prune_images(*, filter=()):
    util.run('podman', 'image', 'prune', *filter_args(filter), '--force',
             stdout=subprocess.DEVNULL)


def build_image(opts):
    ctx = pathlib.Path(__file__).resolve().parent
    util.run('podman', 'image', 'build',
             f'--tag={image_name(opts)}', '--pull', '--no-cache',
             f'--file={ctx / 'sandbox.Containerfile'}',
             f'--from=docker.io/python:{opts.python}-slim',
             f'--label={label_base}.python={opts.python}',
             f'--build-context=config={opts.common / 'config'}',
             ctx)


def list_containers(*, filter=()):
    return util.run_json('podman', 'container', 'list', *filter_args(filter),
                         '--format=json')


def stop_containers(*, filter=()):
    util.run('podman', 'container', 'stop', *filter_args(filter),
             stdout=subprocess.DEVNULL)


def start_container(opts, base):
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
        if repo == opts.common:
            mounts.extend([
                tmpfs(repo, 'dist'),
                tmpfs(repo, 'node_modules'),
                tmpfs(repo, 'tdoc/common/static.gen'),
            ])

    # Run a script that terminates some duration after the last shell exits.
    prange = port_range(opts)
    util.run('podman', 'container', 'run',
             f'--name={container_name(opts)}', f'--userns={opts.userns}',
             '--init', '--detach', '--rm',
             '--security-opt=no-new-privileges', '--cap-drop=ALL', *mounts,
             f'--publish=127.0.0.1:{prange}:{prange}/tcp',
             f'--label={label_base}.port_range={prange}',
             f'--label={label_base}.python={opts.python}',
             image_name(opts),
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


def shell_in_container(opts):
    name = container_name(opts)
    util.run('podman', 'container', 'exec', '--interactive', '--tty',
             f'--user={opts.uid}', '--workdir=/t-doc',
             f'--env=TDOC_DEFAULT_PORT={opts.port}',
             f'--env=TDOC_SANDBOX={name}',
             f'--env=TERM={os.environ['TERM']}',
             name, '/bin/bash',
             stdin=opts.stdin, monitor=util.terminate_on(signal.SIGTERM))


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
