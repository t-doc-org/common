// Copyright 2025 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {
    asyncGet, domLoaded, elmt, instantiateDynTemplate, isPlainObject, isObject,
    mergeAttrs, on, onSet, qs, qsa, resolveDyn,
} from './core.js';
import {Bins, Distribution, Sample} from './math.js';

// TODO: Add plugins from page metadata

// Allow disabling plugins by default by setting their options to false in page
// metadata. This doesn't work in Chart.defaults, but it does in per-chart
// options, so we mix it in there.
const disabledPlugins = {options: {plugins: {}}};
for (const [k, v] of Object.entries(tdoc.dyn.chartjs.plugins)) {
    if (v !== false) continue;
    disabledPlugins.options.plugins[k] = v;
    delete tdoc.dyn.chartjs.plugins[k];
}

// Load Chart.js and plugins.
const plugins = {
    'chartjs-chart-boxplot': {path: 'index.umd.min.js'},
    'chartjs-chart-error-bars': {path: 'index.umd.min.js'},
    'chartjs-chart-graph': {path: 'index.umd.min.js'},
    'chartjs-chart-venn': {path: 'index.umd.min.js'},
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
})();

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
    // TODO: Add support for annotations
    config = await merge(disabledPlugins, config);
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

// Annotation container.
export const annotations = asyncGet({})

const annNameRe = /^([^_]*)(?:_.*)?$/;

// Render annotations into chart config options.
async function renderAnnotations(anns, data) {
    if (anns?.[Symbol.iterator] === undefined) anns = [anns];
    const res = {};
    let id = 0;
    for (const a of anns) {
        if (typeof a === 'function') {
            res[`tdoc$ann$${id++}`] = a(data);
            continue;
        }
        const options = a.options;
        for (const [k, args] of Object.entries(a)) {
            if (k === 'options') continue;
            const fn = await annotations[k.match(annNameRe)[1]];
            res[`tdoc$ann$${id++}`] = await merge(fn(args, data), a.options, args.options);
        }
    }
    return res;
}

attrs.line = {
    type: 'line', drawTime: 'afterDatasetsDraw', z: 0,
    borderWidth: 1, borderDash: [6, 4],
    label: {
        display: true, position: 'start', drawTime: 'afterDatasetsDraw', z: 10,
    },
};
attrs.hLine = [attrs.line, {scaleID: 'y'}];
attrs.vLine = [attrs.line, {scaleID: 'x'}];

annotations.hLine = ({y}) => {
    return [attrs.hLine, {value: y, endValue: y, label: {content: `${y}`}}];
};
annotations.vLine = ({x}) => {
    return [attrs.vLine, {value: x, endValue: x, label: {content: `${x}`}}];
};
annotations.count = ({f = 1, dist = false}, {sample, distribution}) => {
    const ds = sample && !dist ? sample : distribution;
    const v = f * ds.count;
    const p = f === -1 ? '-' : f === 1 ? '' : `${f}*`;
    return [attrs.hLine,
            {value: v, endValue: v, label: {content: `${p}count`}}];
};
annotations.min = ({dist = false}, {sample, distribution}) => {
    const ds = sample && !dist ? sample : distribution;
    const v = ds.min;
    return [attrs.vLine, {value: v, endValue: v, label: {content: "min"}}];
};
annotations.max = ({dist = false}, {sample, distribution}) => {
    const ds = sample && !dist ? sample : distribution;
    const v = ds.max;
    return [attrs.vLine, {value: v, endValue: v, label: {content: "max"}}];
};
annotations.median = ({dist = false}, {sample, distribution}) => {
    const ds = sample && !dist ? sample : distribution;
    const v = ds.median;
    return [attrs.vLine, {value: v, endValue: v, label: {content: "median"}}];
};
annotations.quartile = ({k, dist = false}, {sample, distribution}) => {
    const ds = sample && !dist ? sample : distribution;
    const v = ds.quartile(k);
    return [attrs.vLine, {value: v, endValue: v, label: {content: `Q${k}`}}];
};
annotations.percentile = ({p, dist = false}, {sample, distribution}) => {
    const ds = sample && !dist ? sample : distribution;
    const v = ds.percentile(p);
    return [attrs.vLine, {value: v, endValue: v, label: {content: `P${p}`}}];
};
annotations.quantile = ({p, dist = false}, {sample, distribution}) => {
    const ds = sample && !dist ? sample : distribution;
    const v = ds.quantile(p);
    return [attrs.vLine,
            {value: v, endValue: v, label: {content: `${p}-quantile`}}];
};
annotations.mean = ({dist = false}, {sample, distribution}) => {
    const ds = sample && !dist ? sample : distribution;
    const v = ds.mean;
    return [attrs.vLine, {value: v, endValue: v, label: {content: "mean"}}];
};
annotations.stdDev = ({f, dist = false}, {sample, distribution}) => {
    const ds = sample && !dist ? sample : distribution;
    const v = ds.mean + f * ds.stdDev;
    const sf = f < 0 ? '-' : f > 0 ? '+' : '';
    const af = Math.abs(f);
    return [attrs.vLine, {
        value: v, endValue: v,
        label: {content: `${sf}${af !== 1 ? af : ''}σ`},
    }];
};
annotations.avgDev = ({f, from = 'median', dist = false},
                      {sample, distribution}) => {
    const ds = sample && !dist ? sample : distribution;
    const m = from === 'median' ? ds.median :
              from === 'mean' ? ds.mean : undefined;
    if (m === undefined) {
        throw new Error(`{chartjs} avgDev: unsupported 'from': ${from}`);
    }
    const v = m + f * ds.avgDev(m);
    const sf = f < 0 ? '-' : f > 0 ? '+' : '';
    const af = Math.abs(f);
    return [attrs.vLine, {
        value: v, endValue: v,
        label: {content: `${sf}${af !== 1 ? af : ''}AAD`},
    }];
};

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

