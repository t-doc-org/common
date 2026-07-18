# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import contextlib
import mod_wsgi
import re
import sys
import threading

from tdoc.common import api, config, store, logs, wsgi

_log = logs.logger(__name__)


def application(config_path, events_level=logs.NOTSET):
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
    _log.info("Starting (processes: %(processes)s, threads: %(threads)s)",
              processes=mod_wsgi.maximum_processes,
              threads=mod_wsgi.threads_per_process)

    @mod_wsgi.subscribe_shutdown
    def on_shutdown(event, **kwargs):
        _log.info("Shutdown: %s", kwargs)
        stack.close()

    if events_level != logs.NOTSET:
        @mod_wsgi.subscribe_events
        def on_event(event, **kwargs):
            _log.log(events_level, "Event %s: %s", event, kwargs)

    # Instantiate the store and the API.
    st = store.Store(store_config)
    st.check_version()
    stack.enter_context(st)
    app = stack.enter_context(api.Api(config=cfg, store=st))

    dep = cfg.sub('deployment')
    return wsgi.cors(
        origins=rf'{re.escape(dep.get('scheme', 'https'))}://'
                rf'(?:{wsgi.hostname_re}\.)?{re.escape(domain)}'
                if (domain := dep.get('domain')) is not None else (),
        methods=('DELETE', 'GET', 'HEAD', 'OPTIONS', 'POST', 'PUT'),
        headers=('Authorization', 'Cache-Control', 'Content-Type', 'Cookie',
                 'X-Csrf'),
        credentials=True,
    )(app)
