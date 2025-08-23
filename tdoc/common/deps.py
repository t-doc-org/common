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
    'jsxgraph': {
        # https://www.npmjs.com/package/jsxgraph?activeTab=versions
        # https://github.com/jsxgraph/jsxgraph/releases
        'version': '1.11.1',
        'url': lambda v: f'{jsdelivr}/npm/jsxgraph@{v}/distrib',
    },
    'mathjax': {
        # https://www.npmjs.com/package/mathjax?activeTab=versions
        # https://github.com/mathjax/MathJax/releases
        'version': '3.2.2',
        'url': lambda v: f'{jsdelivr}/npm/mathjax@{v}/es5',
    },
    'mermaid': {
        # https://www.npmjs.com/package/mermaid?activeTab=versions
        # https://github.com/mermaid-js/mermaid/releases
        'version': '11.10.1',
        'url': lambda v: f'{jsdelivr}/npm/mermaid@{v}/dist',
    },
    'mermaid-layout-elk': {
        # https://www.npmjs.com/package/@mermaid-js/layout-elk?activeTab=versions
        # https://github.com/mermaid-js/mermaid/releases
        'version': '0.1.9',
        'url': lambda v: f'{jsdelivr}/npm/@mermaid-js/layout-elk@{v}/dist',
    },
    'polyscript': {
        # https://www.npmjs.com/package/polyscript?activeTab=versions
        # https://github.com/pyscript/polyscript/tags
        'version': '0.18.10',
        'url': lambda v: f'{jsdelivr}/npm/polyscript@{v}/dist',
    },
    'pyodide': {
        # https://www.npmjs.com/package/pyodide?activeTab=versions
        # https://pyodide.org/en/stable/project/changelog.html
        'version': '0.28.2',
        'url': lambda v: f'{jsdelivr}/pyodide/v{v}/full',
    },
    'sqlite': {
        # https://www.npmjs.com/package/@sqlite.org/sqlite-wasm?activeTab=versions
        # https://github.com/sqlite/sqlite-wasm/releases
        # https://www.sqlite.org/changes.html
        'version': '3.50.4-build1',
        'url': lambda v: f'{jsdelivr}/npm/@sqlite.org/sqlite-wasm@{v}',
    },
}
