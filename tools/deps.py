#!/usr/bin/env python

# Copyright 2024 Caroline Blank <caro@c-space.org>
# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import sys
import tomllib


def main(argv, stdin, stdout, stderr):
    with open(argv[1], 'rb') as f:
        pyproj = tomllib.load(f)
    for dep in pyproj.get('project', {}).get('dependencies', []):
        stdout.write(f'{dep}\n')


if __name__ == '__main__':
    sys.exit(main(sys.argv, sys.stdin, sys.stdout, sys.stderr))
