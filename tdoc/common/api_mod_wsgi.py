# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import contextlib
import mod_wsgi
import sys
import threading

from tdoc.common import api, config, store, logs, wsgi

log = logs.logger(__name__)


def application(config_path, origins, events_level=logs.NOTSET):
    threading.current_thread().name = 'main'

    # Load the config and set defaults.
    cfg = config.Config.load(config_path)
    store_config = cfg.sub('store')
    store_config.setdefault('poll_interval',
                            1 if mod_wsgi.maximum_processes > 1 else 0)
    store_config.setdefault('pool_size', mod_wsgi.threads_per_process)

    stack = contextlib.ExitStack()
    stack.enter_context(logs.configure(config=cfg.sub('logging'),
                                       stderr=sys.stderr))

    @mod_wsgi.subscribe_shutdown
    def on_shutdown(event, **kwargs):
        log.info("Shutdown: %s", kwargs)
        stack.close()

    if events_level != logs.NOTSET:
        @mod_wsgi.subscribe_events
        def on_event(event, **kwargs):
            log.log(events_level, "Event %s: %s", event, kwargs)

    # Instantiate the store and the API.
    st = store.Store(store_config)
    st.check_version()
    stack.enter_context(st)
    app = stack.enter_context(api.Api(config=cfg, store=st))

    return wsgi.cors(
        origins=origins,
        methods=('DELETE', 'GET', 'HEAD', 'OPTIONS', 'POST', 'PUT'),
        headers=('Authorization', 'Content-Type'))(app)
