# Copyright 2026 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import datetime

_warning_lead = datetime.timedelta(days=14)


def level(name, default='warning'):
    if (f := _fixes.get(name)) is None: return default
    level = f.get('level')
    if level is None and (dl := f.get('deadline')) is not None:
        lead = datetime.date.fromisoformat(dl) - datetime.date.today()
        level = 'warning' if lead <= _warning_lead else 'info'
    return level or default


def attrs(name, *attrs):
    if (f := _fixes.get(name)) is None: return (None,) * len(attrs)
    return tuple(f.get(a) for a in attrs)


_fixes = {
    'bad-filename': dict(
        title="""\
Use only non-whitespace and non-reserved \
<a href="https://en.wikipedia.org/wiki/ASCII#Printable_character_table">\
printable ASCII</a> characters in file names.""",
        level='warning',
    ),

    # For testing.
    'test': dict(
        title="""A <b>test fix</b>.""",
    ),
    'test-deadline-early': dict(
        title="""A <b>test fix</b> with a deadline past the threshold.""",
        deadline=str(datetime.date.today() + _warning_lead
                     + datetime.timedelta(days=1)),
    ),
    'test-deadline-late': dict(
        title="""A <b>test fix</b> with a deadline at the threshold.""",
        deadline=str(datetime.date.today() + _warning_lead),
    ),
    'test-info': dict(
        title="""A <b>test fix</b> at info level.""",
        level='info',
    ),
    'test-warning': dict(
        title="""A <b>test fix</b> at warning level.""",
        level='warning',
    ),
}
