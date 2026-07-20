# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

jsdelivr = 'https://cdn.jsdelivr.net'

# TODO: Add constraints on allowed versions

def cdn_url(dep, version=None):
    if (d := info.get(dep)) is None: return
    if (cdn := d.get('cdn')) is None: return
    return cdn(d['name'], version if version is not None else d['version'])


info = {
    'cffi': {'version_tag': lambda v: f'v{v}'},
    'chartjs': {
        'name': 'chart.js',
        'version': '4.5.1',
        'tag': 'latest',
        'cdn': lambda n, v: f'{jsdelivr}/npm/{n}@{v}/dist',
        'release_urls': [
            'https://github.com/chartjs/Chart.js/releases',
        ],
    },
    'chartjs-chart-boxplot': {
        'name': '@sgratzl/chartjs-chart-boxplot',
        'version': '4.4.5',
        'tag': 'latest',
        'cdn': lambda n, v: f'{jsdelivr}/npm/{n}@{v}/build',
        'release_urls': [
            'https://github.com/sgratzl/chartjs-chart-boxplot/releases',
        ],
    },
    'chartjs-chart-error-bars': {
        'name': 'chartjs-chart-error-bars',
        'version': '4.4.5',
        'tag': 'latest',
        'cdn': lambda n, v: f'{jsdelivr}/npm/{n}@{v}/build',
        'release_urls': [
            'https://github.com/sgratzl/chartjs-chart-error-bars/releases',
        ],
    },
    'chartjs-chart-graph': {
        'name': 'chartjs-chart-graph',
        'version': '4.3.5',
        'tag': 'latest',
        'cdn': lambda n, v: f'{jsdelivr}/npm/{n}@{v}/build',
        'release_urls': [
            'https://github.com/sgratzl/chartjs-chart-graph/releases',
        ],
    },
    'chartjs-chart-venn': {
        'name': 'chartjs-chart-venn',
        'version': '4.3.7',
        'tag': 'latest',
        'cdn': lambda n, v: f'{jsdelivr}/npm/{n}@{v}/build',
        'release_urls': [
            'https://github.com/upsetjs/chartjs-chart-venn/releases',
        ],
    },
    'chartjs-plugin-annotation': {
        'name': 'chartjs-plugin-annotation',
        'version': '3.1.0',
        'tag': 'latest',
        'cdn': lambda n, v: f'{jsdelivr}/npm/{n}@{v}/dist',
        'release_urls': [
            'https://github.com/chartjs/chartjs-plugin-annotation/releases',
        ],
    },
    'chartjs-plugin-datalabels': {
        'name': 'chartjs-plugin-datalabels',
        'version': '2.2.0',
        'tag': 'latest',
        'cdn': lambda n, v: f'{jsdelivr}/npm/{n}@{v}/dist',
        'release_urls': [
            'https://github.com/chartjs/chartjs-plugin-datalabels/releases',
        ],
    },
    'chartjs-plugin-deferred': {
        'name': 'chartjs-plugin-deferred',
        'version': '2.0.0',
        'tag': 'latest',
        'cdn': lambda n, v: f'{jsdelivr}/npm/{n}@{v}/dist',
        'release_urls': [
            'https://github.com/chartjs/chartjs-plugin-deferred/releases',
        ],
    },
    'drauu': {
        'name': '@drauu/core',
        'version': '1.0.0',
        'tag': 'latest',
        'cdn': lambda n, v: f'{jsdelivr}/npm/{n}@{v}/dist',
        'release_urls': [
            'https://github.com/antfu/drauu/tags',
        ],
    },
    'hatchling': {'version_tag': lambda v: f'hatchling-v{v}'},
    'jsxgraph': {
        'name': 'jsxgraph',
        'version': '1.12.2',
        'tag': 'latest',
        'cdn': lambda n, v: f'{jsdelivr}/npm/{n}@{v}/distrib',
    },
    'mathjax': {
        'name': 'mathjax',
        'version': '4.1.3',
        'tag': 'latest',
        'cdn': lambda n, v: f'{jsdelivr}/npm/{n}@{v}',
        'release_urls': [
            'https://github.com/mathjax/MathJax-src/releases',
        ],
    },
    **{k: {
        'name': f'@mathjax/{k}',
        'version': '4.1.3',
        'tag': 'latest',
        'cdn': lambda n, v: f'{jsdelivr}/npm/{n}@{v}',
        'exclude_from_js': True,
    } for k in [
        # Fonts
        'mathjax-newcm-font',
        'mathjax-asana-font',
        'mathjax-bonum-font',
        'mathjax-dejavu-font',
        'mathjax-fira-font',
        'mathjax-modern-font',
        'mathjax-pagella-font',
        'mathjax-schola-font',
        'mathjax-stix2-font',
        'mathjax-termes-font',
        'mathjax-tex-font',
        # Font extensions
        'mathjax-bbm-font-extension',
        'mathjax-bboldx-font-extension',
        'mathjax-dsfont-font-extension',
        'mathjax-euler-font-extension',
        'mathjax-mhchem-font-extension',
    ]},
    'mermaid': {
        'name': 'mermaid',
        'version': '11.16.0',
        'tag': 'latest',
        'cdn': lambda n, v: f'{jsdelivr}/npm/{n}@{v}/dist',
    },
    'mermaid-layout-elk': {
        'name': '@mermaid-js/layout-elk',
        'version': '0.2.2',
        'tag': 'latest',
        'cdn': lambda n, v: f'{jsdelivr}/npm/{n}@{v}/dist',
    },
    'markdown-it-py': {'version_tag': lambda v: f'v{v}'},
    'mdit-py-plugins': {'version_tag': lambda v: f'v{v}'},
    'myst-parser': {'version_tag': lambda v: f'v{v}'},
    'polyscript': {
        'name': 'polyscript',
        'version': '0.20.13',
        'tag': 'latest',
        'version_tag': lambda v: f'v{v}',
        'cdn': lambda n, v: f'{jsdelivr}/npm/{n}@{v}/dist',
        'release_urls': [
            'https://github.com/pyscript/polyscript/tags',
        ],
    },
    'pydata-sphinx-theme': {'version_tag': lambda v: f'v{v}'},
    'pyodide': {
        'name': 'pyodide',
        'version': '0.29.4',
        'tag': 'latest',
        'cdn': lambda n, v: f'{jsdelivr}/{n}/v{v}/full',
        'release_urls': [
            'https://pyodide.org/en/stable/project/changelog.html',
        ],
    },
    'sphinx-book-theme': {'version_tag': lambda v: f'v{v}'},
    'sqlite': {
        'name': '@sqlite.org/sqlite-wasm',
        'version': '3.53.0-build1',
        'tag': 'latest',
        'cdn': lambda n, v: f'{jsdelivr}/npm/{n}@{v}',
        'release_urls': [
            'https://github.com/sqlite/sqlite-wasm/releases',
            'https://www.sqlite.org/changes.html',
        ],
    },
}
