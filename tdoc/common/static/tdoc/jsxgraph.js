// Copyright 2025 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {domLoaded, findDyn, mathJaxReady, qs} from './core.js';

// Import JSXGraph. Get the reference to the JXG namespace from globalThis
// instead of using the module directly, as their content isn't identical,
// which breaks some functions (e.d. deepCopy() fails due to exists() missing).
await import(`${tdoc.versions.jsxgraph}/jsxgraphcore.mjs`);
export const JXG = globalThis.JXG;

// Set global defaults.
const fontSize = 14;
JXG.merge(JXG.Options, {
    board: {
        showCopyright: false,
        showNavigation: false,
        keepAspectRatio: true,
        defaultAxes: {
            x: {
                name: '\\(x\\)',
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
                                                       - zero.usrCoords[1]);
                        return `\\(${v}\\)`;
                    },
                },
            },
            y: {
                name: '\\(y\\)',
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
                                                       - zero.usrCoords[2]);
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

// Mix-in board attributes to disable interactive features.
export const nonInteractive = {
    showNavigation: false,
    registerEvents: {keyboard: false, pointer: false, wheel: false},
};

// Mix-in board attributes to draw only selected labels on the default axes.
export function withAxesLabels(xs, ys) {
    return {
        defaultAxes: {
            x: {ticks: {
                // TODO: Find how to use "labels"
                generateLabelText: function(tick, zero) {
                    const v = this.formatLabelText(tick.usrCoords[1]
                                                   - zero.usrCoords[1]);
                    return !xs || xs.includes(v) ? `\\(${v}\\)` : '';
                },
            }},
            y: {ticks: {
                generateLabelText: function(tick, zero) {
                    const v = this.formatLabelText(tick.usrCoords[2]
                                                   - zero.usrCoords[2]);
                    return !ys || ys.includes(v) ? `\\(${v}\\)` : '';
                },
            }},
        },
    };
}

// Merge attribute sets, with later sets overriding earlier ones.
export function merge(...attrs) {
    const res = {};
    const mergeToRes = (...as) => {
        for (const a of as) {
            if (a instanceof Array) {
                mergeToRes(...a);
            } else {
                JXG.mergeAttr(res, a, true);
            }
        }
    };
    mergeToRes(...attrs);
    return res;
}

// Initialize a board for the {jsxgraph} directive with the given name. Calls
// fn(board) if fn is provided, and returns the board.
export async function initBoard(name, attrs, fn) {
    attrs = merge(attrs);
    await domLoaded;
    const node = findDyn('jsxgraph', name);
    if (node.style.aspectRatio === ''
            && getComputedStyle(node).aspectRatio === '142857 / 142857') {
        const a = JXG.copyAttributes(attrs, JXG.Options, 'board');
        if (a.keepaspectratio) {
            const [xn, yp, xp, yn] = a.boundingbox;
            node.style.aspectRatio = `${xp - xn} / ${yp - yn}`;
        }
    }
    await mathJaxReady;
    const board = JXG.JSXGraph.initBoard(node, attrs);
    const defaults = attrs.defaults ?? {};
    if (defaults) JXG.merge(board.options, defaults);
    if (fn) fn(board);
    node.classList.add('rendered');
    return board;
}
