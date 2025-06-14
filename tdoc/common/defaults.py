# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

# Sphinx options.
author = ''
language = 'fr'
smartquotes = False
primary_domain = None
numfig = True
highlight_language = 'text'
nitpicky = True
exclude_patterns = ['_build', '.DS_Store', 'Thumbs.db']

extensions = [
    'myst_parser',
    'sphinx.ext.duration',
    'sphinx.ext.extlinks',
    'sphinx.ext.githubpages',
    'sphinx.ext.graphviz',
    'sphinx.ext.ifconfig',
    'sphinx.ext.imgconverter',
    'sphinx.ext.intersphinx',
    'sphinx.ext.mathjax',
    'sphinx.ext.todo',
    'sphinx_copybutton',
    'sphinx_design',
    'tdoc.common.ext',
    'tdoc.common.ext.defaults',
    'tdoc.common.ext.exec',
    'tdoc.common.ext.iframe',
    'tdoc.common.ext.metadata',
    'tdoc.common.ext.num',
    'tdoc.common.ext.poll',
    'tdoc.common.ext.quiz',
    'tdoc.common.ext.solution',
]

suppress_warnings = [
    'myst.strikethrough',  # Only supported for HTML, but that's all we want
]

# Extension options.
# The graphviz extension embeds SVG images as <object> tags. This causes them
# to be loaded as separate documents, which doesn't play well with the
# Cross-Origin Isolation workaround (the requests don't get intercepted, lack
# the necessary headers, and therefore get blocked). PNG images are embedded
# as <img>, which don't have this issue.
graphviz_output_format = 'png'
todo_include_todos = True

# MyST options.
myst_enable_extensions = {
    'amsmath',
    'attrs_block',
    'attrs_inline',
    'colon_fence',
    'deflist',
    'dollarmath',
    'fieldlist',
    'html_admonition',
    'html_image',
    # 'linkify',
    # 'replacements',
    'strikethrough',
    'substitution',
    'tasklist',
}
myst_dmath_double_inline = True
myst_heading_anchors = 6

# HTML rendering options.
html_show_sphinx = False
html_theme = 't-doc'

# MathJax options.
mathjax_path = 'mathjax/tex-chtml-full.js'
mathjax3_config = {
    'loader': {'load': ['input/mml']},
    'options': {
        'menuOptions': {'settings': {'inTabOrder': False}},
    },
}

# LaTeX rendering options.
latex_engine = 'xelatex'
