# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

jsdelivr = 'https://cdn.jsdelivr.net'

# TODO: Add constraints on allowed versions

info = {
    'chartjs': {
        'name': 'chart.js',
        'version': '4.5.1',
        'tag': 'latest',
        'url': lambda n, v: f'{jsdelivr}/npm/{n}@{v}/dist',
        'release_urls': [
            'https://github.com/chartjs/Chart.js/releases',
        ],
    },
    'chartjs-chart-boxplot': {
        'name': '@sgratzl/chartjs-chart-boxplot',
        'version': '4.4.5',
        'tag': 'latest',
        'url': lambda n, v: f'{jsdelivr}/npm/{n}@{v}/build',
        'release_urls': [
            'https://github.com/sgratzl/chartjs-chart-boxplot/releases',
        ],
    },
    'chartjs-chart-error-bars': {
        'name': 'chartjs-chart-error-bars',
        'version': '4.4.5',
        'tag': 'latest',
        'url': lambda n, v: f'{jsdelivr}/npm/{n}@{v}/build',
        'release_urls': [
            'https://github.com/sgratzl/chartjs-chart-error-bars/releases',
        ],
    },
    'chartjs-chart-graph': {
        'name': 'chartjs-chart-graph',
        'version': '4.3.5',
        'tag': 'latest',
        'url': lambda n, v: f'{jsdelivr}/npm/{n}@{v}/build',
        'release_urls': [
            'https://github.com/sgratzl/chartjs-chart-graph/releases',
        ],
    },
    'chartjs-chart-venn': {
        'name': 'chartjs-chart-venn',
        'version': '4.3.7',
        'tag': 'latest',
        'url': lambda n, v: f'{jsdelivr}/npm/{n}@{v}/build',
        'release_urls': [
            'https://github.com/upsetjs/chartjs-chart-venn/releases',
        ],
    },
    'chartjs-plugin-annotation': {
        'name': 'chartjs-plugin-annotation',
        'version': '3.1.0',
        'tag': 'latest',
        'url': lambda n, v: f'{jsdelivr}/npm/{n}@{v}/dist',
        'release_urls': [
            'https://github.com/chartjs/chartjs-plugin-annotation/releases',
        ],
    },
    'chartjs-plugin-datalabels': {
        'name': 'chartjs-plugin-datalabels',
        'version': '2.2.0',
        'tag': 'latest',
        'url': lambda n, v: f'{jsdelivr}/npm/{n}@{v}/dist',
        'release_urls': [
            'https://github.com/chartjs/chartjs-plugin-datalabels/releases',
        ],
    },
    'chartjs-plugin-deferred': {
        'name': 'chartjs-plugin-deferred',
        'version': '2.0.0',
        'tag': 'latest',
        'url': lambda n, v: f'{jsdelivr}/npm/{n}@{v}/dist',
        'release_urls': [
            'https://github.com/chartjs/chartjs-plugin-deferred/releases',
        ],
    },
    'drauu': {
        'name': '@drauu/core',
        'version': '1.0.0',
        'tag': 'latest',
        'url': lambda n, v: f'{jsdelivr}/npm/{n}@{v}/dist',
        'release_urls': [
            'https://github.com/antfu/drauu/tags',
        ],
    },
    'jsxgraph': {
        'name': 'jsxgraph',
        'version': '1.12.2',
        'tag': 'latest',
        'url': lambda n, v: f'{jsdelivr}/npm/{n}@{v}/distrib',
    },
    'mathjax': {
        'name': 'mathjax',
        'version': '4.1.3',
        'tag': 'latest',
        'url': lambda n, v: f'{jsdelivr}/npm/{n}@{v}',
        'release_urls': [
            'https://github.com/mathjax/MathJax-src/releases',
        ],
    },
    'mermaid': {
        'name': 'mermaid',
        'version': '11.16.0',
        'tag': 'latest',
        'url': lambda n, v: f'{jsdelivr}/npm/{n}@{v}/dist',
    },
    'mermaid-layout-elk': {
        'name': '@mermaid-js/layout-elk',
        'version': '0.2.2',
        'tag': 'latest',
        'url': lambda n, v: f'{jsdelivr}/npm/{n}@{v}/dist',
    },
    'polyscript': {
        'name': 'polyscript',
        'version': '0.20.13',
        'tag': 'latest',
        'url': lambda n, v: f'{jsdelivr}/npm/{n}@{v}/dist',
        'release_urls': [
            'https://github.com/pyscript/polyscript/tags',
        ],
    },
    'pyodide': {
        'name': 'pyodide',
        'version': '0.29.4',
        'tag': 'latest',
        'url': lambda n, v: f'{jsdelivr}/{n}/v{v}/full',
        'release_urls': [
            'https://pyodide.org/en/stable/project/changelog.html',
        ],
    },
    'sqlite': {
        'name': '@sqlite.org/sqlite-wasm',
        'version': '3.53.0-build1',
        'tag': 'latest',
        'url': lambda n, v: f'{jsdelivr}/npm/{n}@{v}',
        'release_urls': [
            'https://github.com/sqlite/sqlite-wasm/releases',
            'https://www.sqlite.org/changes.html',
        ],
    },
}
