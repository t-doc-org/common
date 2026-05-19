% Copyright 2026 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Charts

## Chart.js

`````{rst:directive} .. chartjs:: [template:]name
This directive creates a chart based on [Chart.js](https://www.chartjs.org/).

- [Chart.js documentation](https://www.chartjs.org/docs/latest/)
- [Chart types](https://www.chartjs.org/docs/latest/charts/area.html)
- [Chart.js examples](https://www.chartjs.org/docs/latest/samples/)

The charts are constructed in JavaScript, by importing the {js:mod}`chart`
module and calling {js:func}`~chart.chart` for each {rst:dir}`chartjs`
directive, referencing it by name.

````{code-block} html
```{chartjs} v-bar
```

<script type="module">
const [core, {chart}] = await tdoc.imports('tdoc/core.js', 'tdoc/chart.js');

chart('v-bar', {
  type: 'bar',
  data: {
    labels: ['January', 'February', 'March', 'April', 'May', 'June', 'July'],
    datasets: [{
      label: '',
      data: [65, 59, 80, 81, 56, 55, 40],
      borderWidth: 1,
      borderColor: core.palette,
      backgroundColor: core.palette.map(c => c.with({a: 0.2})),
    }],
  },
  options: {scales: {y: {beginAtZero: true}}},
});
</script>
````

Alternatively, templates can be instantiated by prefixing the template name with
`template:` and passing arguments in the directive content.

````{code-block}
```{chartjs} template:json
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

#### `json`

This template renders a chart with a static JSON config. The chart configuration
is provided in the directive content. Some attributes are special-cased for more
flexibility.

- Setting an attribute named `color` or ending with `Color` to a string starting
  with `@` looks up a color by name in
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
construct, or the wrapper DOM element that should contain the chart.
:arg !Object config: The chart configuration.
:returns: A `Promise` that resolves to the  created `Chart` instance.
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
`````
