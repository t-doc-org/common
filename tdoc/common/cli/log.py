# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import contextlib
import functools
import time

from .. import cli, console, logs


def add_commands(parser):
    p = parser.add_parser('log', help="Log-related commands.")
    sp = p.add_subparsers(title="Sub-commands")
    sp.required = True

    p = sp.add_parser('backup', help="Backup log databases.")
    p.set_defaults(handler=cmd_backup)
    cli.add_common_options(p)

    p = sp.add_parser('create', help="Create log databases.")
    p.set_defaults(handler=cmd_create)
    arg = p.add_argument
    arg('--version', metavar='VERSION', dest='version', type=int, default=None,
        help="The version at which to create the log databases (default: "
             "latest).")
    cli.add_common_options(p)

    p = sp.add_parser('query', help="Query a log database.")
    p.set_defaults(handler=cmd_query)
    arg = p.add_argument
    arg('--begin', metavar='TIME', dest='begin', type='opt_nrel_timestamp',
        default='1h',
        help="Output entries logged at or after the given relative or absolute "
             "time (default: %(default)s).")
    arg('--end', metavar='TIME', dest='end', type='opt_nrel_timestamp',
        default=None,
        help="Output entries logged before the given relative or absolute "
             "time.")
    arg('--format', metavar='FORMAT', dest='format', default='',
        help="An additional format string to append to the format string used "
             "to format log entries.")
    arg('--index', metavar='N', dest='index', type=int, default=0,
        help="The index of the database handler in the config (default: "
             "%(default)s).")
    arg('--level', metavar='LEVEL', dest='level', type=logs.to_level,
        default=None,
        help="Output entries with a log level equal to or above the given "
             "level.")
    arg('--utc', action='store_true', dest='utc',
        help="Format times in UTC instead of local time.")
    arg('--watch', action='store_true', dest='watch',
        help="Output new log entries as they appear.")
    arg('--where', metavar='EXPR', dest='where', default=None,
        help="An additional SQL expression to add to the WHERE clause of the "
             "database query.")
    cli.add_common_options(p)

    p = sp.add_parser('upgrade', help="Upgrade log databases.")
    p.set_defaults(handler=cmd_upgrade)
    arg = p.add_argument
    arg('--version', metavar='VERSION', dest='version', type=int, default=None,
        help="The version to which to upgrade the log databases (default: "
             "latest).")
    cli.add_common_options(p)


@cli.disable_db_logs
def cmd_backup(opts):
    for c in opts.cfg.subs('logging.databases'):
        lst = logs.LogStore(c)
        dest = cli.backup_path(lst)
        with contextlib.closing(lst.connect(mode='ro')) as db, db:
            opts.stdout.write(f"Backing up to: {dest}\n")
            lst.backup(db, dest)


@cli.disable_db_logs
def cmd_create(opts):
    for c in opts.cfg.subs('logging.databases'):
        lst = logs.LogStore(c)
        if lst.exists:
            opts.stdout.write(f"Already exists: {lst.path}\n")
            continue
        version = lst.create(version=opts.version, local=opts.local)
        opts.stdout.write(f"Created (version: {version}): {lst.path}\n")


@cli.disable_db_logs
def cmd_query(opts):
    fmt = opts.cfg.get('logging.format', logs.default_query_format)
    if f := opts.format: fmt = f'{fmt}\n{f}'
    formatter = logs.Formatter(fmt, utc=opts.utc,
                               attrs=console.color_tags(opts.stdout))
    for i, c in enumerate(opts.cfg.subs('logging.databases')):
        if i == opts.index: break
    else:
        raise Exception("Invalid log database index")
    lst = logs.LogStore(c)
    lst.check_version(functools.partial(cli.on_upgrade, opts))
    with contextlib.closing(lst.connect(mode='ro')) as db:
        rid = None
        while True:
            with db:
                for rec, rid in db.query(row_id=rid, level=opts.level,
                                         begin=opts.begin, end=opts.end,
                                         where=opts.where):
                    opts.stdout.write(f"{formatter.format(rec)}\n")
            if not opts.watch: break
            time.sleep(1)


@cli.disable_db_logs
def cmd_upgrade(opts):
    for c in opts.cfg.subs('logging.databases'):
        lst = logs.LogStore(c)
        with contextlib.closing(lst.connect(mode='rw')) as db:
            with db: version, latest = lst.version(db)
            if version == latest:
                opts.stdout.write(
                    f"Already up-to-date (version: {version}): {lst.path}\n")
                continue
            opts.stdout.write(f"Upgrading (version: {version}): {lst.path}\n")
            to_version = opts.version if opts.version is not None else latest
            cli.upgrade_database(opts, lst, db, version, to_version,
                                 indent="  ")
