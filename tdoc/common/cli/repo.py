# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import certifi
import re

from .. import cli, util


def add_commands(parser):
    p = parser.add_parser('repo', help="Repository-related commands.")
    sp = p.add_subparsers(title="Sub-commands")
    sp.required = True

    p = sp.add_parser('auth', help="Modify repository authentication.")
    p.set_defaults(handler=cmd_auth)
    arg = p.add_argument
    arg('--disable', action='store_false', dest='enable', default=None,
        help="Disable repository access.")
    arg('--enable', action='store_true', dest='enable', default=None,
        help="Enable repository access.")
    arg('--reset', action='store_true', dest='reset',
        help="Reset the password.")
    arg('user', metavar='USER', nargs='+',
        help="The users for whom to modify repository authentication.")
    cli.add_common_options(p)

    p = sp.add_parser('list-users', help="List repository users.")
    p.set_defaults(handler=cmd_list_users)
    arg = p.add_argument
    arg('users', metavar='REGEXP', nargs='?', default='.*',
        help="A regexp to limit the users to consider.")
    cli.add_common_options(p)

    p = sp.add_parser('update-run', help="Update run.py.")
    p.set_defaults(handler=cmd_update_run)
    arg = p.add_argument
    arg('--sites', action='store_true', dest='sites', default=None,
        help="Update run.py in site repositories.")
    cli.add_common_options(p)


def cmd_auth(opts):
    with cli.write_db(opts) as db:
        for u in opts.user:
            if (v := opts.enable) is not None:
                db.repo.enable_auth(db.users.uid(u), v)
            if opts.reset: db.repo.reset_password(db.users.uid(u))


def cmd_list_users(opts):
    with cli.read_db(opts) as db:
        infos = db.repo.list_users(opts.users)
    infos.sort(key=lambda r: (r[1], r[0]))
    wuser = max((len(r[1]) for r in infos), default=0)
    o = opts.stdout
    for uid, name, enabled, prefix in infos:
        opts.stdout.write(
            f"{o.CYAN}{name:{wuser}}{o.NORM} ({uid:19d})  "
            f"access: {"enabled " if enabled else "disabled"}  "
            f"password: {"[none]" if prefix is None else prefix + "****"}\n")


run_py_name = 'run.py'
ca_data_re = re.compile(r'(?ms)^(ca_data = r"""\n).*(^"""  # ca_data)')


def cmd_update_run(opts):
    cli.require_common(opts)
    run_py = opts.common / run_py_name

    # Update the trusted CA bundle.
    ca_data = certifi.contents().strip()
    old = run_py.read_text('utf-8')
    new = ca_data_re.sub(lambda m: f'{m[1]}{ca_data}\n{m[2]}', old)
    if new != old: run_py.write_text(new, 'utf-8')
    util.run('hg', 'diff', '-R', run_py.parent, run_py)
    if not opts.sites: return

    # Update site repositories.
    o = opts.stdout
    for repo in sorted(opts.common.parent.iterdir()):
        dest = repo / run_py_name
        if not dest.is_file() or dest == run_py: continue
        o.write(f"\n{o.BOLD}{repo}{o.NORM}\n")
        dest.write_text(new, 'utf-8')
        util.run('hg', 'status', '-R', repo)
