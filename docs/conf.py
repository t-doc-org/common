# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import sys

from tdoc.common.defaults import *

project = "t-doc"
copyright = "%Y Remy Blank"
license = 'MIT'
language = 'en'

# myst_links_external_new_tab = True

html_theme_options = {
    'repository_url': 'https://github.com/t-doc-org/common',
}

tdoc_enable_sab = 'no'
# tdoc_enable_sab = 'cross-origin-isolation'
# tdoc_enable_sab = 'sabayon'

intersphinx_mapping = {
    'python': (
        f'https://docs.python.org/{sys.version_info[0]}.{sys.version_info[1]}',
        None,
    ),
    'sphinx': ('https://www.sphinx-doc.org/en/master', None),
}
