# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import sys

from tdoc.common.defaults import *

project = "t-doc"
author = "Remy Blank"
license = 'MIT'
language = 'en'

# myst_links_external_new_tab = True

html_logo = 'logo.svg'
html_css_files = ['site-styles.css']
html_theme_options = {
    'repository_url': 'https://github.com/t-doc-org/common',
    'use_download_button': True,
    'show_navbar_depth': 2,
    'show_toc_level': 2,
}

intersphinx_mapping = {
    'python': (
        f'https://docs.python.org/{sys.version_info[0]}.{sys.version_info[1]}',
        ('_cached/python.inv', None),
    ),
    'sphinx': ('https://www.sphinx-doc.org/en/master',
               ('_cached/sphinx.inv', None)),
}
