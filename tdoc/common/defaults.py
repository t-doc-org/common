# Copyright 2024 Caroline Blank <caro@c-space.org>
# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

from importlib import metadata as _metadata
import pathlib

# Sphinx options.
author = ''
language = 'fr'
smartquotes = False
primary_domain = None
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
    # TODO: sphinx_exercise force "numfig = True", et la numérotation ne peut
    #       pas être désactivée par type, page ou bloc
    #       <https://github.com/sphinx-doc/sphinx/issues/10316>.
    # 'sphinx_exercise',
    # TODO: sphinx_proof force "numfig = True", et empêche la parallélisation
    #       de la compilation.
    # 'sphinx_proof',
    'sphinx_togglebutton',
    'tdoc.common',
]

# Extension options.
graphviz_output_format = 'svg'
todo_include_todos = True

# MyST options.
myst_enable_extensions = [
    'amsmath',
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
]
myst_dmath_double_inline = True

# HTML rendering options.
html_show_sphinx = False
html_theme = 't-doc'
html_theme_options = {
    'use_sidenotes': True,
    'path_to_docs': 'docs',
}

# LaTeX rendering options.
latex_engine = 'xelatex'
