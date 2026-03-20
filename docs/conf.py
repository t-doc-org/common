# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

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
    'use_repository_button': True,
    'use_source_button': True,
    'show_navbar_depth': 2,
    'show_toc_level': 2,
    'tdoc_badges': [
        {'href': '/actions/workflows/package.yml',
         'img': '/actions/workflows/package.yml/badge.svg'},
        {'href': 'https://pypi.org/project/t-doc-common/',
         'img': 'https://img.shields.io/pypi/v/t-doc-common.svg?color=blue'},
        {'href': '/actions/workflows/publish.yml',
         'img': '/actions/workflows/publish.yml/badge.svg'},
    ],
}

intersphinx_cache_limit = 14
intersphinx_mapping = {
    'python': (
        f'https://docs.python.org/3', ('_cached/python.inv', None),
    ),
    'sphinx': ('https://www.sphinx-doc.org/en/master',
               ('_cached/sphinx.inv', None)),
}
