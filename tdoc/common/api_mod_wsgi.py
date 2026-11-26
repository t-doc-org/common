# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import contextlib
import mod_wsgi
import os
import re
import sys
import threading

from tdoc.common import api, config, http, logs, store, util, ws, wsgi

_log = logs.logger(__name__)


def application(site_repo, events_level=logs.NOTSET):
    threading.current_thread().name = 'main'

    # Load the config and set defaults.
    cfg = config.Server.load(site_repo)
    store_config = cfg.sub('store')
    store_config.setdefault('poll_interval',
                            1 if mod_wsgi.maximum_processes > 1 else 0)
    dep = cfg.sub('deployment')
    aio_threads = dep.get('aio_threads',
                          min(32, (os.process_cpu_count() or 1) + 4))
    store_config.setdefault(
        'pool_size', mod_wsgi.threads_per_process + aio_threads + 4)

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

    # Set up the asyncio thread.
    aio = stack.enter_context(util.AioThread(
        name='aio', stop_on_exit=True, executor_threads=dep.get('aio_threads')))

    # Instantiate the store and the API.
    st = store.Store(config=store_config, aio=aio)
    st.check_version()
    stack.enter_context(st)
    app = stack.enter_context(api.Api(config=cfg, store=st, aio=aio))

    # Set up the request dispatcher.
    disp = http.Dispatcher()
    disp.add(app.endpoints(disp))

    # Set up the websocket server.
    scheme = dep.get('scheme', 'https')
    origins = http.origins(scheme=scheme, domain=domain) \
              if (domain := dep.get('domain')) is not None else util.no_match
    dws = dep.sub('websocket')
    host, path = dws.get('host'), dws.path('path')
    if host is not None or path is not None:
        ws_server = stack.enter_context(ws.Server(
            aio=aio, host=host, port=dws.get('port', 0), path=path,
            perms=dws.get('permissions', 0o600), scheme=scheme,
            origins=origins, remote_addr_header=dws.get('remote_addr_header')))
        ws_server.start_serving(disp)

    return wsgi.cors(
        origins=origins,
        methods=('DELETE', 'GET', 'HEAD', 'OPTIONS', 'POST', 'PUT'),
        headers=('Authorization', 'Cache-Control', 'Content-Type', 'Cookie',
                 'X-Csrf', 'X-Tdoc'),
        max_age=dep.get('access_control_max_age'),
        credentials=True,
    )(disp['wsgi'].handle)
