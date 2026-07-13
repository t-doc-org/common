% Copyright 2026 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Charts

## Chart.js

`````{rst:directive} {chartjs} renderer
This directive creates a chart based on [Chart.js](https://www.chartjs.org/).

- Chart.js: [documentation](https://www.chartjs.org/docs/latest/),
  [chart types](https://www.chartjs.org/docs/latest/charts/area.html),
  [examples](https://www.chartjs.org/docs/latest/samples/)
- Available plugins:
  - [chartjs-chart-boxplot](https://www.sgratzl.com/chartjs-chart-boxplot/)
  - [chartjs-chart-error-bars](https://www.sgratzl.com/chartjs-chart-error-bars/)
  - [chartjs-chart-graph](https://www.sgratzl.com/chartjs-chart-graph/)
  - [chartjs-chart-venn](https://upset.js.org/chartjs-chart-venn/)
    ([data structure](https://github.com/upsetjs/chartjs-chart-venn#venn-diagram))
  - [chartjs-plugin-annotation](https://www.chartjs.org/chartjs-plugin-annotation/master/)
  - [chartjs-plugin-datalabels](https://chartjs-plugin-datalabels.netlify.app/)
  - [chartjs-plugin-deferred](https://chartjs-plugin-deferred.netlify.app/)

[Pre-defined renderers](#renderers) can be used by specifying their name as a
directive argument, and providing arguments in the directive content as a
[JSON5](https://spec.json5.org/) object (without enclosing `{}`).

````{code-block}
```{chartjs} chart
type: 'bar',
data: {
  labels: ['Monday', 'Tuesday', 'Wednesday'],
  datasets: [{
    label: "Option A",
    data: [7, 11, 3],
    borderWidth: 1, borderColor: '#36a2eb', hoverBorderColor: '#36a2eb',
    backgroundColor: '#36a2eb33',
  }],
},
options: {
  scales: {y: {beginAtZero: true}},
  plugins: {legend: {display: false}},
},
```
````

Custom renderers can be defined in JavaScript, by importing the {js:mod}`chart`
module, adding rendering functions to {js:data}`~chart.render`, and calling {js:func}`~chart.chart` (or one of the other renderers) in the rendering
function.

````{code-block} html
```{chartjs} vBar
```

<script type="module">
const {chart, render} = await tdoc.import('tdoc/chart.js');

const colors = ['#36a2eb', '#ff6384', '#4bc0c0', '#ff9f40', '#9966ff',
                '#ffcd56', '#c9cbcf'];
render.vBar = el => {
  return chart(el, {
    type: 'bar',
    data: {
      labels: ['January', 'February', 'March', 'April', 'May', 'June', 'July'],
      datasets: [{data: [65, 59, 80, 81, 56, 55, 40]}],
    },
    options: {
      borderWidth: 1, borderColor: colors, hoverBorderColor: colors,
      backgroundColor: colors.map(c => `${c}33`),
      scales: {y: {beginAtZero: true}},
    },
  });
};
</script>
````

Defaults can be set via the `chartjs` {rst:dir}`metadata`, and are merged into
[`Chart.defaults`](https://www.chartjs.org/docs/latest/configuration/#global-configuration).

{rst:dir}`chartjs` directives generate `<tdoc-dyn type="chartjs">`{l=html}
elements, and their {js:attr}`~core.DynElement.controller` property is the
[`Chart`](https://www.chartjs.org/docs/latest/api/classes/Chart.html) instance
returned by the renderer.

{.rubric}
Options

```{rst:directive:option} class: name [name...]
:type: IDs
A space-separated list of CSS classes to add to the chart container.
```

```{rst:directive:option} style: property: value; [property: value; ...]
CSS styles to apply to the chart container.
```
`````

### Renderers

This section describes the pre-defined renderers. Custom renderers can be
added in JavaScript via {js:data}`~chart.render`.

#### `chart`

