# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import contextlib
import datetime
import functools
import os
import pathlib
import shlex
import threading

from .. import __project__, __version__, config, console, logs, \
               store as _store, util

_log = logs.logger(__name__)


@console.main
def main(argv, stdin, stdout, stderr):
    """Run the command."""
    threading.current_thread().name = 'main'

    parser = console.get_arg_parser(stdin, stdout, stderr)(
        prog=pathlib.Path(argv[0]).name, description="Manage a t-doc site.")
    root = parser.add_subparsers(title='Sub-commands')
    root.required = True

    from . import deps, group, log, repo, sandbox, site, store, test, token, \
                  user
    deps.add_commands(root)
    group.add_commands(root)
    log.add_commands(root)
    repo.add_commands(root)
    sandbox.add_commands(root)
    site.add_commands(root)
    store.add_commands(root)
    test.add_commands(root)
    token.add_commands(root)
    user.add_commands(root)

    p = root.add_parser('version', help="Display version information.")
    p.set_defaults(handler=cmd_version)
    add_common_options(p)

    opts = parser.parse_args(argv[1:])
    if opts.config is None:
        opts.config = config.Config.find(pathlib.Path.cwd())
    opts.cfg = config.Config.load(
        opts.config.resolve() if opts.config is not None else None)
    if (fn := getattr(opts.handler, '_pre_run', None)) is not None:
        if (res := fn(opts)) is not None: return res
    with logs.configure(config=opts.cfg.sub('logging'), stderr=stderr,
                        level=logs.WARNING, stream=True, raise_exc=opts.debug,
                        on_upgrade=functools.partial(on_upgrade, opts),
                        db_logs=not getattr(opts.handler, '_disable_db_logs',
                                            False)):
        _log.info("CLI: %(cmd)s", cmd=' '.join(shlex.quote(a) for a in argv),
                  argv=argv)
        return opts.handler(opts)


def pre_run(pre):
    def deco(fn):
        fn._pre_run = pre
        return fn
    return deco


def disable_db_logs(fn):
    fn._disable_db_logs = True
    return fn


def add_common_options(parser):
    arg = parser.add_argument_group("Common options").add_argument
    arg('--color', dest='color', choices=['auto', 'false', 'true'],
        default='auto',
        help="Control the use of colors in output (default: %(default)s).")
    arg('--config', metavar='PATH', dest='config', type='path',
        default=os.environ.get('TDOC_CONFIG'),
        help="The path to the config file.")
    arg('--debug', action='store_true', dest='debug',
        help="Enable debug functionality.")
    arg('--local', action='store_true', dest='local',
        help="Create databases for local mode.")


def add_origin_option(arg):
    arg('--origin', metavar='URL', dest='origin', default='',
        help="The origin on which to operate.")


def root_origin(cfg, default=''):
    dep = cfg.sub('deployment')
    if (domain := dep.get('domain')) is None: return default
    return f'{dep.get('scheme', 'https')}://{domain}'


def require_common(opts):
    path = pathlib.Path(__file__).parent.resolve().parent.parent.parent
    with contextlib.suppress(Exception):
        data = util.read_toml(path / 'pyproject.toml')
        if data['project']['name'] == __project__:
            opts.common = path
            return
    raise Exception("This command is only available in an editable install of "
                    f"{__project__}")


def on_upgrade(opts, st, db, version, latest):
    o = opts.stdout
    if db is None:
        o.write(f"""\
{o.LYELLOW}A database needs to be created:{o.NORM} local={opts.local}
  {st.path}
Would you like to create it (y/n)? """)
    elif latest < version:
        o.write(f"""\
{o.LYELLOW}A database needs to be downgraded:{o.NORM} version\
 {o.CYAN}{version}{o.NORM} => {o.CYAN}{latest}{o.NORM}
  {st.path}
This cannot be done automatically. Please downgrade manually or restore from a
backup.
""")
        raise Exception("Aborting to prevent data loss")
    else:
        o.write(f"""\
{o.LYELLOW}A database needs to be upgraded:{o.NORM} version\
 {o.CYAN}{version}{o.NORM} => {o.CYAN}{latest}{o.NORM}
  {st.path}
Would you like to perform the upgrade (y/n)? """)
    o.flush()
    resp = input().lower()
    o.write("\n")
    if resp not in ('y', 'yes', 'o', 'oui', 'j', 'ja'): return
    if db is None:
        st.create(local=opts.local)
    else:
        upgrade_database(opts, st, db, version, latest)
    return True


def get_store(opts, allow_mem=False):
    st = _store.Store(opts.cfg.sub('store'),
                      mem_name='store' if allow_mem else None)
    st.check_version(functools.partial(on_upgrade, opts))
    return st


@contextlib.contextmanager
def get_db(opts, mode):
    with get_store(opts) as st, \
            contextlib.closing(st.connect(mode=mode)) as db, db:
        yield db


def read_db(opts): return get_db(opts, 'ro')
def write_db(opts): return get_db(opts, 'rw')


def backup_path(st):
    suffix = datetime.datetime.now() \
                .isoformat('.', 'microseconds').replace(':', '-')
    return st.path.with_name(f'{st.path.name}.{suffix}')


def upgrade_database(opts, database, db, version, to_version, indent=""):
    o = opts.stdout
    backup = backup_path(database)
    o.write(f"{indent}Backing up database to: {backup}\n")
    database.backup(db, backup)
    def on_version(v): o.write(f"{indent}Upgrading database to version {v}\n")
    database.upgrade(version=to_version, on_version=on_version)
    o.write(f"{indent}Database upgraded successfully\n\n")


def comma_separated(s):
    if s is None: return []
    return s.split(',')


def cmd_version(opts):
    opts.stdout.write(f"{__project__}-{__version__}\n")
