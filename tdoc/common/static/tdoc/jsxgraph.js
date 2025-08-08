// Copyright 2025 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {domLoaded, qs} from './core.js';

// Import JSXGraph. Get the reference to JXG from globalThis instead of using
// the module directly, as their content isn't identical, which breaks some
// functions (e.d. deepCopy() fails due to exists() missing).
await import(`${tdoc.versions.jsxgraph}/jsxgraphcore.mjs`);
export const JXG = globalThis.JXG;

// Set global defaults.
const fontSize = 14;
JXG.merge(JXG.Options, {
    board: {
        showCopyright: false,
        showNavigation: false,
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
                    majorHeight: 10,
                    minorHeight: 8,
                    strokeOpacity: 0.5,
                    label: {
                        display: 'html',
                        fontSize,
                        offset: [0, -6],
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
                    majorHeight: 10,
                    minorHeight: 8,
                    strokeOpacity: 0.5,
                    label: {
                        display: 'html',
                        fontSize,
                        offset: [-10, 0],
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

export async function render(name, attrs, fn) {
    await domLoaded;
    const node = qs(document,
                    `div.tdoc-jsxgraph[data-name="${CSS.escape(name)}"]`);
    if (!node) {
        console.error(`{jsxgraph} not found: ${name}`);
        return;
    }
    if (node.style.aspectRatio === ''
            && getComputedStyle(node).aspectRatio === '142857 / 142857') {
        const a = JXG.deepCopy(attrs, undefined, true);
        if (a.keepaspectratio) {
            const [xn, yp, xp, yn] = a.boundingbox;
            node.style.aspectRatio = `${xp - xn} / ${yp - yn}`;
        }
    }
    const board = JXG.JSXGraph.initBoard(node, attrs);
    const defaults = attrs.defaults ?? {};
    if (defaults) JXG.merge(board.options, defaults);
    fn(board);
    node.classList.add('rendered');
}

export function nonInteractive(attrs) {
    return JXG.merge({
        showNavigation: false,
        registerEvents: {keyboard: false, pointer: false, wheel: false},
    }, attrs);
}
