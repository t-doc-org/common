# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import platform
import sys

from polyscript import xworker
from pyodide_js import version

sys.path.append('/lib/tdoc.zip')
import tdoc.core  # noqa

xworker.sync.ready(f"{platform.python_implementation()}"
                   f" {'.'.join(platform.python_version_tuple())}"
                   f" on {platform.platform()},"
                   f" using Pyodide {version}"
                   f" (polyfill: {xworker.polyfill})")
