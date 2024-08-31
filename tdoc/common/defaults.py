# Copyright 2024 Caroline Blank <caro@c-space.org>
# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

# Sphinx options.
author = ''
language = 'fr'
smartquotes = False
primary_domain = None
nitpicky = True
exclude_patterns = ['_build', '.DS_Store', 'Thumbs.db']
highlight_language = 'text'

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
    # TODO: sphinx_exercise forces "numfig = True", and numbering cannot be
    #       disabled per type, page or block
    #       <https://github.com/sphinx-doc/sphinx/issues/10316>.
    # 'sphinx_exercise',
    # TODO: sphinx_proof forces "numfig = True", and prevents build
    #       parallelization.
    # 'sphinx_proof',
    'sphinx_togglebutton',
    'tdoc.common',
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

# LaTeX rendering options.
latex_engine = 'xelatex'
