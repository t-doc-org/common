# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import contextlib

from .. import cli, store


def add_commands(parser):
    p = parser.add_parser('store', help="Store-related commands.")
    sp = p.add_subparsers(title="Sub-commands")
    sp.required = True

    p = sp.add_parser('backup', help="Backup the store database.")
    p.set_defaults(handler=cmd_backup)
    arg = p.add_argument
    arg('destination', metavar='PATH', nargs='?', type='path', default=None,
        help="The path to the backup copy. Defaults to the source database "
             "file with a date + time suffix.")
    cli.add_common_options(p)

    p = sp.add_parser('create', help="Create the store database.")
    p.set_defaults(handler=cmd_create)
    arg = p.add_argument
    arg('--version', metavar='VERSION', dest='version', type=int, default=None,
        help="The version at which to create the store database (default: "
             "latest).")
    cli.add_common_options(p)

    p = sp.add_parser('upgrade', help="Upgrade the store database.")
    p.set_defaults(handler=cmd_upgrade)
    arg = p.add_argument
    arg('--version', metavar='VERSION', dest='version', type=int, default=None,
        help="The version to which to upgrade the store database (default: "
             "latest).")
    cli.add_common_options(p)


def cmd_backup(opts):
    st = store.Store(opts.cfg.sub('store'))
    if opts.destination is None: opts.destination = cli.backup_path(st)
    with contextlib.closing(st.connect(mode='ro')) as db, db:
        opts.stdout.write(f"Backing up to: {opts.destination}\n")
        st.backup(db, opts.destination)


def cmd_create(opts):
    st = store.Store(opts.cfg.sub('store'))
    version = st.create(version=opts.version, local=opts.local)
    opts.stdout.write(f"Created (version: {version}): {st.path}\n")


def cmd_upgrade(opts):
    st = store.Store(opts.cfg.sub('store'))
    with contextlib.closing(st.connect(mode='rw')) as db:
        with db: version, latest = st.version(db)
        if version == latest:
            opts.stdout.write(
                f"Already up-to-date (version: {version}): {st.path}\n")
            return
        opts.stdout.write(f"Upgrading (version: {version}): {st.path}\n")
        to_version = opts.version if opts.version is not None else latest
        cli.upgrade_database(opts, st, db, version, to_version, indent="  ")
