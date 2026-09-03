# Copyright 2026 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

def get(name, *attrs):
    if (f := _fixes.get(name)) is None: return (None,) * len(attrs)
    return tuple(f.get(a) for a in attrs)


_fixes = {
    'bad-filename': dict(
        title="""\
Use only non-whitespace and non-reserved \
<a href="https://en.wikipedia.org/wiki/ASCII#Printable_character_table">\
printable ASCII</a> characters in file names.""",
    ),
}
