# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

jsdelivr = 'https://cdn.jsdelivr.net'

# TODO: Add constraints on allowed versions

info = {
    'drauu': {
        'name': '@drauu/core',
        'version': '0.4.3',
        'tag': 'latest',
        'url': lambda n, v: f'{jsdelivr}/npm/{n}@{v}/dist',
        'docs': [
            'https://github.com/antfu/drauu/tags',
        ],
    },
    'jsxgraph': {
        'name': 'jsxgraph',
        'version': '1.11.1',
        'tag': 'latest',
        'url': lambda n, v: f'{jsdelivr}/npm/{n}@{v}/distrib',
        'docs': [
            'https://github.com/jsxgraph/jsxgraph/releases',
        ],
    },
    'mathjax': {
        'name': 'mathjax',
        'version': '3.2.2',
        'tag': 'latest',
        'url': lambda n, v: f'{jsdelivr}/npm/{n}@{v}/es5',
        'docs': [
            'https://github.com/mathjax/MathJax/releases',
        ],
    },
    'mermaid': {
        'name': 'mermaid',
        'version': '11.12.0',
        'tag': 'latest',
        'url': lambda n, v: f'{jsdelivr}/npm/{n}@{v}/dist',
        'docs': [
            'https://github.com/mermaid-js/mermaid/releases',
        ],
    },
    'mermaid-layout-elk': {
        'name': '@mermaid-js/layout-elk',
        'version': '0.2.0',
        'tag': 'latest',
        'url': lambda n, v: f'{jsdelivr}/npm/{n}@{v}/dist',
        'docs': [
            'https://github.com/mermaid-js/mermaid/releases',
        ],
    },
    'polyscript': {
        'name': 'polyscript',
        'version': '0.18.14',
        'tag': 'latest',
        'url': lambda n, v: f'{jsdelivr}/npm/{n}@{v}/dist',
        'docs': [
            'https://github.com/pyscript/polyscript/tags',
        ],
    },
    'pyodide': {
        'name': 'pyodide',
        'version': '0.28.3',
        'tag': 'latest',
        'url': lambda n, v: f'{jsdelivr}/{n}/v{v}/full',
        'docs': [
            'https://pyodide.org/en/stable/project/changelog.html',
        ],
    },
    'sqlite': {
        'name': '@sqlite.org/sqlite-wasm',
        'version': '3.50.4-build1',
        'tag': 'latest',
        'url': lambda n, v: f'{jsdelivr}/npm/{n}@{v}',
        'docs': [
            'https://github.com/sqlite/sqlite-wasm/releases',
            'https://www.sqlite.org/changes.html',
        ],
    },
}
