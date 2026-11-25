# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import asyncio
from concurrent import futures
import contextlib
import datetime
import functools
import heapq
from http import client
import itertools
import json
import os
import pathlib
import re
import shlex
import signal
import ssl
import subprocess
import sys
import sysconfig
import tempfile
import threading
import time
import tomllib
from urllib import request

import certifi

from . import context

usec = datetime.timedelta(microseconds=1)
build_errors = 'tdoc-build-errors.log'
fixes = 'tdoc-fixes.json'
fixes_badge = 'tdoc-fixes.svg'
_levels = {'error': 0, 'warning': 1, 'info': 2}
no_match = r'^\b$'


def not_implemented(*args, **kwargs): raise NotImplementedError()


def level_key(level): return _levels.get(level, 3)


def version_tuple(version):
    if not version: return None
    return tuple(try_int(v) for v in version.split('.'))


def try_int(v):
    try: return int(v)
    except ValueError: return v


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


class Timers:
    def __init__(self, executor, log):
        self.exec, self.log = executor, log
        self.lock = threading.Condition(threading.Lock())
        self.timers, self.counter, self.stop = [], 0, False
        self.runner = threading.Thread(target=self.run, name='Timers.run')
        self.runner.start()

    def shutdown(self):
        with self.lock:
            self.stop = True
            self.lock.notify()
        self.runner.join()

    def __enter__(self): return self
    def __exit__(self, typ, value, tb): self.shutdown()

    def at(self, t, fn, period=None):
        def run():
            reschedule = period is not None
            try:
                with entry[3]:
                    if entry[2] is not None:
                        reschedule = fn() is not False and reschedule
                    else:
                        reschedule = False
            except Exception as e:
                self.log.exception("Uncaught exception in timer",
                                   event='timer:exception')
            finally:
                if reschedule:
                    entry[0] = max(entry[0] + period, time.monotonic())
                    self.insert(entry)
        entry = [t, 0, run, threading.Lock()]
        self.insert(entry)
        return entry

    def after(self, delay, fn, period=None):
        return self.at(time.monotonic() + delay, fn, period)

    def repeat(self, period, fn, delay=0):
        return self.after(delay, fn, period)

    def remove(self, entry):
        with entry[3]: entry[2] = None

    def insert(self, entry):
        with self.lock:
            entry[1] = self.counter
            self.counter += 1
            heapq.heappush(self.timers, entry)
            self.lock.notify()

    def run(self):
        with self.lock:
            while True:
                now = time.monotonic()
                d = None
                while self.timers:
                    entry = self.timers[0]
                    with entry[3]: fn = entry[2]
                    if fn is None:
                        heapq.heappop(self.timers)
                        continue
                    if (t := entry[0]) > now:
                        d = t - now
                        break
                    heapq.heappop(self.timers)
                    self.exec.submit(fn)
                self.lock.wait(d)
                if self.stop: return


class Partialer:
    __slots__ = ('inst',)

    def __init__(self, inst):
        self.inst = inst

    def __getattr__(self, name):
        return functools.partial(functools.partial, getattr(self.inst, name))


def suppress(result=None, *, exc=Exception, log=None):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except exc:
                if log is not None: log()
                return result() if result is not None else None
        return wrapper
    return decorator


if sys.platform == 'win32':
    def retry_on_win(fn, duration=1, interval=0.1, exc=PermissionError):
        start = time.monotonic()
        while True:
            try:
                return fn()
            except exc:
                if time.monotonic() - start >= duration: raise
                time.sleep(interval)
else:
    def retry_on_win(fn, duration=1, interval=0.1, exc=PermissionError):
        return fn()


def task(fn):
    @functools.wraps(fn)
    def wrapper(self, /, *args, **kwargs):
        @context.ctx.set_default(fn.__name__)
        def run(): return fn(self, *args, **kwargs)
        return self.exec.submit(run).result
    return wrapper


def tasks(fn):
    res = lambda self, rs: rs

    @functools.wraps(fn)
    def wrapper(self, /, *args, **kwargs):
        fs = [self.exec.submit(t) for t in fn(self, *args, **kwargs)]
        return lambda timeout=None: \
            res(self, (f.result() for f in futures.as_completed(fs, timeout)))

    def result(rfn):
        nonlocal res
        res = rfn
        return wrapper

    wrapper.result = result
    return wrapper


def read_stable(path):
    with path.open('rb') as f:
        mtime = os.stat(fd := f.fileno()).st_mtime_ns
        while True:  # Repeat read if mtime changes
            data = f.read()
            if (mtime2 := os.stat(fd).st_mtime_ns) == mtime: return data
            mtime = mtime2
            f.seek(0)


def read_toml(path):
    with open(path, 'rb') as f:
        return tomllib.load(f)


if sys.platform == 'win32':
    def replace_file(path, target):
        tries = 10
        while True:
            try:
                return path.replace(target)
            except PermissionError as e:
                if tries <= 1: raise
                time.sleep(0.1)
                tries -= 1
else:
    def replace_file(path, target):
        return path.replace(target)


