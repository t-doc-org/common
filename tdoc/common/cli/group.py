# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

from .. import cli


def add_commands(parser):
    p = parser.add_parser('group', help="Group-related commands.")
    sp = p.add_subparsers(title="Sub-commands")
    sp.required = True

    def add_groups(arg):
        for name in ('group', 'groups'):
            arg(f'--{name}', metavar="GROUP,...", dest='groups',
                help="A comma-separated list of groups.")

    def add_users(arg):
        for name in ('user', 'users'):
            arg(f'--{name}', metavar="USER,...", dest='users',
                help="A comma-separated list of users.")

    def add_groups_re(arg):
        arg('groups', metavar='REGEXP', nargs='?', default='.*',
            help="A regexp to limit the groups to consider.")

    p = sp.add_parser('add', help="Add members to one or more groups.")
    p.set_defaults(handler=cmd_add)
    arg = p.add_argument
    add_groups(arg)
    cli.add_origin_option(arg)
    add_users(arg)
    arg('group', metavar='GROUP', nargs='+', help="The group to add to.")
    cli.add_common_options(p)

    p = sp.add_parser('list', help="List groups.")
    p.set_defaults(handler=cmd_list)
    arg = p.add_argument
    add_groups_re(arg)
    cli.add_common_options(p)

    p = sp.add_parser('members', help="List members of a group.")
    p.set_defaults(handler=cmd_members)
    arg = p.add_argument
    cli.add_origin_option(arg)
    arg('--direct', action='store_true', dest='direct',
        help="List only direct memberships.")
    add_groups_re(arg)
    cli.add_common_options(p)

    p = sp.add_parser('memberships', help="List group memberships for a group.")
    p.set_defaults(handler=cmd_memberships)
    arg = p.add_argument
    cli.add_origin_option(arg)
    add_groups_re(arg)
    cli.add_common_options(p)

    p = sp.add_parser('remove', help="Remove members from one or more groups.")
    p.set_defaults(handler=cmd_remove)
    arg = p.add_argument
    add_groups(arg)
    cli.add_origin_option(arg)
    add_users(arg)
    arg('group', metavar='GROUP', nargs='+', help="The group to remove from.")
    cli.add_common_options(p)


def cmd_add(opts):
    with cli.write_db(opts) as db:
        db.groups.modify(opts.origin, opts.group,
                         add_users=cli.comma_separated(opts.users),
                         add_groups=cli.comma_separated(opts.groups))


def cmd_list(opts):
    with cli.read_db(opts) as db:
        groups = db.groups.list(opts.groups)
    groups.sort()
    o = opts.stdout
    for group in groups: opts.stdout.write(f"{o.CYAN}{group}{o.NORM}\n")


def cmd_members(opts):
    with cli.read_db(opts) as db:
        members = db.groups.members(opts.origin, opts.groups,
                                    transitive=not opts.direct)
    members.sort()
    wgroup = max((len(r[0]) for r in members), default=0)
    wname = max((len(r[2]) for r in members), default=0)
    o = opts.stdout
    prev = None
    for group, typ, name, transitive in members:
        prefix = f"{o.CYAN}{group:{wgroup}}{o.NORM}" if group != prev \
                 else f"{'':{wgroup}}"
        if transitive:
            opts.stdout.write(
                f"{prefix}  {typ:5} {o.LWHITE}{name:{wname}}{o.NORM}  "
                "(transitive)\n")
        else:
            opts.stdout.write(f"{prefix}  {typ:5} {o.LWHITE}{name}{o.NORM}\n")
        prev = group


def cmd_memberships(opts):
    with cli.read_db(opts) as db:
        memberships = db.groups.memberships(opts.origin, opts.groups)
    memberships.sort()
    wmember = max((len(r[0]) for r in memberships), default=0)
    o = opts.stdout
    prev = None
    for member, group in memberships:
        prefix = f"{o.CYAN}{member:{wmember}}{o.NORM}" if member != prev \
                 else f"{'':{wmember}}"
        opts.stdout.write(f"{prefix}  {o.LWHITE}{group}{o.NORM}\n")
        prev = member


def cmd_remove(opts):
    with cli.write_db(opts) as db:
        db.groups.modify(opts.origin, opts.group,
                         remove_users=cli.comma_separated(opts.users),
                         remove_groups=cli.comma_separated(opts.groups))
