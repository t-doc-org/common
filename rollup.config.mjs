// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import path from 'node:path';
import url from 'node:url';
import resolve from '@rollup/plugin-node-resolve';
import license from 'rollup-plugin-license';

// import.meta.(dir|file)name require Node.js 20.11 or 21.2, but the
// ubuntu-latest image on GitHub only has 18.20.4.
const __filename = import.meta.filename || url.fileURLToPath(import.meta.url)
const __dirname = import.meta.dirname || path.dirname(__filename)

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
                output: path.join(__dirname, 'LICENSES.deps.txt'),
                includePrivate: true,
            },
        }),
    ],
};
