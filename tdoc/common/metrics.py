# Copyright 2026 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import threading

from prometheus_client import core as pcc, registry as pcr


class Collector(pcr.Collector):
    def __init__(self):
        super().__init__()
        self.lock = threading.Lock()
        self.metrics = {}
        self.handlers = set()

    def define(self, type, *, name, **kwargs):
        with self.lock: self.metrics[name] = (type, kwargs)

    def add_handler(self, fn):
        with self.lock: self.handlers.add(fn)
        def remove():
            with self.lock: self.handlers.discard(fn)
        return remove

    def collect(self):
        with self.lock:
            metrics = {n: t(name=n, **kw)
                       for n, (t, kw) in self.metrics.items()}
            for fn in self.handlers: fn(metrics)
        return metrics.values()


collector = Collector()
pcc.REGISTRY.register(collector)

counter = lambda **kwargs: collector.define(pcc.CounterMetricFamily, **kwargs)
gauge = lambda **kwargs: collector.define(pcc.GaugeMetricFamily, **kwargs)
summary = lambda **kwargs: collector.define(pcc.SummaryMetricFamily, **kwargs)
histogram = \
    lambda **kwargs: collector.define(pcc.HistogramMetricFamily, **kwargs)
gauge_histogram = \
    lambda **kwargs: collector.define(pcc.GaugeHistogramMetricFamily, **kwargs)
info = lambda **kwargs: collector.define(pcc.InfoMetricFamily, **kwargs)
state_set = \
    lambda **kwargs: collector.define(pcc.StateSetMetricFamily, **kwargs)

collect = collector.add_handler
