# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import certifi
import contextlib
import datetime
import pathlib
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

    p = sp.add_parser('template', help="Prepare a template repository clone.")
    p.set_defaults(handler=cmd_template)
    arg = p.add_argument
    arg('--author', metavar='AUTHOR', dest='author', required=True,
        help="The owner of the repository and author of its content.")
    arg('--email', metavar='EMAIL', dest='email', required=True,
        help="The email address of the repository owner.")
    arg('--repo', metavar='NAME', dest='repo',
        help="The namem of the repository.")
    arg('--title', metavar='TITLE', dest='title', required=True,
        help="The title of the site.")
    arg('path', metavar='PATH', type='path',
        help="The path of the template repository clone.")
    cli.add_common_options(p)

    p = sp.add_parser('update',
                      help="Update common files across site repositories.")
    p.set_defaults(handler=cmd_update)
    arg = p.add_argument
    arg('--all', action='store_true', dest='all', default=None,
        help="Update all site repositories.")
    arg('site', metavar='SITE', nargs='*',
        help="The sites whose repositories should be updated.")
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
        o.write(
            f"{o.CYAN}{name:{wuser}}{o.NORM}  0x{uid:016x}  "
            f"access: {"enabled " if enabled else "disabled"}  "
            f"password: {"[none]" if prefix is None else prefix + "****"}\n")


def cmd_template(opts):
    if opts.repo is None: opts.repo = opts.path.name
    subst = {'AUTHOR': opts.author, 'EMAIL': opts.email, 'TITLE': opts.title,
             'YEAR': str(datetime.datetime.now().year)}
    phs = re.compile(f'\\{{({'|'.join(re.escape(k) for k in subst)})\\}}')
    urls = re.compile(r'(https://github\.com/[^/]+/)([a-zA-Z0-9_-]+)')
    def on_error(e): _log.error("Walk: %(exc)s", exc=e)
    for parent, dirs, files in opts.path.walk(on_error=on_error):
        with contextlib.suppress(ValueError): dirs.remove('.hg')
        dirs.sort()
        files.sort()
        for f in files:
            if (path := parent / f) == opts.path / run_py: continue
            text = path.read_text('utf-8')
            new_text = phs.sub(lambda m: subst[m[1]], text)
            new_text = urls.sub(lambda m: f'{m[1]}{opts.repo}', new_text)
            if new_text != text: path.write_text(new_text, 'utf-8')


run_py = pathlib.Path('run.py')
ca_data_re = re.compile(r'(?ms)^(ca_data = r"""\n).*(^"""  # ca_data)')
common_files = [
    pathlib.Path('.gitignore'),
    pathlib.Path('.hgignore'),
    pathlib.Path('run.desktop'),
    run_py,
]


def cmd_update(opts):
    cli.require_common(opts)
    o, sep = opts.stdout, ''

    # Update the trusted CA bundle.
    ca_data = certifi.contents().strip()
    old = (path := opts.common / run_py).read_text('utf-8')
    new = ca_data_re.sub(lambda m: f'{m[1]}{ca_data}\n{m[2]}', old)
    if new != old:
        o.write(f"{o.BOLD}Updating {run_py}{o.NORM}\n")
        sep = '\n'
        path.write_text(new, 'utf-8')
        util.run('hg', 'diff', '-R', opts.common, path)

    # Update site repositories.
    for repo in sorted(opts.common.parent.iterdir()):
        if repo == opts.common or not util.is_site_repo(repo): continue
        if not opts.all and repo.name not in opts.site: continue
        o.write(f"{sep}{o.BOLD}{repo}{o.NORM}\n")
        sep = '\n'
        for p in common_files: update_common_file(opts, p, repo)
        util.run('hg', 'status', '-R', repo)


common_re = re.compile(r'(?ms)(^[#;] BEGIN-COMMON\n)(.*)(^[#;] END-COMMON\n)')


def update_common_file(opts, path, repo):
    src_text = (opts.common / path).read_text('utf-8')
    snippet = m[2] if (m := common_re.search(src_text)) else src_text
    dst_text = dst.read_text('utf-8') if (dst := repo / path).exists() else ''
    if m := common_re.search(dst_text):
        start, end = m.span(2)
        text = f'{dst_text[:start]}{snippet}{dst_text[end:]}'
    else:
        text = snippet
    if text == dst_text: return
    o = opts.stdout
    o.write(f"  {path}\n")
    dst.write_text(text, 'utf-8')
