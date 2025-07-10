# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

jsdelivr = 'https://cdn.jsdelivr.net'

info = {
    'drauu': {
        'version': '0.4.3',
        'url': lambda v: f'{jsdelivr}/npm/@drauu/core@{v}/dist',
    },
    'mathjax': {
        'version': '3.2.2',
        'url': lambda v: f'{jsdelivr}/npm/mathjax@{v}/es5',
    },
    'polyscript': {
        'version': '0.17.30',
        'url': lambda v: f'{jsdelivr}/npm/polyscript@{v}/dist',
    },
    'pyodide': {
        'version': '0.27.7',
        'url': lambda v: f'{jsdelivr}/pyodide/v{v}/full',
    },
    'sqlite': {
        'version': '3.50.1-build1',
        'url': lambda v: f'{jsdelivr}/npm/@sqlite.org/sqlite-wasm@{v}',
    },
}
