// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import * as path from 'node:path';
import resolve from '@rollup/plugin-node-resolve';
import license from 'rollup-plugin-license';

export default {
    input: "./tdoc/common/scripts/tdoc-editor.js",
    output: {
        chunkFileNames: '[name].gen.js',
        compact: true,
        dir: './tdoc/common/static/',
        entryFileNames: '[name].gen.js',
        format: 'es',
        generatedCode: {
            arrowFunctions: true,
            constBindings: true,
            objectShorthand: true,
        },
        // TODO: Package @sqlite.org/sqlite-wasm as well. Or maybe it must
        //       be an external because of the worker module and .wasm
        manualChunks: {
            'tdoc-cm': ['codemirror'],
            'tdoc-cm-css': ['@codemirror/lang-css'],
            'tdoc-cm-html': ['@codemirror/lang-html'],
            'tdoc-cm-javascript': ['@codemirror/lang-javascript'],
            'tdoc-cm-python': ['@codemirror/lang-python'],
            'tdoc-cm-sql': ['@codemirror/lang-sql'],
        },
    },
    plugins: [
        resolve(),
        license({
            thirdParty: {
                output: path.join(import.meta.dirname, 'LICENSES.deps.txt'),
                includePrivate: true,
            },
        }),
    ],
};
