#!/usr/bin/env python

# Copyright 2024 Caroline Blank <caro@c-space.org>
# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import os
import sys


def main(argv, stdin, stdout, stderr):
    src, tmp = argv[1], argv[1] + '.tmp'
    with open(src, 'rb') as r, open(tmp, 'wb') as w:
        conv = False
        for line in r:
            if line.startswith(b'dependencies = ['):
                conv = True
            elif line.startswith(b']'):
                conv = False
            if conv: line = line.replace(b'>=', b'==', 1)
            w.write(line)
    os.replace(tmp, src)


if __name__ == '__main__':
    sys.exit(main(sys.argv, sys.stdin, sys.stdout, sys.stderr))
