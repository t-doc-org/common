// Copyright 2025 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {colors, domLoaded, elmt, findDyn, on, qs, qsa} from './core.js';

// TODO: Handle theme changes: change defaults and redraw on theme changes
// TODO: Allow specifying an array of configs

await import(`${tdoc.versions.chartjs}/chart.umd.min.js`);

// Set defaults.
// TODO: Set appropriate defaults
// console.log(Chart.defaults);

// Handle resizing when printing.
function resizeAll() {
    for (const id in Chart.instances) Chart.instances[id].resize();
}

on(window).beforeprint(resizeAll);
on(window).afterprint(resizeAll);

function visit(obj, fn) {
    const it = obj instanceof Array ? obj.entries() :
               typeof obj === 'object'
                   && Object.getPrototypeOf(obj).isPrototypeOf(Object) ?
               Object.entries(obj) : [];
    for (const [k, v] of it) {
        fn(obj, k, v);
        visit(v, fn);
    }
}

// Initialize a chart for a {chartjs} directive, identified either by name or
// by its wrapper element.
export async function chart(el, config) {
    if (typeof el === 'string') {
        await domLoaded;
        el = findDyn('chartjs', el);
    }
    const c = new Chart(el.appendChild(elmt`<canvas role="img"></canvas>`),
                        config);
    el.classList.add('rendered');
    return c;
}

// Define a template.
export async function template(name, fn) {
    await domLoaded;
    for (const el of qsa(document, `\
div.tdoc-dyn[data-type=chartjs][data-template="${CSS.escape(name)}"]`)) {
        const args = el.dataset.args ? JSON.parse(el.dataset.args) : [];
        fn(el, args);
    }
}

const colorRe = /^@([a-zA-Z0-9_]+)(?:\/(\d?\.\d*))?$/;

template('json', (el, config) => {
    // Expand @color references.
    visit(config, (obj, k, v) => {
        if (typeof k === 'string' && (k === 'color' || k.endsWith('Color'))
                && typeof v === 'string') {
            const m = v.match(colorRe);
            if (!m) return;
            let c = colors[m[1]];
            if (c === undefined) {
                console.warn(`Unknown color: ${v}`);
                return;
            }
            if (m[2] !== undefined) c = c.with({a: parseFloat(m[2])});
            obj[k] = c.rgb();
        }
    });
    chart(el, config);
});
