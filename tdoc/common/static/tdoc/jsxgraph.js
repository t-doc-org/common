// Copyright 2025 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {
    asyncGet, domLoaded, gcd, instantiateDynTemplate, mathJaxReady, mergeAttrs,
    onSet, qs, qsa, resolveDyn,
} from './core.js';
import {Distribution, Sample} from './math.js';

export {gcd};

// Import JSXGraph. Get the reference to the JXG namespace from globalThis
// instead of using the module directly, as their content isn't identical,
// which breaks some functions (e.d. deepCopy() fails due to exists() missing).
await import(`${tdoc.versions.jsxgraph}/jsxgraphcore.mjs`);
export const JXG = globalThis.JXG;

function generateLabelText(...args) {
    let v = Object.getPrototypeOf(this).generateLabelText.call(this, ...args);
    const label = this.evalVisProp('label');
    if (label.usemathjax) {
        v = v.replace(/\\[()]/g, '');
        if (label.tofraction) {
            // Replace e.g. "3 \\frac{1}{2}" with "\\frac{7}{2}".
            let found = false;
            v = v.replace(
                /(?:(\d+) *)?\\frac\{(\d+)}{(\d+)}/,
                (m, u, n, d) => {
                    found = true;
                    return `\\frac{${+(u ?? 0) * (+d) + (+n)}}{${d}}`;
                });
            if (!found && this.evalVisProp('scaleSymbol')) {
                // Remove a leading "1" or "-1" before a symbol.
                v = v.replace(/(^|\D)1(\D)/, (m, p, s) => `${p}${s}`);
            }
        }
    }
    return `\\(${v}\\)`;
}

// Set global defaults.
const fontSize = 14;
JXG.merge(JXG.Options, {
    board: {
        showCopyright: false,
        showNavigation: false,
        keepAspectRatio: true,
        fullscreen: {scale: 1},
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
                    generateLabelText,
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
                    generateLabelText,
                },
            },
        },
    },
    text: {
        fontSize,
        useMathJax: true,
    },
    grid: {
        includeBoundaries: true,
        strokeOpacity: 0.6,
        major: {face: 'line'},
        minor: {face: 'line', strokeOpacity: 0.3},
    },
});
JXG.merge(JXG.Options, tdoc.dyn.jsxgraph);

// A set of pre-defined attributes.
export const attrs = asyncGet({});

// Merge attribute sets, with later sets overriding earlier ones.
function merge(...as) {
    return mergeAttrs((dst, src) => JXG.mergeAttr(dst, src, true),
                      attrs, ...as);
}

// Mix-in board attributes to disable interactive features.
attrs.nonInteractive = {
    showNavigation: false,
    registerEvents: {keyboard: false, pointer: false, wheel: false},
};

// Mix-in board attributes to draw only selected labels on the default axes.
// For number arguments, the labels that are their multiples are drawn. For
// array arguments, only the listed values are drawn.
export function withAxesLabels(xs, ys) {
    function gen(vs) {
        // This must not be a lambda because JSXGraph binds "this".
        function format(tick, zero, value) {
            let v = this.getDistanceFromZero(zero, tick);
            if (Math.abs(v) < JXG.Math.eps) v = 0;
            v /= this.evalVisProp('scale');
            return (typeof vs === 'number' && !multipleOf(v, vs))
                   || (Array.isArray(vs) && !includesClose(vs, v)) ?
                   '' : generateLabelText.call(this, tick, zero, value);
        }
        return format;
    }
    // TODO: Find how to use "labels"
    return {defaultAxes: {
        x: {ticks: xs ? {generateLabelText: gen(xs)} : {}},
        y: {ticks: ys ? {generateLabelText: gen(ys)} : {}},
    }};
}

// Return true iff v is close to a multiple of n.
function multipleOf(v, n, epsilon = 1e-6) {
    const d = Math.abs((v % n) / n);
    return d < epsilon || (1 - d) < epsilon;
}

// Return true iff values contains a value that is close to v.
function includesClose(values, v, epsilon = 1e-6) {
    return values.some(value => Math.abs(value - v) < epsilon);
}

// Initialize a board for a {jsxgraph} directive, identified either by name or
// by its wrapper element. Calls fn(board) if fn is provided, and returns the
// board.
export async function initBoard(el, attrs, fn) {
    attrs = await merge(attrs);
    el = await resolveDyn('jsxgraph', el);
    if (el.style.aspectRatio === ''
            && getComputedStyle(el).aspectRatio === '142857 / 142857') {
        const a = JXG.copyAttributes(attrs, JXG.Options, 'board');
        if (a.keepaspectratio) {
            const [xn, yp, xp, yn] = a.boundingbox;
            el.style.aspectRatio = `${xp - xn} / ${yp - yn}`;
        }
    }
    await mathJaxReady;
    const board = JXG.JSXGraph.initBoard(el, attrs);
    JXG.merge(board.options, attrs.defaults ?? {});
    if (fn) fn(board);
    el.classList.add('rendered');
    return board;
}

