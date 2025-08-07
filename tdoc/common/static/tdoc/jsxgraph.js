// Copyright 2025 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {domLoaded, qs} from './core.js';

export const JXG = await import(`${tdoc.versions.jsxgraph}/jsxgraphcore.mjs`);

// Set global defaults.
const fontSize = 14;
JXG.merge(JXG.Options, {
    board: {
        showCopyright: false,
        defaultAxes: {
            x: {
                name: `\\(x\\)`,
                withLabel: true,
                label: {
                    position: '1fr left',
                    anchorX: 'right',
                    anchorY: 'bottom',
                    distance: 0,
                    offset: [0, 0],
                },
                ticks: {
                    label: {
                        display: 'html',
                        fontSize,
                    },
                    generateLabelText: function(tick, zero) {
                        const v = this.formatLabelText(tick.usrCoords[1]
                                                       - zero.usrCoords[1])
                        return `\\(${v}\\)`;
                    },
                },
            },
            y: {
                name: `\\(y\\)`,
                withLabel: true,
                label: {
                    position: '1fr right',
                    anchorX: 'left',
                    anchorY: 'top',
                    distance: 0,
                    offset: [8, 7],
                },
                ticks: {
                    label: {
                        display: 'html',
                        fontSize,
                    },
                    generateLabelText: function(tick, zero) {
                        const v = this.formatLabelText(tick.usrCoords[2]
                                                       - zero.usrCoords[2])
                        return `\\(${v}\\)`;
                    },
                },
            },
        },
    },
    text: {
        fontSize,
        useMathJax: true,
    },
});

export function render(name, attrs, fn) {
    domLoaded.then(() => {
        const node = qs(document,
                        `div.tdoc-jsxgraph[data-name="${CSS.escape(name)}"]`);
        if (!node) {
            console.error(`{jsxgraph} not found: ${name}`);
            return;
        }
        const board = JXG.JSXGraph.initBoard(node, attrs);
        const defaults = attrs.defaults ?? {};
        if (defaults) JXG.merge(board.options, defaults);
        fn(board);
        node.classList.add('rendered');
    });
}

export function nonInteractive(attrs) {
    return JXG.merge({
        showNavigation: false,
        registerEvents: {keyboard: false, pointer: false, wheel: false},
    }, attrs);
}
