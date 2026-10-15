# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import contextlib
import mod_wsgi
import re
import sys
import threading

from tdoc.common import api, config, store, logs, ws, wsgi

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

    # Set up the request dispatcher.
    disp = wsgi.Dispatcher()
    disp.add(app.endpoints(disp))

    # Set up the websocket server.
    dep = cfg.sub('deployment')
    scheme = dep.get('scheme', 'https')
    origins = wsgi.origins(scheme=scheme, domain=domain) \
              if (domain := dep.get('domain')) is not None else util.no_match
    host, path = dep.get('websocket.host'), dep.path('websocket.path')
    if host is not None or path is not None:
        ws_server = stack.enter_context(ws.Server(
            host=host, port=dep.get('websocket.port', 0), path=path,
            perms=dep.get('websocket.permissions', 0o600), scheme=scheme,
            origins=origins))
        ws_server.start_serving()

    return wsgi.cors(
        origins=origins,
        methods=('DELETE', 'GET', 'HEAD', 'OPTIONS', 'POST', 'PUT'),
        headers=('Authorization', 'Cache-Control', 'Content-Type', 'Cookie',
                 'X-Csrf'),
        max_age=dep.get('access_control_max_age'),
        credentials=True,
    )(disp)
