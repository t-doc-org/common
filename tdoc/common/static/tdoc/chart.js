// Copyright 2025 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {
    asyncGet, domLoaded, elmt, instantiateDynTemplate, isPlainObject, isObject,
    mergeAttrs, on, onSet, qs, qsa, resolveDyn,
} from './core.js';
import {Bins, Sample} from './math.js';

// TODO: Add plugins from page metadata
const plugins = {
    'chartjs-chart-boxplot': {path: 'index.umd.min.js'},
    'chartjs-chart-error-bars': {path: 'index.umd.min.js'},
    'chartjs-chart-graph': {path: 'index.umd.min.js'},
    'chartjs-chart-venn': {path: 'index.umd.min.js'},
    'chartjs-chart-wordcloud': {path: 'index.umd.min.js'},
    'chartjs-plugin-annotation': {path: 'chartjs-plugin-annotation.min.js'},
    'chartjs-plugin-datalabels': {
        path: 'chartjs-plugin-datalabels.min.js',
        register: ['ChartDataLabels'],
    },
    'chartjs-plugin-deferred': {
        path: 'chartjs-plugin-deferred.min.js', register: ['ChartDeferred'],
    },
};
const ready = (async () => {
    await import(`${tdoc.versions.chartjs}/chart.umd.min.js`);
    const urls = [...Object.entries(plugins)].map(
        ([n, {path}]) => `${tdoc.versions[n]}/${path}`)
    await Promise.all(urls.map(u => import(u)));
    for (const {register} of Object.values(plugins)) {
        for (const n of register ?? []) Chart.register(globalThis[n]);
    }

    // Set global defaults.
    mergeTo(Chart.defaults, {
        datasets: {
            venn: {layout: {padding: 10}},
        },
        plugins: {
            datalabels: {display: false},
        },
    });
    mergeTo(Chart.defaults, tdoc.dyn.chartjs);
})();  // Background

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

// Call ChartVenn.extractSets() once ChartVenn has been loaded.
export async function extractSets(...args) {
    await ready;
    return ChartVenn.extractSets(...args);
}

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
    await ready;
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

const fnRe = /^([^(]+)(?:\((.*)\))?$/;

// A plugin that sets the bar width from the "w" data attribute.
const barWidth = {
    id: 'bar-width',
    beforeDatasetDraw(chart, args, options) {
        const md = chart.getDatasetMeta(args.index);
        const s = md.xScale;
        for (const [i, bar] of md.data.entries()) {
            const d = chart.data.datasets[args.index].data[i];
            bar.width = s.getPixelForValue(d.x + d.w / 2)
                        - s.getPixelForValue(d.x - d.w / 2);
        }
    },
};

// TODO: Allow taking a distribution instead of a sample
// TODO: Optionally use frequencies instead of counts

templates.histogram = async (el, {
    uniform, custom, options = {}, annotations = {}, sample,
}) => {
    sample = new Sample(sample);

    // Compute the bins.
    const bins = custom !== undefined ? Bins.custom({bins: custom, sample}) :
                 Bins.uniform({...uniform, sample});

    // Compute the distribution and the chart data.
    const dist = sample.distribution(bins);
    const data = dist.map(
        (lo, hi, c) => ({x: (lo + hi) / 2, y: c, w: hi - lo}));

    // Set up annotations.
    for (const [n, ann] of Object.entries(annotations)) {
        const res = [];
        if (typeof ann === 'function') {
            res.push(ann(sample));
        } else {
            const m = n.match(fnRe);
            const name = m ? m[1] : n;
            const fn = await templates.histogram.annotations[name];
            const args = m && m[2] !== undefined ? JSON.parse(`[${m[2]}]`) : [];
            res.push(fn({sample, dist}, ...args), ann);
        }
        annotations[n] = await merge(...res);
    }

    return await chart(el, [{
        type: 'bar',
        data: {datasets: [{data}]},
        plugins: [barWidth],
        options: {
            barThickness: 0,  // Overridden by barWidth
            scales: {
                x: {
                    type: 'linear',
                    min: dist.bins.lowerBound, max: dist.bins.upperBound,
                    offset: false,
                    grid: {offset: false},
                    ticks: {stepSize: dist.bins.minWidth},
                },
                y: {beginAtZero: true, ticks: {stepSize: 1}, grace: '10%'},
            },
            plugins: {
                legend: {display: false},
                tooltip: {
                    callbacks: {
                        title: items => {
                            if (items.length === 0) return "";
                            const it = items[0];
                            const sx = it.chart.scales.x, x = it.parsed.x;
                            const i = dist.bins.find(x);
                            const [lo, hi] = dist.bins.bounds(i);
                            const flo = formatTick(sx, lo);
                            const fhi = formatTick(sx, hi);
                            const c = i == dist.bins.length - 1 ? "]" : "[";
                            return `[${flo}; ${fhi}${c}`;
                        },
                    },
                },
                annotation: {annotations},
            },
        },
    }, {options}]);
};

attrs.line = {
    type: 'line', drawTime: 'afterDatasetsDraw', z: 0,
    borderWidth: 1, borderDash: [6, 4],
    label: {
        display: true, position: 'start', drawTime: 'afterDatasetsDraw', z: 10,
    },
};
attrs.hLine = [attrs.line, {scaleID: 'y'}];
attrs.vLine = [attrs.line, {scaleID: 'x'}];

templates.histogram.annotations = asyncGet({});
templates.histogram.annotations.hLine = ({}, v) => {
    return [attrs.hLine, {value: v, endValue: v, label: {content: `${v}`}}];
};
templates.histogram.annotations.vLine = ({}, v) => {
    return [attrs.vLine, {value: v, endValue: v, label: {content: `${v}`}}];
};
templates.histogram.annotations.min = ({sample}) => {
    const v = sample.min;
    return [attrs.vLine, {value: v, endValue: v, label: {content: "min"}}];
};
templates.histogram.annotations.max = ({sample}) => {
    const v = sample.max;
    return [attrs.vLine, {value: v, endValue: v, label: {content: "max"}}];
};
templates.histogram.annotations.median = ({sample}) => {
    const v = sample.median;
    return [attrs.vLine, {value: v, endValue: v, label: {content: "median"}}];
};
templates.histogram.annotations.quartile = ({sample}, k) => {
    const v = sample.quartile(k);
    return [attrs.vLine, {value: v, endValue: v, label: {content: `Q${k}`}}];
};
templates.histogram.annotations.percentile = ({sample}, p) => {
    const v = sample.percentile(p);
    return [attrs.vLine, {value: v, endValue: v, label: {content: `P${p}`}}];
};
templates.histogram.annotations.quantile = ({sample}, p) => {
    const v = sample.quantile(p);
    return [attrs.vLine,
            {value: v, endValue: v, label: {content: `${p}-quantile`}}];
};
templates.histogram.annotations.mean = ({sample}) => {
    const v = sample.mean;
    return [attrs.vLine, {value: v, endValue: v, label: {content: "mean"}}];
};
templates.histogram.annotations.stdDev = ({sample}, f) => {
    const m = sample.mean, sd = sample.stdDev;
    const v = m + f * sd;
    const sf = f < 0 ? '-' : f > 0 ? '+' : '';
    const af = Math.abs(f);
    return [attrs.vLine, {
        value: v, endValue: v,
        label: {content: `${sf}${af !== 1 ? af : ''}σ`},
    }];
};
// TODO: avgDevFromMean, avgDevFromMedian
