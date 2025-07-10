# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

jsdelivr = 'https://cdn.jsdelivr.net'

info = {
    'drauu': {
        # https://www.npmjs.com/package/@drauu/core?activeTab=versions
        # https://github.com/antfu/drauu/tags
        'version': '0.4.3',
        'url': lambda v: f'{jsdelivr}/npm/@drauu/core@{v}/dist',
    },
    'mathjax': {
        # https://www.npmjs.com/package/mathjax?activeTab=versions
        # https://github.com/mathjax/MathJax/releases
        'version': '3.2.2',
        'url': lambda v: f'{jsdelivr}/npm/mathjax@{v}/es5',
    },
    'polyscript': {
        # https://www.npmjs.com/package/polyscript?activeTab=versions
        # https://github.com/pyscript/polyscript/tags
        'version': '0.18.2',
        'url': lambda v: f'{jsdelivr}/npm/polyscript@{v}/dist',
    },
    'pyodide': {
        # https://www.npmjs.com/package/pyodide?activeTab=versions
        # https://pyodide.org/en/stable/project/changelog.html
        'version': '0.28.0',
        'url': lambda v: f'{jsdelivr}/pyodide/v{v}/full',
    },
    'sqlite': {
        # https://www.npmjs.com/package/@sqlite.org/sqlite-wasm?activeTab=versions
        # https://github.com/sqlite/sqlite-wasm/releases
        'version': '3.50.1-build1',
        'url': lambda v: f'{jsdelivr}/npm/@sqlite.org/sqlite-wasm@{v}',
    },
}
