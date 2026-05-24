// Copyright 2025 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {
    asyncGet, domLoaded, elmt, instantiateDynTemplate, isPlainObject, isObject,
    mergeAttrs, on, onSet, qs, qsa, resolveDyn,
} from './core.js';

await import(`${tdoc.versions.chartjs}/chart.umd.min.js`);

// Merge src into dst.
function mergeTo(dst, src) {
    const it = Array.isArray(src) ? src.entries() : Object.entries(src);
    for (const [k, sv] of it) {
        if (Array.isArray(sv)) {
            // Only merge into arrays of objects; overwrite otherwise.
            let dv = dst[k];
            if (dv === undefined || dv === null || !Array.isArray(dv)
                    || !dv.every(v => isObject(v))) {
                dv = dst[k] = [];
            }
            mergeTo(dv, sv);
        } else if (isObject(sv) && typeof sv.valueOf() !== 'string') {
            let dv = dst[k];
            if (dv === undefined || dv === null || !isObject(dv)) {
                dv = dst[k] = {};
            }
            mergeTo(dv, sv);
        } else if (sv !== undefined && sv !== null) {
            dst[k] = sv;
        }
    }
    return dst;
}

// Set global defaults.
mergeTo(Chart.defaults, tdoc.dyn.chartjs);

// A set of pre-defined attributes.
export const attrs = asyncGet({});

// Merge attribute sets, with later sets overriding earlier ones.
function merge(...as) {
    return mergeAttrs(mergeTo, attrs, ...as);
}

// Format a tick value on a scale.
function formatTick(scale, value) {
    return Chart.Ticks.formatters.numeric.apply(scale, [value, 0, scale.ticks]);
}

// Handle resizing when printing.
function resizeAll() {
    for (const id in Chart.instances) Chart.instances[id].resize();
}

on(window).beforeprint(resizeAll);
on(window).afterprint(resizeAll);

// Initialize a chart for a {chartjs} directive, identified either by name or
// by its wrapper element.
export async function chart(el, config) {
    config = await merge(config);
    el = await resolveDyn('chartjs', el);
    const c = new Chart(el.appendChild(elmt`<canvas role="img"></canvas>`),
                        config);
    el.classList.add('rendered');
    return c;
}

// Template container.
export const templates = onSet({}, (obj, name, fn) => {
    if (obj[name] !== undefined) {
        throw new Error(`{chartjs} Duplicate template: ${name}`);
    }
    instantiateDynTemplate('chartjs', name, fn);
});

templates.chart = chart;

templates.histogram = async (el, {bins, options = {}, samples}) => {
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

    return await chart(el, [{
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
    }, {options}]);
};