// Template container.
export const templates = onSet({}, (obj, name, fn) => {
    if (obj[name] !== undefined) {
        throw new Error(`{jsxgraph} Duplicate template: ${name}`);
    }
    instantiateDynTemplate('jsxgraph', name, fn);
});

templates.grid = (el, {width = 35, height = 10, grid = {}, board = {}}) => {
    return initBoard(el, [
        {
            boundingBox: [0, 0, width, -height],
            grid: {majorStep: 1, minorElements: 0},
        },
        {grid}, attrs.nonInteractive, board,
    ]);
};

templates.axes = (el, {boundingBox = [-11, 11, 11, -11], majorX, majorY, major,
                       minorX, minorY, minor, labelsX, labelsY, labels,
                       grid, board}) => {
    return initBoard(el, [
        {
            boundingBox, axis: true, grid: true,
            defaultAxes: {
                x: {ticks: {
                    insertTicks: false,
                    ticksDistance: majorX ?? major ?? 1,
                    minorTicks: minorX ?? minor ?? 0,
                }},
                y: {ticks: {
                    insertTicks: false,
                    ticksDistance: majorY ?? major ?? 1,
                    minorTicks: minorY ?? minor ?? 0,
                }},
            },
        },
        withAxesLabels(labelsX ?? labels,
                       labelsY ?? labels),
        {grid: grid ?? {}}, attrs.nonInteractive, board ?? [],
    ]);
};

function noNegLabels(tick, zero, value) {
    return this.getDistanceFromZero(zero, tick) >= 0 ?
           generateLabelText.call(this, tick, zero, value) : '';
}

templates['cumulative-distribution-function'] = async (el, {
    sample, distribution, min, max, step, normalize = true, yAnchor = 0.08,
    defaults = {}, options = {},
}) => {
    let ds, cdf;
    if (sample !== undefined) {
        ds = sample = new Sample(sample);
        distribution = undefined;
        cdf = sample.cumulativeDistributionFunction(normalize);
    } else if (distribution !== undefined) {
        ds = distribution = Distribution.of(distribution);
        cdf = distribution.cumulativeDistributionFunction(normalize);
    } else {
        throw new Error(`\
{jsxgraph} cumulative-distribution-function: Either sample or distribution is\
 required`);
    }

    min ??= ds.min - 0.05 * ds.range;
    max ??= ds.max + 0.05 * ds.range;
    const last = cdf[cdf.length - 1][1];
    const bounds = [min - yAnchor * (max - min), 1.1 * last, max, -0.15 * last];

    function f(x) {
        if (x < cdf[0][0]) return 0;
        for (let i = 1; i < cdf.length; ++i) {
            if (x < cdf[i][0]) return cdf[i - 1][1];
        }
        return cdf[cdf.length - 1][1];
    }

    return initBoard(el, [
        defaults,
        {
            boundingBox: bounds, keepAspectRatio: false, axis: true,
            zoom: {factorY: 1},
            defaultAxes: {
                x: {
                    ticks: {
                        insertTicks: true, majorHeight: -1, minorHeight: 10,
                        drawZero: true, includeBoundaries: true,
                        strokeOpacity: 0.25,
                    },
                },
                y: {
                    name: '\\[f\\]',
                    position: 'fixed', anchor: 'left',
                    anchorDist: `${1 - 1 / (1 + yAnchor)}fr`,
                    ticks: {
                        insertTicks: true, majorHeight: -1, minorHeight: 10,
                        strokeOpacity: 0.25,
                        generateLabelText: noNegLabels,
                    },
                },
            },
            defaults: {
                functiongraph: {strokeWidth: 3},
                point: {size: 2, strokeWidth: 1, fixed: true, withLabel: false},
            },
        },
        options,
    ], board => {
        board.create('functiongraph',
                     [f, min - 0.5 * (max - min), max + 0.5 * (max - min)]);
        for (let i = 0; i < cdf.length; ++i) {
            const v = cdf[i][0];
            board.create('point', [v, i === 0 ? 0 : cdf[i - 1][1]],
                         {fillColor: JXG.palette.white});
            board.create('point', [v, cdf[i][1]]);
        }
        board.on('boundingbox', () => {
            const box = board.getBoundingBox(), nbox = [...box];
            nbox[1] = bounds[1];
            nbox[3] = bounds[3];
            if (nbox.some((v, i) => v !== box[i])) board.setBoundingBox(nbox);
        });
    });
};
