# Copyright 2026 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import mod_wsgi
import pathlib
import sys

from tdoc.common import api_mod_wsgi, config, logs

base = pathlib.Path(__file__).parent.parent.resolve()
sys.stderr.write(
    f"[{base.name}] Starting (processes: {mod_wsgi.maximum_processes}, "
    f"threads: {mod_wsgi.threads_per_process})\n")

application = api_mod_wsgi.application(
    config_path=(base / config.local).resolve(),
    events_level=logs.NOTSET)
