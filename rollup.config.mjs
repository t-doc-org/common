// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import * as path from 'node:path';
import * as url from 'node:url';
import resolve from '@rollup/plugin-node-resolve';
import license from 'rollup-plugin-license';

// import.meta.(dir|file)name require Node.js 20.11 or 21.2, but the
// ubuntu-latest image on GitHub only has 18.20.4.
const __filename = import.meta.filename || url.fileURLToPath(import.meta.url)
const __dirname = import.meta.dirname || path.dirname(__filename)

// TODO: Package @sqlite.org/sqlite-wasm. Or maybe it must be an external
//       because of the worker module and .wasm.

export default {
    input: "./tdoc/common/scripts/editor.js",
    output: {
        chunkFileNames: '[name].js',
        compact: true,
        dir: './tdoc/common/static.gen/tdoc/',
        entryFileNames: '[name].js',
        format: 'es',
        generatedCode: {
            arrowFunctions: true,
            constBindings: true,
            objectShorthand: true,
        },
        manualChunks: {},
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
