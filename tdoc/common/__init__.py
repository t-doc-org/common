# Copyright 2024 Caroline Blank <caro@c-space.org>
# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

__version__ = '0.1'


def setup(app):
    return {'parallel_read_safe': True, 'parallel_write_safe': True}