This renderer displays a chart from a static JSON config. The directive content
is passed directly to {js:func}`~chart.chart`, after extracting
[dynamic annotation specifications](#annotations) from the `annotations` key.
The whole config is provided as data to annotation generators.

````{code-block}
```{chartjs} chart
type: 'bar',
data: {
  labels: ['Monday', 'Tuesday', 'Wednesday'],
  datasets: [{
    label: "Option A",
    data: [7, 11, 3],
    borderWidth: 1, borderColor: '#36a2eb', hoverBorderColor: '#36a2eb',
    backgroundColor: '#36a2eb33',
  }],
},
options: {
  scales: {y: {beginAtZero: true}},
  plugins: {legend: {display: false}},
},
annotations: {hLine: {y: 5, label: ''}}
```
````

#### `venn`

This renderer works the same as [`chart`](#chart), but it sets some defaults to
simplify the creation of Venn diagrams.

- The chart type is set to `venn`.
- The `background` [plugin](#plugins) is enabled and configured to set a solid
  white background.
- A border is set on the containing element, unless the `no-border` class is
  present.

#### `histogram`

This renderer displays the [histogram](https://en.wikipedia.org/wiki/Histogram)
of a sample or a distribution.

- `sample`: The statistical sample for which to plot the histogram, an array of
  values or `[value, count]` pairs.
- `distribution`: The distribution for which to plot the histogram, an array of
  `[x, count]` pairs where `x` is the lower bound of the bin, and the last
  element must have a zero (or `undefined`) count.
- `uniform`: Use bins of uniform width (default) to compute the distribution
  from the sample. The keys define how the bins are computed:
  - `count`: The number of bins.
  - `max`: The largest value that needs to be handled. When unset, this is
    derived from the sample.
  - `min`: The lower limit of the first bin. When unset, this is derived from
    the sample.
  - `origin` (default: `0`): The origin of the binning when `width` is set and
    `min` isn't.
  - `width`: The width of the bins. When unset, this is derived from `count` and
    the sample.
- `custom`: Use custom bins to compute the distribution from the sample. The
  value is an array of bin boundaries.
- `normalize` (default: `false`): When true, represent frequencies instead of
  counts.
- `options`: Options to merge into the `options` field of the chart.
- `annotations`: An object or array of objects containing
  [dynamic annotation specifications](#annotations).

````{code-block}
```{chartjs} histogram
uniform: {min: 0, max: 24, width: 2},
sample: [
  10, 9, 11, 10, 9, 8, 6, 9, 10, 10, 7, 10, 9, 13, 15, 11, 8, 13, 7, 7,
  9, 7, 10, 12, 9, 10, 12, 15, 10, 8, 9, 11, 12, 9, 6, 17, 8, 13, 11, 16,
],
options: {
  borderWidth: 0.5, borderColor: '#36a2eb', backgroundColor: '#36a2eb33',
  scales: {y: {title: {display: true, text: "Occurrences"}}}
},
annotations: {median: {}},
```
````

#### `densityFunction`

This renderer displays the
[density function](https://en.wikipedia.org/wiki/Probability_mass_function)
 of a sample.

- `sample`: The statistical sample for which to plot the density function, an
  array of values or `[value, count]` pairs.
- `min`: The minimum value to represent on the horizontal axis.
- `max`: The maximum value to represent on the horizontal axis.
- `step`: The smallest tick interval to represent on the horizontal axis.
- `width` (default: `5`): The width of the bars in pixels.
- `normalize` (default: `false`): When true, represent frequencies instead of
  counts.
- `options`: Options to merge into the `options` field of the chart.
- `annotations`: An object or array of objects containing
  [dynamic annotation specifications](#annotations).

````{code-block}
```{chartjs} densityFunction
min: 0, max: 24, step: 2,
sample: [
  [6, 2], [7, 4], [8, 4], [9, 8], [10, 8], [11, 4], [12, 3], [13, 3], [15, 2],
  [16, 1], [17, 1],
],
options: {
  backgroundColor: '#36a2eb',
  scales: {y: {title: {display: true, text: "Occurrences"}}},
},
annotations: {median: {}},
```
````

#### `cumulativeDistributionFunction`

This renderer displays the
[cumulative distribution function](https://en.wikipedia.org/wiki/Cumulative_distribution_function)
of a sample or a distribution.

- `sample`: The statistical sample for which to plot the CDF, an array of
  values or `[value, count]` pairs.
- `distribution`: The distribution for which to plot the CDF, an array of
  `[x, count]` pairs where `x` is the lower bound of the bin, and the last
  element must have a zero (or `undefined`) count.
- `min`: The minimum value to represent on the horizontal axis.
- `max`: The maximum value to represent on the horizontal axis.
- `step`: The smallest tick interval to represent on the horizontal axis.
- `normalize` (default: `true`): When true, represent cumulative frequencies
  instead of counts.
- `options`: Options to merge into the `options` field of the chart.
- `annotations`: An object or array of objects containing
  [dynamic annotation specifications](#annotations).

````{code-block}
```{chartjs} cumulativeDistributionFunction
min: 0, max: 24, step: 2,
sample: [
  [2, 1], [4, 3], [6, 7], [8, 8], [10, 2], [12, 1], [14, 6], [16, 9], [18, 8],
  [20, 5],
],
options: {
  borderColor: '#36a2eb',
  scales: {y: {title: {display: true, text: "Cumulative frequency"}}},
},
annotations: {median: {}},
```
````

### Annotations

Annotations are additional elements added to a graph by
[chartjs-plugin-annotation](https://www.chartjs.org/chartjs-plugin-annotation/master/). While static annotations can be added directly via
`options.plugins.annotation.annotations` and don't need special support,
**dynamic annotations** are computed from chart data and are implemented via
{js:data}`~chart.annotations`.

An **annotation specification** is an object where each key specifies an
annotation generator, and the value specifies the arguments to the generator, as
an object. Moreover, the `options` key provides additional attributes to merge
into the generated `options.plugins.annotation.annotations` entries. It can be
set either in the specification or as an annotation argument.

For example, the following annotation specification adds vertical lines for the
median, minimum, maximum, 1st and 3rd quartile and 5th and 95th percentile of a
sample or distribution provided by a renderer. The median is colored magenta,
while the others are colored red.

```{code-block} js
{
  median: {options: {borderColor: '#9966ff'}},
  min: {}, max: {}, quartile: {k: [1, 3]}, percentile: {p: [5, 95]},
  options: {borderColor: '#ff6384'},
}
```

The following annotation generators are pre-defined:

{.vsep-2}
- **Generic annotations:**
  - `hLine: {y, label}`: A horizontal line with the given text label. `y` can
    be an array to add multiple lines.
  - `vLine: {x, label}`: A vertical line with the given text label. `x` can
    be an array to add multiple lines.

- **Statistical annotations:** These annotations get either a sample or a
  distribution from the renderer, as a `{sample, distribution}` object. If a
  renderer provides both a sample and a distribution, the `dist` argument
  specifies which should be used (`false` &rarr; sample, `true` &rarr;
  distribution).
  - `count: {f = 1, dist = false, label}`: A horizontal line at `f` times the
    sample or distribution count. `f` can be an array to add multiple lines.
  - `min: {dist = false, label}`: A vertical line at the minimum of the sample
    or distribution.
  - `max: {dist = false, label}`: A vertical line at the maximum of the sample
    or distribution.
  - `median: {dist = false, label}`: A vertical line at the median of the sample
    or distribution.
  - `quartile: {k, dist = false, label}`: A vertical line at the `k`th quartile
    of the sample or distribution. `k` can be an array to add multiple
    quartiles.
  - `percentile: {p, dist = false, label}`: A vertical line at the `p`th
    percentile of the sample or distribution. `p` can be an array to add
    multiple percentiles.
  - `quantile: {p, dist = false, label}`: A vertical line at the `p`th
    quantile of the sample or distribution. `p` can be an array to add multiple
    quantiles.
  - `mean: {dist = false, label}`: A vertical line at the mean of the sample or
    distribution.
  - `stdDev: {f, population = false, dist = false, label}`: A vertical line at
    `f` times the standard deviation from the mean. `f` can be an array to add
    multiple lines. When `population` is true, use the population deviation
    instead of the sample deviation.
  - `avgDev: {f, from = 'median', dist = false, label}`: A vertical line at
    `f` times the average deviation from the median (`from = 'median'`) or mean
    (`from = 'mean'`). `f` can be an array to add multiple lines.
  - `mode: {k, dist = true, label}`: A vertical line at the `k`th mode of the
    sample or distribution. `k` can be an array to add multiple lines. If `k` is
    missing, a line is added for each mode.

**Custom dynamic annotations** can be defined by setting functions as attributes
of {js:data}`~chart.annotations`. Annotation generator functions receive the
arguments from the annotation specification as their first argument, and the
data from the renderer as their second argument, and return an array of
annotation values to be added to `options.plugins.annotation.annotations`.

````{code-block} html
```{chartjs} chart
type: 'bar',
data: {
  labels: ['Monday', 'Tuesday', 'Wednesday'],
  datasets: [{data: [7, 11, 3]}],
},
annotations: {valueLabels: {label: 'Value: '}}
```

<script type="module">
const {annotations} = await tdoc.import('tdoc/chart.js');

annotations.valueLabels = ({label}, config) => {
  return config.data.datasets[0].data.map((v, i) => ({
    type: 'label', content: `${label ?? ''}${v}`,
    xValue: i, yValue: v, yAdjust: -15,
  }));
};
</script>
````

### Plugins

Chart.js [plugins](https://www.chartjs.org/docs/latest/developers/plugins.html)
are implemented in JavaScript and managed via {js:data}`~chart.plugins`. Plugins
can be referenced by name by using strings as elements of the `plugins`
attribute of the chart config.

The following plugins are pre-defined:

- `background`: Paint the chart background. The following options are supported:
  - `color`: Fill the background with the given solid color.
  - `gradient`: Fill the background with a gradient.
    - `type`: The type of gradient; one of `linear`, `conic` or `radial`.
    - `from`, `to`: The endpoints of the gradient. For `linear` gradients, the
      endpoints are `[x, y]` tuples, where `x` is a fraction of the chart width
      and `y` a fraction of the chart height. For `radial` gradients, the
      endpoints are `[x, y, r]` tuples, where `r` is a fraction of the minimum
      between the chart width and height.
    - `stops`: The gradient stops, a list of `[offset, color]` tuples, where the
      offset is between 0 and 1.

**Custom plugins** can be registered by assigning them as attributes of
{js:data}`~chart.plugins`. The plugin `id` is automatically set to the name of
the attribute, and that's also the name to use for the options of the plugin.

````{code-block} html
```{chartjs} chart
type: 'bar',
data: {
  labels: ['Monday', 'Tuesday', 'Wednesday'],
  datasets: [{data: [7, 11, 3]}],
},
plugins: ['backgroundGradient'],
options: {
  plugins: {
    backgroundGradient: {
      from: [0, 0], to: [0, 1], stops: [[0, '#fee'], [1, '#efe']],
    },
  },
},
```

<script type="module">
const {plugins} = await tdoc.import('tdoc/chart.js');

plugins.backgroundGradient = {
    beforeDraw(chart, args, options) {
        if (options.stops === undefined) return;
        const {ctx} = chart;
        ctx.save();
        ctx.globalCompositeOperation = 'destination-over';
        const grad = ctx.createLinearGradient(
          options.from[0] * chart.width, options.from[1] * chart.height,
          options.to[0] * chart.width, options.to[1] * chart.height);
        for (const [p, c] of options.stops) grad.addColorStop(p, c);
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, chart.width, chart.height);
        ctx.restore();
    },
};
</script>
````

### `tdoc/chart.js`

```{js:module} chart
This module
([source](https://github.com/t-doc-org/common/blob/main/tdoc/common/static/tdoc/chart.js))
provides functionality related to {rst:dir}`chartjs` directives.
```

{.rubric}
Module globals

`````{js:data} render
An object containing named rendering functions. In addition to the
[pre-defined renderers](#renderers) described above, custom renderers can be
added by setting functions as object attributes. Rendering functions receive the
wrapper DOM element as their first argument, and the content of the directive as
a JSON object as their second argument.

````{code-block} html
```{chartjs} randomBars
count: 3, min: 10, max: 50,
```
```{chartjs} randomBars
count: 5, min: 100, max: 500,
```

<script type="module">
const [core, {chart, render}] = await tdoc.import('tdoc/core.js', 'tdoc/chart.js');

render.randomBars = (el, {count, min, max}) => {
  const labels = [], data = [];
  for (let i = 0; i < count; ++i) {
    labels.push(`L${i + 1}`);
    data.push(core.randomInt(min, max));
  }
  return chart(el, {
    type: 'bar',
    data: {
      labels,
      datasets: [{data}],
    },
    options: {
      borderWidth: 1, borderColor: '#36a2eb', hoverBorderColor: '#36a2eb',
      backgroundColor: '#36a2eb33',
      scales: {y: {beginAtZero: true}},
      plugins: {legend: {display: false}},
    },
  })
};
</script>
````
`````

```{js:data} attrs
An object containing named attribute sets. Custom sets can be defined by
assigning to object attributes.
```

```{js:data} annotations
An object containing [annotation generators](#annotations). Custom annotations
can be defined by assigning to object attributes.
```

```{js:data} plugins
An object containing [plugins](#plugins). Custom plugins can be defined by
assigning to object attributes.
```

{.rubric}
Functions

```{js:function} chart(el, config)
Render the content of a {rst:dir}`chartjs` directive.

:arg !HTMLElement el: The wrapper DOM element that will contain the chart.
:arg !Object|Array config: The chart configuration, passed to the `Chart`
constructor. If an `Array` of configs is provided, they are merged.
:returns: A `Promise` that resolves to the created `Chart` instance.
```
