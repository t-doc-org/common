# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import asyncio
from pyodide.ffi import run_sync

from tdoc import core


class Clock:
    """A replacement for pygame.time.Clock."""
    def __init__(self):
        self.t, self.fps_cnt, self.fps = None, 0, 0

    def tick(self, framerate=0):
        if self.t is None:
            t = self.t = self.fps_t = run_sync(core.animation_frame())
            return t
        end = self.t + (1000 / framerate if framerate != 0 else 0)
        while (t := run_sync(core.animation_frame())) < end: pass
        self.t = t
        self.fps_cnt += 1
        if self.fps_cnt >= 10:
            self.fps = self.fps_cnt / ((t - self.fps_t) / 1000)
            self.fps_t, self.fps_cnt = t, 0
        return t

    tick_busy_loop = tick

    def get_time(self): return self.t
    def get_rawtime(self): return core.animation_time()
    def get_fps(self): return self.fps


def get_ticks():
    return core.animation_time()


def wait(milliseconds):
    start = core.animation_time()
    core.sleep(milliseconds / 1000)
    return core.animation_time() - start


def event_wait(timeout=None):
    if timeout is None:
        while (e := pygame.event.poll()) == pygame.NOEVENT: core.sleep(0.02)
        return e
    loop = asyncio.get_running_loop()
    end = loop.time() + timeout / 1000
    while True:
        if (e := pygame.event.poll()) != pygame.NOEVENT: return e
        if (now := loop.time()) >= end: return e
        core.sleep(min(0.02, end - now))


import pygame  # noqa
pygame.time.Clock = pygame.Clock = Clock
pygame.time.get_ticks = get_ticks
pygame.time.wait = pygame.time.delay = wait
# TODO: Test that event_wait() actually works
# pygame.event.wait = event_wait
