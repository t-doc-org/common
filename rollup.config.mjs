// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import * as path from 'node:path';
import * as url from 'node:url';
import nodeResolve from '@rollup/plugin-node-resolve';

export default {
    input: "./tdoc/common/scripts/codemirror.js",
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
        nodeResolve(),
    ],
};
