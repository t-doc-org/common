#!/usr/bin/env python
# Copyright 2026 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import pathlib
import re
import subprocess
import sys

run_py_name = 'run.py'


def main(argv, stdin, stdout, stderr):
    base = pathlib.Path(argv[0]).parent.resolve().parent
    run_py = base / run_py_name
    if not pathlib.Path(sys.executable).is_relative_to(base):
        return subprocess.run([run_py, 'python', '-P'] + argv).returncode

    # Update the trusted CA bundle.
    import certifi
    ca_data = certifi.contents().strip()
    old = run_py.read_text('utf-8')
    new = re.sub(r'(?ms)^(ca_data = r"""\n).*(^"""  # ca_data)',
                 lambda m: f'{m[1]}{ca_data}\n{m[2]}', old)
    if new != old: run_py.write_text(new, 'utf-8')
    subprocess.run(['hg', 'diff', '-R', run_py.parent, run_py])
    stdout.write("\n")

    # Write to site repositories.
    for repo in sorted(base.parent.iterdir()):
        dest = repo / run_py_name
        if not dest.is_file() or dest == run_py: continue
        stdout.write(f"==== {repo}\n")
        dest.write_text(new, 'utf-8')
        subprocess.run(['hg', 'status', '-R', repo])


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv, sys.stdin, sys.stdout, sys.stderr))
    except SystemExit:
        raise
    except KeyboardInterrupt:
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f'\n{e}\n')
        sys.exit(1)
