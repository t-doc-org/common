# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import contextlib
import datetime
from http import client
import itertools
import json
import os
import re
import shlex
import signal
import ssl
import subprocess
import sys
import tempfile
import tomllib
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


def parse_duration(duration, *, signed=False):
    """Parse a human-readable duration of the form '3d28m32s'."""
    if (neg := signed and duration.startswith('-')): duration = duration[1:]
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
    td = datetime.timedelta(**kwargs)
    return -td if neg else td


def nsec_to_datetime(nsec):
    return datetime.datetime.fromtimestamp(nsec / 1e9, datetime.UTC)


def datetime_to_nsec(dt):
    return int(dt.timestamp() * 1e9)


def timedelta_to_nsec(td):
    return (td // usec) * 1000


def read_stable(path):
    with path.open('rb') as f:
        mtime = os.stat(fd := f.fileno()).st_mtime_ns
        while True:  # Repeat read if mtime changes
            data = f.read()
            if (mtime2 := os.stat(fd).st_mtime_ns) == mtime: return data
            mtime = mtime2
            f.seek(0)


def read_toml(path):
    with path.open('rb') as f:
        return tomllib.load(f)


try:
    import msvcrt
except ModuleNotFoundError:
    _mswindows = False
else:
    _mswindows = True


def run(*args, input=None, capture_output=False, timeout=None, check=False,
        monitor=contextlib.nullcontext, success=(0,), common=None, **kwargs):
    """Run a command and return a CompletedProcess instance.

    This is a copy of subprocess.run() with additional functionality that cannot
    be implemented on top of it (monitor).
    """
    if input is not None:
        if kwargs.get('stdin') is not None:
            raise ValueError('stdin and input arguments may not both be used.')
        kwargs['stdin'] = subprocess.PIPE
    elif 'stdin' not in kwargs:
        kwargs['stdin'] = subprocess.DEVNULL
    if capture_output:
        if kwargs.get('stdout') is not None or kwargs.get('stderr') is not None:
            raise ValueError('stdout and stderr arguments may not be used '
                             'with capture_output.')
        kwargs['stdout'] = subprocess.PIPE
        kwargs['stderr'] = subprocess.PIPE
    if common is not None:
        args = (sys.executable, '-P', common / 'run.py', *args)
    with subprocess.Popen(args, **kwargs) as process, monitor(process):
        try:
            stdout, stderr = process.communicate(input, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            process.kill()
            if _mswindows:
                exc.stdout, exc.stderr = process.communicate()
            else:
                process.wait()
            raise
        except BaseException:
            process.kill()
            raise
        retcode = process.poll()
        if check and retcode:
            raise subprocess.CalledProcessError(retcode, process.args,
                                                output=stdout, stderr=stderr)
        if success is not None and retcode not in success:
            raise Exception(e if (e := (stderr or '').strip())
                            else f"Command failed (exit status: {retcode})")
    return subprocess.CompletedProcess(process.args, retcode, stdout, stderr)


def terminate_on(*sigs):
    @contextlib.contextmanager
    def on_started(proc):
        save = {}
        try:
            for sig in sigs:
                save[sig] = signal.signal(sig, lambda *args: proc.terminate())
            yield
        finally:
            for sig, fn in save.items(): signal.signal(sig, fn)
    return on_started


to_json = json.JSONEncoder(separators=(',', ':')).encode
to_json_sorted = json.JSONEncoder(separators=(',', ':'), sort_keys=True).encode


class Namespace(dict):
    def __getattr__(self, name):
        return self[name]


def run_json(*args, object_pairs_hook=Namespace, **kwargs):
    return json.loads(run(*args, capture_output=True, text=True,
                          **kwargs).stdout,
                      object_pairs_hook=object_pairs_hook)


def run_uv(*args, common, **kwargs):
    return run('uv', *args, common=common, cwd=common, **kwargs)


def requirements(*, common, pkgs=(), only_pkgs=(), only_groups=(),
                 no_project=False):
    def export(*args):
        return run_uv('export', '--no-header', '--no-default-groups',
                      '--format=requirements.txt', *args,
                      *(f'--only-emit-package={p}' for p in only_pkgs),
                      *(f'--only-group={g}' for g in only_groups),
                      *(('--no-emit-project',) if no_project else ()),
                      common=common, capture_output=True, text=True).stdout

    if not pkgs: return export()
    run_toml = read_toml(common / 'config' / 'run.toml')
    with tempfile.NamedTemporaryFile('w') as f:
        f.write(f"""\
# /// script
# requires-python = '>={run_toml['python']['minimum']}'
# dependencies = [{', '.join(f"'{p}'" for p in pkgs)}]
# ///
""")
        f.flush()
        return export('--no-cache', f'--script={f.name}')


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


def fetch_json(*args, **kwargs):
    with urlopen(*args, **kwargs) as f:
        return json.load(f, object_pairs_hook=Namespace)
