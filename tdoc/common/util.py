# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import datetime
from http import client
import itertools
import re
import ssl
from urllib import request

import certifi

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


# Use certifi instead of the system CA store for portability.
#  - Recent SSL certificates from Sectigo used by GitHub aren't trusted on
#    Windows 10.
# The default context is configured like request.urlopen(context=None) does it
# via http.client._create_https_context().
ssl_ctx = ssl.create_default_context(cafile=certifi.where())
if client.HTTPSConnection._http_vsn == 11:
    ssl_ctx.set_alpn_protocols(['http/1.1'])
if ssl_ctx.post_handshake_auth is not None:
    ssl_ctx.post_handshake_auth = True


def urlopen(*args, **kwargs):
    if 'context' not in kwargs: kwargs['context'] = ssl_ctx
    return request.urlopen(*args, **kwargs)
