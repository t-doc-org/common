% Copyright 2026 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Charts

## Chart.js

`````{rst:directive} .. chartjs:: [template:]name
This directive creates a chart based on [Chart.js](https://www.chartjs.org/).

- [Chart.js documentation](https://www.chartjs.org/docs/latest/)
- [Chart types](https://www.chartjs.org/docs/latest/charts/area.html)
- [Chart.js examples](https://www.chartjs.org/docs/latest/samples/)

The charts are rendered in JavaScript, by importing the {js:mod}`chart`
module and calling {js:func}`~chart.chart` (or one of the other renderers) for
each {rst:dir}`chartjs` directive, referencing them by name. Defaults can be set
via the `chartjs:` {rst:dir}`metadata`.

````{code-block} html
```{chartjs} v-bar
```

<script type="module">
const [core, {chart}] = await tdoc.imports('tdoc/core.js', 'tdoc/chart.js');

chart('v-bar', {
  type: 'bar',
  data: {
    labels: ['January', 'February', 'March', 'April', 'May', 'June', 'July'],
    datasets: [{data: [65, 59, 80, 81, 56, 55, 40]}],
  },
  options: {
    borderWidth: 1, borderColor: core.palette, hoverBorderColor: core.palette,
    backgroundColor: core.palette.map(c => c.with({a: 0.2})),
    scales: {y: {beginAtZero: true}},
  },
});
</script>
````

Alternatively, templates can be instantiated by prefixing the template name with
`template:` and passing arguments in the directive content.

````{code-block}
```{chartjs} template:chart
type: 'bar',
data: {
  labels: ['Monday', 'Tuesday', 'Wednesday'],
  datasets: [{
    label: "Option A",
    data: [7, 11, 3],
    borderWidth: 1, borderColor: '@blue', hoverBorderColor: '@blue',
    backgroundColor: '@blue/0.2',
  }],
},
options: {
  scales: {y: {beginAtZero: true}},
  plugins: {legend: {display: false}},
},
```
````

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

### Templates

Templates are instantiated by specifying the template name prefixed by
`template:` as the directive argument. The template arguments are provided in
the directive content as a [JSON5](https://spec.json5.org/) array.

The predefined templates are described below. Custom templates can be created in
JavaScript via {js:func}`~chart.template`.

#### `chart`

This template renders a chart from a static JSON config. Rendering is performed
with {js:func}`~chart.chart`.

````{code-block}
```{chartjs} template:chart
type: 'bar',
data: {
  labels: ['Monday', 'Tuesday', 'Wednesday'],
  datasets: [{
    label: "Option A",
    data: [7, 11, 3],
    borderWidth: 1, borderColor: '@blue', hoverBorderColor: '@blue',
    backgroundColor: '@blue/0.2',
  }],
},
options: {
  scales: {y: {beginAtZero: true}},
  plugins: {legend: {display: false}},
},
```
````

#### `histogram`

This template renders a histogram from an array of samples, using uniform
binning. Rendering is performed with {js:func}`~chart.histogram`.

- `bins`: The definition of the histogram bins.
  - `count`: The number of bins.
  - `max`: The largest sample value that needs to be handled. When unset, this
    is derived from the samples.
  - `min`: The lower limit of the first bin. When unset, this is derived from
    the samples.
  - `origin` (default: `0`): The origin of the binning when `width` is set and
    `min` isn't.
  - `width`: The width of the bins. When unset, this is derived from `count` and
    the samples.
- `options`: A map of options to merge into the `options` field of the chart.
- `samples`: The array of samples.

````{code-block}
```{chartjs} template:histogram
bins: {min: 0, width: 2, count: 12},
options: {
  scales: {
    x: {title: {display: true, text: "Hours"}},
    y: {title: {display: true, text: "Visitors"}},
  }
},
samples: [
  10, 9, 11, 10, 9, 8, 6, 9, 10, 10, 7, 10, 9, 13, 15, 11, 8, 13, 7, 7,
  9, 7, 10, 12, 9, 10, 12, 15, 10, 8, 9, 11, 12, 9, 6, 17, 8, 13, 11, 16,
],
```
````

### Expansion

Certain chart config attributes are expanded before rendering to make static
configs more flexible.

- Attributes named `color` or ending with `Color`, with a value starting with
  `@`, are expanded by looking up the color by name in
  [`core.colors`](https://github.com/t-doc-org/common/blob/main/tdoc/common/static/tdoc/core.js).
  The color name can optionally be followed by `/` and an alpha value in the
  range $\left[0; 1\right]$.

  - `"@blue"` &rarr; `"rgb(54, 162, 235)"`
  - `"@red"` &rarr; `"rgb(255, 99, 132)"`
  - `"@blue/0.2"` &rarr; `"rgba(54, 162, 235, 0.2)"`

### `tdoc/chart.js`

`````{js:module} chart
This module
([source](https://github.com/t-doc-org/common/blob/main/tdoc/common/static/tdoc/chart.js))
provides functionality related to {rst:dir}`chartjs` directives.
`````

```{js:function} chart(el, config)
Render the content of a {rst:dir}`chartjs` directive.

:arg !string|HTMLElement el: The name of the {rst:dir}`chartjs` directive to
render, or the wrapper DOM element that should contain the chart.
:arg !Object config: The chart configuration.
:returns: A `Promise` that resolves to the created `Chart` instance.
```

`````{js:function} template(name, fn)
Render all {rst:dir}`chartjs` directives referencing the template with the given
name.

:arg !string name: The name of the template.
:arg !function fn: A function to be called for each {rst:dir}`chartjs` directive
to render. The function receives the wrapper DOM element as its first argument,
and the content of the directive as a JSON object as its second argument.

````{code-block} html
```{chartjs} template:random-bars
count: 3, min: 10, max: 50,
```
```{chartjs} template:random-bars
count: 5, min: 100, max: 500,
```

<script type="module">
const [core, {template}] = await tdoc.imports('tdoc/core.js', 'tdoc/chart.js');
template('random-bars', (el, {count, min, max}) => {
  const labels = [], data = [];
  for (let i = 0; i < count; ++i) {
    labels.push(`L${i + 1}`);
    data.push(core.randomInt(min, max));
  }
  chart(el, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        data, borderWidth: 1, borderColor: core.colors.blue,
        backgroundColor: core.colors.blue.with({a: 0.2}),
        hoverBorderColor: core.colors.blue,
      }],
    },
    options: {
      scales: {y: {beginAtZero: true}},
      plugins: {legend: {display: false}},
    },
  })
});
</script>
````

```{js:function} histogram(el, args)
Render a histogram in a {rst:dir}`chartjs` directive.

:arg !string|HTMLElement el: The name of the {rst:dir}`chartjs` directive to
render, or the wrapper DOM element that should contain the chart.
:arg !Object args: The histogram arguments, as described for the
[`histogram`](#histogram) template.
:returns: A `Promise` that resolves to the created `Chart` instance.
```
`````
