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
    # 'sphinx.ext.duration',
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
    'tdoc.common.ext.chart',
    'tdoc.common.ext.defaults',
    'tdoc.common.ext.diagram',
    'tdoc.common.ext.exec',
    'tdoc.common.ext.iframe',
    'tdoc.common.ext.layout',
    'tdoc.common.ext.math',
    'tdoc.common.ext.metadata',
    'tdoc.common.ext.num',
    'tdoc.common.ext.poll',
    'tdoc.common.ext.quiz',
    'tdoc.common.ext.solution',
    'tdoc.common.ext.table',
]

suppress_warnings = [
    'myst.strikethrough',  # Only supported for HTML, but that's all we want
]

# Extension options.
graphviz_output_format = 'svg'
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
mathjax4_config = {
    'loader': {
        'load': ['input/mml'],
    },
    'output': {
        'font': 'mathjax-newcm',
        'fontExtensions': [],
    },
    'options': {
        'menuOptions': {
            'settings': {
                'inTabOrder': False,
                'enrich': False,
                'speech': False,
                'braille': False,
            },
        },
    },
    'chtml': {
        'mtextInheritFont': True,
    },
    'svg': {
        'mtextInheritFont': True,
        'blacker': 0,
    },
    # From: https://docs.mathjax.org/en/stable/input/tex/extensions/index.html
    'tdoc_tex_extensions': [
        'action',
        # 'ams',                # Included in combined package
        'amscd',
        # 'autoload',           # Included in combined package
        'bbm',
        'bboldx',
        'bbox',
        'begingroup',
        'boldsymbol',
        'braket',
        'bussproofs',
        'cancel',
        'cases',
        'centernot',
        'color',
        'colortbl',
        # 'colorv2',            # Non-standard
        # 'configmacros',       # Included in combined package
        'dsfont',
        'empheq',
        'enclose',
        'extpfeil',
        'gensymb',
        'html',
        'mathtools',
        'mhchem',
        # 'newcommand',         # Included in combined package
        'noerrors',
        # 'noundefined',        # Included in combined package
        # 'physics',            # Redefines many standard macros
        # 'require',            # Included in combined package
        'setoptions',
        'tagformat',
        'texhtml',
        'textcomp',
        # 'textmacros',         # Included in combined package
        'unicode',
        'units',
        'upgreek',
        'verb',
    ],
}

# Domain storage options.
tdoc_domain_storage = {
    'origin': 'https://t-doc.org',
}
