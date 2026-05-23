// Copyright 2025 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {
    domLoaded, elmt, instantiateDynTemplate, isPlainObject, isObject, on, qs,
    qsa, resolveDyn,
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
function mergeAttr(dst, src) {
    for (const [k, sv] of Object.entries(src)) {
        const dv = dst[k];
        if (isPlainObject(sv) && isObject(dv)) {
            mergeAttr(dv, sv);
         } else {
            dst[k] = structuredClone(sv);
        }
    }
    return dst;
}

// Format a tick value on a scale.
function formatTick(scale, value) {
    return Chart.Ticks.formatters.numeric.apply(scale, [value, 0, scale.ticks]);
}

// Set defaults.
mergeAttr(Chart.defaults, tdoc.dyn.chartjs);

// Handle resizing when printing.
function resizeAll() {
    for (const id in Chart.instances) Chart.instances[id].resize();
}

on(window).beforeprint(resizeAll);
on(window).afterprint(resizeAll);

// Initialize a chart for a {chartjs} directive, identified either by name or
// by its wrapper element.
export async function chart(el, config) {
    el = await resolveDyn('chartjs', el);
    const c = new Chart(el.appendChild(elmt`<canvas role="img"></canvas>`),
                        config);
    el.classList.add('rendered');
    return c;
}

// Define a template.
export function template(name, fn) {
    return instantiateDynTemplate('chartjs', name, fn);
}

template('chart', chart);

export async function histogram(el, {bins, options, samples}) {
    el = await resolveDyn('chartjs', el);

    // Define bins.
    let min = Infinity, max = -Infinity;
    for (const s of samples) {
        if (s < min) min = s;
        if (s > max) max = s;
    }
    let bmin = bins?.min, bw = bins?.width, bc = bins?.count;
    const bmax = Math.max(bins?.max ?? -Infinity, max);
    if (bw === undefined) {
        bmin = Math.min(bmin ?? Infinity, min);
        if (bc === undefined) bc = Math.ceil(Math.sqrt(samples.length));
        bw = (bmax - bmin) / bc;
        if (bw <= 0) bw = 1;
    } else {
        if (bmin === undefined) {
            const bo = bins?.origin ?? 0;
            bmin = bo + Math.floor((min - bo) / bw) * bw;
        }
        bc = Math.max(bc ?? 0, Math.floor((bmax - bmin) / bw) + 1);
    }

    // Compute histogram data.
    const data = [];
    for (let b = 0; b < bc; ++b) data.push({x: bmin + (b + 0.5) * bw, y: 0});
    for (const s of samples) {
        let b = Math.floor((s - bmin) / bw);
        if (b >= data.length) b = data.length - 1;
        ++data[b].y;
    }

    const config = {
        type: 'bar',
        data: {datasets: [{data}]},
        options: {
            barPercentage: 1, categoryPercentage: 1,
            scales: {
                x: {
                    type: 'linear',
                    min: bmin, max: bmin + data.length * bw,
                    offset: false,
                    grid: {offset: false},
                    ticks: {stepSize: bw},
                },
                y: {beginAtZero: true, ticks: {stepSize: 1}},
            },
            plugins: {
                legend: {display: false},
                tooltip: {
                    callbacks: {
                        title: items => {
                            if (items.length === 0) return "";
                            const it = items[0];
                            const sx = it.chart.scales.x, x = it.parsed.x;
                            const rl = formatTick(sx, x - 0.5 * bw);
                            const ru = formatTick(sx, x + 0.5 * bw);
                            const c = x === data[data.length - 1].x ? "]" : "[";
                            return `[${rl}; ${ru}${c}`;
                        },
                    },
                },
            },
        },
    };
    mergeAttr(config.options, options ?? {});
    return await chart(el, config);
}

template('histogram', histogram);
