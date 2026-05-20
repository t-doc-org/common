% Copyright 2026 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Charts

```{metadata}
chartjs:
  plugins:
    legend:
      display: false
```

## Chart.js

This section renders charts using {rst:dir}`chartjs` directives.

### Bar charts

([Documentation](https://www.chartjs.org/docs/latest/charts/bar.html))

```{chartjs} v-bar
```

```{chartjs} h-bar
```

### Bubble charts

([Documentation](https://www.chartjs.org/docs/latest/charts/bubble.html))

```{chartjs} bubble
```

### Pie & doughnut charts

([Documentation](https://www.chartjs.org/docs/latest/charts/doughnut.html))

```{chartjs} pie
:style: width: 70%;
```

```{chartjs} doughnut
:style: width: 70%;
```

### Template: `json`

```{chartjs} template:json
type: 'bar',
data: {
  labels: ['Monday', 'Tuesday', 'Wednesday'],
  datasets: [{
    label: "Option A",
    data: [7, 11, 3],
    borderWidth: 1, borderColor: '@blue', hoverBorderColor: '@blue',
    backgroundColor: '@blue/0.2',
  }, {
    label: "Option B",
    data: [6, 9, 2],
    borderWidth: 1, borderColor: '@red', hoverBorderColor: '@red',
    backgroundColor: '@red/0.2',
  }],
},
options: {
  scales: {y: {beginAtZero: true}},
},
```

### Template: `histogram`

```{chartjs} template:histogram
bins: {min: 0, max: 23, width: 2},
options: {
  scales: {
    x: {title: {display: true, text: "Hours"}},
    y: {title: {display: true, text: "Visitors"}},
  }
},
samples: [
  10, 9, 11, 10, 9, 8, 6, 9, 10, 10, 7, 10, 9, 13, 15, 11, 8, 13, 7, 7,
  9, 7, 10, 12, 9, 10, 12, 15, 10, 8, 9, 11, 12, 9, 6, 17, 8, 13, 11, 16,
  13, 11, 8, 11, 14, 10, 10, 10, 9, 11, 14, 11, 7, 12, 8, 9, 15, 9, 10, 11,
  6, 16, 10, 8, 13, 9, 10, 12, 10, 10, 10, 12, 9, 13, 17, 12, 9, 14, 10, 13,
  15, 10, 12, 10, 14, 10, 7, 13, 10, 8, 6, 8, 9, 8, 11, 17, 8, 9, 9, 14,
  6, 8, 8, 9, 9, 10, 5, 11, 9, 10, 12, 8, 8, 8, 11, 3, 6, 20, 5, 14,
  15, 6, 9, 13, 11, 8, 14, 8, 14, 14, 8, 8, 16, 7, 8, 10, 12, 12, 10, 13,
  9, 11, 12, 7, 7, 11, 12, 9, 8, 14, 6, 12, 9, 9, 15, 7, 12, 11, 11, 13,
  6, 10, 8, 15, 8, 12, 5, 18, 6, 10, 6, 6, 11, 8, 11, 5, 12, 5, 11, 6,
  10, 11, 11, 7, 17, 9, 7, 14, 14, 9, 5, 7, 13, 12, 8, 12, 11, 15, 9, 12,
],
```

### Custom template

````{list-grid}
:style: grid-template-columns: 1fr 1fr;
- ```{chartjs} template:random-bars
  :style: width: 90%;
  count: 3, min: 10, max: 50,
  ```
- ```{chartjs} template:random-bars
  :style: width: 90%;
  count: 5, min: 100, max: 500,
  ```
- ```{chartjs} template:random-bars
  :style: width: 90%;
  count: 2, min: 1, max: 10,
  ```
- ```{chartjs} template:random-bars
  :style: width: 90%;
  count: 20, min: 10, max: 50,
  ```
````

<script type="module">
const [core, {chart, template}] =
  await tdoc.imports('tdoc/core.js', 'tdoc/chart.js');

const months = ["January", "February", "March", "April", "May", "June", "July",
                "August", "September", "October", "November", "December"];

function xyrData(count, min, max, maxR) {
  const values = [];
  for (let i = 0; i < count; ++i) {
    values.push({x: core.randomInt(min, max), y: core.randomInt(min, max),
                 r: core.randomInt(1, maxR)});
  }
  return values;
}

chart('v-bar', {
  type: 'bar',
  data: {
    labels: months.slice(0, 7),
    datasets: [{
      data: [65, 59, 80, 81, 56, 55, 40],
      borderWidth: 1, borderColor: core.colors.blue,
      backgroundColor: core.colors.blue.with({a: 0.2}),
      hoverBorderColor: core.colors.blue,
    }],
  },
  options: {
    scales: {y: {beginAtZero: true}},
  },
});

chart('h-bar', {
  type: 'bar',
  data: {
    labels: months.slice(0, 7),
    datasets: [{
      axis: 'y',
      data: [65, 59, 80, 81, 56, 55, 40],
      borderWidth: 1, borderColor: core.palette,
      backgroundColor: core.palette.map(c => c.with({a: 0.2})),
      hoverBorderColor: core.palette,
    }],
  },
  options: {
    indexAxis: 'y',
  },
});

chart('bubble', {
  type: 'bubble',
  data: {
    datasets: [{
      data: xyrData(50, 0, 50, 15),
      borderWidth: 1, borderColor: core.palette,
      backgroundColor: core.palette.map(c => c.with({a: 0.2})),
      hoverBorderColor: core.palette,
    }],
  },
});

const pieColors = [core.colors.red, core.colors.blue, core.colors.yellow];
chart('pie', {
  type: 'pie',
  data: {
    labels: ["Red", "Blue", "Yellow"],
    datasets: [{
      data: [300, 50, 100],
      borderWidth: 1,
      borderColor: pieColors,
      backgroundColor: pieColors.map(c => c.with({a: 0.2})),
      hoverOffset: 50, hoverBorderWidth: 1, hoverBorderColor: pieColors,
    }],
  },
  options: {
    aspectRatio: 3 / 2,
    layout: {padding: 20},
    plugins: {legend: {display: true, position: 'right'}},
  },
});

chart('doughnut', {
  type: 'doughnut',
  data: {
    labels: ["Red", "Blue", "Yellow"],
    datasets: [
      {label: "Outer", data: [300, 50, 100]},
      {label: "Inner", data: [36, 13, 28]},
    ],
  },
  options: {
    borderAlign: 'inner',
    backgroundColor: pieColors,
    hoverBorderWidth: 2, hoverBorderColor: pieColors,
    hoverBackgroundColor: pieColors,
    aspectRatio: 3 / 2,
    layout: {padding: 20},
    plugins: {legend: {display: true, position: 'right'}},
  },
});

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
