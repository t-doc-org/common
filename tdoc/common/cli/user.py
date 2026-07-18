# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

from .. import cli, util


def add_commands(parser):
    p = parser.add_parser('user', help="User-related commands.")
    sp = p.add_subparsers(title="Sub-commands")
    sp.required = True

    def add_users_re(arg):
        arg('users', metavar='REGEXP', nargs='?', default='.*',
            help="A regexp to limit the users to consider.")

    p = sp.add_parser('create', help="Create users.")
    p.set_defaults(handler=cmd_create)
    arg = p.add_argument
    cli.add_origin_option(arg)
    arg('--token-expire', metavar='TIME', dest='token_expire',
        type='opt_rel_timestamp',
        help="Expire the users' token at the given relative or absolute time.")
    arg('user', metavar='USER', nargs='+',
        help="The names of the users to create.")
    cli.add_common_options(p)

    p = sp.add_parser('list', help="List users.")
    p.set_defaults(handler=cmd_list)
    arg = p.add_argument
    add_users_re(arg)
    cli.add_common_options(p)

    p = sp.add_parser('memberships', help="List group memberships for a user.")
    p.set_defaults(handler=cmd_memberships)
    arg = p.add_argument
    cli.add_origin_option(arg)
    arg('--direct', action='store_true', dest='direct',
        help="List only direct memberships.")
    add_users_re(arg)
    cli.add_common_options(p)


def cmd_create(opts):
    with cli.write_db(opts) as db:
        uids = db.users.create(opts.user)
        tokens = db.tokens.create(uids, opts.token_expire)
    wuser = max((len(u) for u in opts.user), default=0)
    o = opts.stdout
    for uid, user, token in zip(uids, opts.user, tokens):
        o.write(f"{o.CYAN}{user:{wuser}}{o.NORM} ({uid:19})  "
                f"{o.LBLUE}{opts.origin}#?token={token}{o.NORM}\n")


def cmd_list(opts):
    with cli.read_db(opts) as db:
        users = db.users.list(opts.users)
    users.sort(key=lambda r: r[1])
    wuser = max((len(r[1]) for r in users), default=0)
    o = opts.stdout
    for uid, user, created in users:
        opts.stdout.write(
            f"{o.CYAN}{user:{wuser}}{o.NORM} ({uid:19d})  "
            f"created: {util.local_time(created)}\n")


def cmd_memberships(opts):
    with cli.read_db(opts) as db:
        memberships = db.users.memberships(opts.origin, opts.users,
                                           transitive=not opts.direct)
    memberships.sort()
    wuser = max((len(r[1]) for r in memberships), default=0)
    wgroup = max((len(r[2]) for r in memberships), default=0)
    o = opts.stdout
    prev = None
    for uid, user, group, transitive in memberships:
        prefix = f"{o.CYAN}{user:{wuser}}{o.NORM} ({uid:19d})  " \
                 if uid != prev else f"{'':{wuser + 19 + 5}}"
        if transitive:
            opts.stdout.write(f"{prefix}  {o.LWHITE}{group:{wgroup}}{o.NORM}  "
                             "(transitive)\n")
        else:
            opts.stdout.write(f"{prefix}  {o.LWHITE}{group}{o.NORM}\n")
        prev = uid
