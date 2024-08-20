# Copyright 2024 Caroline Blank <caro@c-space.org>
# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import time

from tdoc.common.defaults import *

project = "t-doc"
copyright = f"{time.strftime('%Y')} Remy Blank"
license = 'MIT'
language = 'en'

keep_warnings = True

html_theme_options = {
    'repository_url': 'https://github.com/t-doc-org/common',
}