templates.histogram = async (el, {
    sample, uniform, custom, distribution, normalize = false, options = {},
    annotations = [],
}) => {
    let bins;
    if (sample !== undefined) {
        sample = new Sample(sample);
        bins = custom !== undefined ? Bins.custom({bins: custom, sample}) :
                                      Bins.uniform({...uniform, sample});
        distribution = sample.distribution(bins);
    } else if (distribution !== undefined) {
        bins = Bins.custom({bins: distribution.map(it => it[0])});
        distribution = Distribution.from(distribution);
    } else {
        throw new Error(
            "{chartjs} histogram: Either sample or distribution is required");
    }
    if (normalize) distribution.normalize();
    const data = distribution.map(
        (lo, hi, c) => ({x: (lo + hi) / 2, y: c, w: hi - lo}));

    const anns = await renderAnnotations(annotations, {sample, distribution});
    return await chart(el, [{
        type: 'bar',
        data: {datasets: [{data}]},
        plugins: [barWidth],
        options: {
            barThickness: 0,  // Overridden by barWidth
            scales: {
                x: {
                    type: 'linear',
                    min: distribution.bins.lowerBound, max: distribution.bins.upperBound,
                    offset: false,
                    grid: {offset: false},
                    ticks: {stepSize: distribution.bins.minWidth},
                },
                y: {
                    beginAtZero: true, grace: '10%',
                    ticks: {stepSize: normalize ? undefined : 1},
                },
            },
            plugins: {
                legend: {display: false},
                tooltip: {
                    callbacks: {
                        title: items => {
                            if (items.length === 0) return "";
                            const it = items[0];
                            const sx = it.chart.scales.x, x = it.parsed.x;
                            const i = distribution.bins.find(x);
                            const [lo, hi] = distribution.bins.bounds(i);
                            const flo = formatTick(sx, lo);
                            const fhi = formatTick(sx, hi);
                            const c = i == distribution.bins.length - 1 ? "]"
                                                                        : "[";
                            return `[${flo}; ${fhi}${c}`;
                        },
                    },
                },
                annotation: {annotations: anns},
            },
        },
    }, {options}]);
};

templates['cumulative-distribution-function'] = async (el, {
    sample, min, max, step, normalize = false, options = {}, annotations = [],
}) => {
    sample = new Sample(sample);
    const cdf = sample.cumulativeDistributionFunction(normalize);
    const data = [{x: -Number.MAX_VALUE, y: 0}];
    for (let [x, y] of cdf) {
        data.push({x, y: data[data.length - 1].y}, {}, {x, y});
    }
    data.push({x: Number.MAX_VALUE, y: data[data.length - 1].y});

    const anns = await renderAnnotations(annotations, {sample});
    return await chart(el, [{
        type: 'scatter',
        data: {datasets: [{data}]},
        options: {
            showLine: true,
            scales: {
                x: {
                    min: min ?? sample.min - 0.05 * sample.range,
                    max: max ?? sample.max + 0.05 * sample.range,
                    ticks: {stepSize: step, includeBounds: false},
                },
                y: {
                    max: 1.1 * cdf[cdf.length - 1][1],
                    beginAtZero: true,
                    ticks: {includeBounds: false},
                },
            },
            pointRadius: 3, pointBorderWidth: 1,
            pointBackgroundColor: ctx => ctx.index % 3 === 0 ?
                                         ctx.chart.options.pointBorderColor :
                                         '#fff',
            plugins: {
                legend: {display: false},
                annotation: {annotations: anns},
            },
        },
    }, {options}]);
};

