// Copyright 2025 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {
    colors, domLoaded, elmt, findDyn, isPlainObject, isObject, on, qs, qsa,
} from './core.js';

await import(`${tdoc.versions.chartjs}/chart.umd.min.js`);

// Call fn on each attribute of obj, and recurse into arrays and objects.
function visit(obj, fn) {
    const it = obj instanceof Array ? obj.entries() :
               isObject(obj) ? Object.entries(obj) : [];
    for (const [k, v] of it) {
        fn(obj, k, v);
        visit(v, fn);
    }
}

// Merge the attributes of src into dst.
function merge(dst, src) {
    for (const [k, sv] of Object.entries(src)) {
        const dv = dst[k];
        if (isPlainObject(sv) && isObject(dv)) {
            merge(dv, sv);
         } else {
            dst[k] = structuredClone(sv);
        }
    }
    return dst;
}

const colorRe = /^@([a-zA-Z0-9_]+)(?:\/(\d?\.\d*))?$/;

// Expand @color references.
function expandColors(config) {
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
}

// Set defaults.
merge(Chart.defaults, tdoc.dyn.chartjs);
expandColors(Chart.defaults);

// Handle resizing when printing.
function resizeAll() {
    for (const id in Chart.instances) Chart.instances[id].resize();
}

on(window).beforeprint(resizeAll);
on(window).afterprint(resizeAll);

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

template('json', (el, config) => {
    expandColors(config);
    chart(el, config);
});
