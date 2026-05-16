// Copyright 2025 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {domLoaded, elmt, findDyn, on, qs, qsa} from './core.js';

// TODO: Handle theme changes: change defaults and redraw on theme changes
// TODO: Allow specifying an array of configs

await import(`${tdoc.versions.chartjs}/chart.umd.min.js`);

// Set defaults.
// console.log(Chart.defaults);
// Chart.defaults.maintainAspectRatio = false;

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
        fn(el, ...args);
    }
}

// TODO: Add a template for a pie chart
