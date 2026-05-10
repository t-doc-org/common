# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import datetime

from .. import cli, util


def add_commands(parser):
    p = parser.add_parser('token', help="Token-related commands.")
    sp = p.add_subparsers(title="Sub-commands")
    sp.required = True

    p = sp.add_parser('create', help="Create tokens.")
    p.set_defaults(handler=cmd_create)
    arg = p.add_argument
    arg('--expire', metavar='TIME', dest='expire', type='opt_rel_timestamp',
        help="Expire the token at the given relative or absolute time.")
    cli.add_origin_option(arg)
    arg('user', metavar='USER', nargs='+',
        help="The users for whom to create tokens.")
    cli.add_options(p)

    p = sp.add_parser('expire', help="Expire tokens.")
    p.set_defaults(handler=cmd_expire)
    arg = p.add_argument
    arg('--time', metavar='TIME', dest='time', type='opt_rel_timestamp',
        default='0s',
        help="The time when the tokens should expire (default: now). An empty "
             "value removes the expiry time.")
    arg('--users', action='store_true', dest='users',
        help="Expire all tokens for the users passed as arguments.")
    arg('arg', metavar='ARG', nargs='+',
        help="The tokens to expire, or the users for whom to expire tokens.")
    cli.add_options(p)

    p = sp.add_parser('list', help="List tokens.")
    p.set_defaults(handler=cmd_list)
    arg = p.add_argument
    arg('--expired', action='store_true', dest='expired',
        help="Include expired tokens.")
    cli.add_origin_option(arg)
    arg('users', metavar='REGEXP', nargs='?', default='.*',
        help="A regexp to limit the users to consider.")
    cli.add_options(p)


def cmd_create(opts):
    with cli.write_db(opts) as db:
        uids = [db.users.uid(u) for u in opts.user]
        tokens = db.tokens.create(uids, opts.expire)
    width = max((len(u) for u in opts.user), default=0)
    o = opts.stdout
    for uid, user, token in zip(uids, opts.user, tokens):
        opts.stdout.write(
            f"{o.CYAN}{user:{width}}{o.NORM}  ({uid:19d})  "
            f"{o.LBLUE}{opts.origin}#?token={token}{o.NORM}\n")


def cmd_expire(opts):
    with cli.write_db(opts) as db:
        if opts.users:
            db.tokens.expire(uids=[db.users.uid(u) for u in opts.arg],
                             expires=opts.time)
        else:
            db.tokens.expire(tokens=opts.arg, expires=opts.time)


def cmd_list(opts):
    with cli.read_db(opts) as db:
        tokens = db.tokens.list(opts.users, expired=opts.expired)
    epoch = datetime.datetime.fromtimestamp(0, datetime.UTC)
    tokens.sort(key=lambda r: (r[1], r[3], r[4] or epoch, r[2]))
    wuser = max((len(t[1]) for t in tokens), default=0)
    o = opts.stdout
    for uid, user, token, created, expires in tokens:
        if expires: expires = f", expires: {util.local_time(expires)}"
        opts.stdout.write(
            f"{o.CYAN}{user:{wuser}}{o.NORM} ({uid:19d})  "
            f"{o.LBLUE}{opts.origin}#?token={token}{o.NORM}\n"
            f"  created: {util.local_time(created)}{expires or ""}\n")
