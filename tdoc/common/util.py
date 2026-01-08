# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import datetime
import itertools
import re

usec = datetime.timedelta(microseconds=1)


def local_time(dt, sep=' ', timespec='seconds'):
    return dt.astimezone().replace(tzinfo=None).isoformat(sep, timespec)


def parse_time(v):
    dt = datetime.datetime.fromisoformat(v)
    if dt.tzinfo is None: dt = dt.astimezone()
    return dt


_duration_unit_re = re.compile('(us|ms|s|m|h|d|w)')
_duration_kw_map = {
    'us': 'microseconds',
    'ms': 'milliseconds',
    's': 'seconds',
    'm': 'minutes',
    'h': 'hours',
    'd': 'days',
    'w': 'weeks',
}


def parse_duration(duration):
    """Parse a human-readable duration of the form '3d28m32s'."""
    if not duration: raise ValueError(f"Invalid duration: {duration}")
    parts = _duration_unit_re.split(duration)
    if len(parts) % 2 != 0 and not parts[-1]: parts.pop()
    kwargs = {}
    for value, unit in itertools.zip_longest(parts[::2], parts[1::2],
                                             fillvalue='s'):
        k = _duration_kw_map[unit]
        try:
            v = float(value)
        except ValueError:
            raise ValueError(f"Invalid duration: {duration}")
        if v < 0: raise ValueError(f"Invalid duration: {duration}")
        kwargs[k] = kwargs.get(k, 0) + v
    return datetime.timedelta(**kwargs)


def nsec_to_datetime(nsec):
    return datetime.datetime.fromtimestamp(nsec / 1e9, datetime.UTC)


def datetime_to_nsec(dt):
    return int(dt.timestamp() * 1e9)


def timedelta_to_nsec(td):
    return (td // usec) * 1000
