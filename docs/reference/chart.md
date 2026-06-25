% Copyright 2026 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Charts

## Chart.js

`````{rst:directive} .. chartjs:: renderer
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
is passed directly to {js:func}`~chart.chart`.

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
```
````

### `tdoc/chart.js`

```{js:module} chart
This module
([source](https://github.com/t-doc-org/common/blob/main/tdoc/common/static/tdoc/chart.js))
provides functionality related to {rst:dir}`chartjs` directives.
```

```{js:function} chart(el, config)
Render the content of a {rst:dir}`chartjs` directive.

:arg !HTMLElement el: The wrapper DOM element that will contain the chart.
:arg !Object|Array config: The chart configuration, passed to the `Chart`
constructor. If an `Array` of configs is provided, they are merged.
:returns: A `Promise` that resolves to the created `Chart` instance.
```

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

```{js:data} attrs
An object containing named attribute sets. Custom sets can be defined by
assigning to object attributes.
```
`````
