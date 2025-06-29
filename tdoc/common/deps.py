# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

jsdelivr = 'https://cdn.jsdelivr.net'

info = {
    'pyodide': {
        'version': '0.27.7',
        'url': lambda v: f'{jsdelivr}/pyodide/v{v}/full',
    },
    'sqlite': {
        'version': '3.50.1-build1',
        'url': lambda v: f'{jsdelivr}/npm/@sqlite.org/sqlite-wasm@{v}',
    },
}
