# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import sys

from tdoc import common
from tdoc.common.defaults import *

project = "t-doc"
copyright = "%Y Remy Blank"
license = 'MIT'
language = 'en'

keep_warnings = True

html_theme_options = {
    'repository_url': 'https://github.com/t-doc-org/common',
}

tdoc_enable_sab = 'no'
# tdoc_enable_sab = 'cross-origin-isolation'
# tdoc_enable_sab = 'sabayon'

tdoc = {
    'store_url': 'https://api.t-doc.org/store'
                 if 'tdoc-dev' not in tags else None,
}

intersphinx_mapping = {
    'python': (
        f'https://docs.python.org/{sys.version_info[0]}.{sys.version_info[1]}',
        None,
    ),
    'sphinx': ('https://www.sphinx-doc.org/en/master', None),
}