@contextlib.contextmanager
def write_atomic(path, *args, **kwargs):
    with tempfile.NamedTemporaryFile(*args, dir=path.parent,
                                     prefix=path.name + '.',
                                     delete_on_close=False, **kwargs) as f:
        yield f
        f.close()
        replace_file(pathlib.Path(f.name), path)


def find_site_repo(path):
    path = path.resolve()
    for parent in itertools.chain([path], path.parents):
        if is_site_repo(parent): return parent


def is_site_repo(path):
    return (path / 'run.py').is_file() and (path / 'docs' / 'conf.py').is_file()


try:
    import msvcrt
except ModuleNotFoundError:
    _mswindows = False
else:
    _mswindows = True


def run(*args, input=None, capture_output=False, timeout=None, check=False,
        monitor=contextlib.nullcontext, success=(0,), prefix=False, **kwargs):
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
    if prefix: args = (script_path(args[0]), *args[1:])
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


def script_path(name):
    scripts = pathlib.Path(sysconfig.get_path('scripts'))
    ext = sysconfig.get_config_vars().get('EXE', '')
    return scripts / f'{name}{ext}'


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


_set_types = (set, frozenset)


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, _set_types): return tuple(obj)
        if isinstance(obj, os.PathLike): return str(obj)
        return super().default(obj)


to_json = JSONEncoder(separators=(',', ':')).encode
to_json_sorted = JSONEncoder(separators=(',', ':'), sort_keys=True).encode


class Namespace(dict):
    def __getattr__(self, name):
        return self[name]


def run_json(*args, object_pairs_hook=Namespace, **kwargs):
    return json.loads(run(*args, capture_output=True, text=True,
                          **kwargs).stdout,
                      object_pairs_hook=object_pairs_hook)


def run_uv(*args, common, **kwargs):
    return run('uv', *args, prefix=True, cwd=common, **kwargs)


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


class Thread(threading.Thread):
    def __enter__(self):
        self.start()
        return self

    def __exit__(self, typ, value, tb):
        self.join()


class AioThread(threading.Thread):
    def __init__(self, *, stop_on_exit=False, executor_threads=None, group=None,
                 name=None, daemon=None, context=None):
        super().__init__(group=group, name=name, daemon=daemon, context=context)
        self.__stop_on_exit = stop_on_exit
        self.__executor_threads = executor_threads
        self.__lock = threading.Lock()
        self.__running = threading.Event()
        self.__stop = asyncio.Event()

    def start(self):
        super().start()
        self.__running.wait()

    def stop(self, *args):
        with self.__lock:
            if (loop := self.__loop) is not None:
                loop.call_soon_threadsafe(self.__stop.set)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, typ, value, tb):
        if self.__stop_on_exit: self.stop()
        self.join()

    def run(self):
        with asyncio.Runner() as runner:
            loop = runner.get_loop()
            loop.set_default_executor(
                futures.ThreadPoolExecutor(max_workers=self.__executor_threads,
                                           thread_name_prefix=self.name))
            with self.__lock: self.__loop = loop
            try:
                return runner.run(self.__run())
            finally:
                with self.__lock: self.__loop = None

    async def __run(self):
        self.__running.set()
        await self.__stop.wait()

    def call(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.__loop)

    def call_sync(self, fn, *args, **kwargs):
        if threading.current_thread() is self: return fn(*args, **kwargs)
        async def afn(): return fn(*args, **kwargs)
        return self.call(afn()).result()

    def call_soon(self, fn):
        if threading.current_thread() is self: return fn()
        self.__loop.call_soon_threadsafe(fn)


running_loop = asyncio._get_running_loop


def current_task():
    if running_loop() is not None and (t := asyncio.current_task()) is not None:
        return t


class CancelTaskGroup(Exception): pass


class TaskGroup(asyncio.TaskGroup):
    def __init__(self, *, first_exc=False):
        super().__init__()
        self.__first_exc = first_exc

    def run(self, fn=None, /, **kwargs):
        if fn is not None: return self.create_task(fn(), **kwargs)
        return lambda fn: self.create_task(fn(), **kwargs)

    async def __aexit__(self, typ, value, tb):
        try:
            try:
                return await super().__aexit__(typ, value, tb)
            except* CancelTaskGroup:
                pass
        except ExceptionGroup as e:
            if not self.__first_exc: raise
            raise first_exception(e, Exception) from None
        except BaseExceptionGroup as e:
            if not self.__first_exc: raise
            raise first_exception(e, BaseException) from None
        finally:
            value = e = None

    # TODO(py-3.15): Remove
    if not hasattr(asyncio.TaskGroup, 'cancel'):
        def cancel(self):
            async def fn(): raise CancelTaskGroup()
            try:
                self.create_task(fn())
            except RuntimeError:
                pass  # TaskGroup is aborting


def first_exception(eg, typ):
    stack = [[eg.exceptions, 0]]
    while stack:
        es, i = stack[-1]
        while i < len(es):
            e = es[i]
            if isinstance(e, typ): return e
            if isinstance(e, (BaseExceptionGroup, ExceptionGroup)):
                stack[-1][1] = i + 1
                stack.append([e.exceptions, 0])
                break
        else:
            stack.pop()
