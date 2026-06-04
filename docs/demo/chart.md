% Copyright 2026 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Charts

```{metadata} json
chartjs: {plugins: {legend: {display: false}}},
```

## Chart.js

This section renders charts of various types using {rst:dir}`chartjs`
directives.

### Bar chart

([Documentation](https://www.chartjs.org/docs/latest/charts/bar.html))

```{chartjs} v-bar
```

```{chartjs} h-bar
```

### Line chart

([Documentation](https://www.chartjs.org/docs/latest/charts/line.html))

```{chartjs} line
```

### Bubble chart

([Documentation](https://www.chartjs.org/docs/latest/charts/bubble.html))

```{chartjs} bubble
```

### Pie & doughnut chart

([Documentation](https://www.chartjs.org/docs/latest/charts/doughnut.html))

```{chartjs} pie
:style: width: 70%;
```

```{chartjs} doughnut
:style: width: 70%;
```

### Boxplot & violin chart

([Documentation](https://www.sgratzl.com/chartjs-chart-boxplot/))

```{chartjs} boxplot
```

```{chartjs} violin
```

### Error bar chart

([Documentation](https://www.sgratzl.com/chartjs-chart-error-bars/))

```{chartjs} bar-error-bars
```

```{chartjs} line-error-bars
```

### Venn diagrams

([Documentation](https://upset.js.org/chartjs-chart-venn/),
[data structure](https://github.com/upsetjs/chartjs-chart-venn#venn-diagram))

```{chartjs} venn
:style: |
: width: 70%; border: 1px solid var(--pst-color-border);
: border-radius: 0.25rem; padding: 2rem 0;
```

### Graph chart

([Documentation](https://www.sgratzl.com/chartjs-chart-graph/))

```{chartjs} tree
```

```{chartjs} graph
```

### Template: `chart`

```{chartjs} template:chart
type: 'bar',
data: {
  labels: ['Monday', 'Tuesday', 'Wednesday'],
  datasets: [{
    label: "Option A",
    data: [7, 11, 3],
    borderColor: '#36a2eb', hoverBorderColor: '#36a2eb',
    backgroundColor: '#36a2eb33',
  }, {
    label: "Option B",
    data: [6, 9, 2],
    borderColor: '#ff6384', hoverBorderColor: '#ff6384',
    backgroundColor: '#ff638433',
  }],
},
options: {
  borderWidth: 1,
  scales: {y: {beginAtZero: true}},
},
```

### Template: `histogram`

A histogram computed from a sample, with annotations computed from the sample
as well.

```{chartjs} template:histogram
uniform: {min: 0, max: 24, width: 2},
annotations: [{
  min: {}, max: {}, quartile: {k: [1, 3]}, percentile: {p: [5, 95]},
}, {
  quantile: {p: [0.01, 0.99]},
  options: {label: {rotation: -90}},
}, {
  median: {}, avgDev: {f: [-1, 1]},
  options: {
    borderColor: '#9966ff',
    label: {position: '25%', backgroundColor: '#9966ffcc'},
  },
}, {
  mean: {}, stdDev: {f: [-2, -1, 1, 2]},
  options: {
    borderColor: '#ff6384',
    label: {position: '40%', backgroundColor: '#ff6384cc'},
  },
}, {
  mode: {},
  options: {
    borderColor: '#ff9f40',
    label: {position: 'end', rotation: -90, backgroundColor: '#ff9f40cc'},
  },
}, {
  hLine: {y: 25, label: "half-capacity"},
  vLine: {x: 22, label: "closing time", options: {label: {rotation: -90}}},
  options: {borderColor: '#4bc0c0', label: {backgroundColor: '#4bc0c0cc'}},
}],
options: {
  borderWidth: 0.5, borderColor: '#36a2eb', hoverBorderColor: '#36a2eb',
  backgroundColor: '#36a2eb33',
  scales: {
    x: {title: {display: true, text: "Hours"}},
    y: {title: {display: true, text: "Visitors"}},
  },
},
sample: [
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

A histogram of a distribution, with annotations computed from the distribution
as well.

```{chartjs} template:histogram
annotations: [{
  min: {}, max: {}, quartile: {k: [1, 3]}, percentile: {p: [5, 95]},
}, {
  quantile: {p: [0.01, 99]},
  options: {label: {position: '30%', rotation: -90}},
}, {
  median: {}, avgDev: {f: [-1, 1]},
  options: {
    borderColor: '#9966ff',
    label: {position: '20%', backgroundColor: '#9966ffcc'},
  },
}, {
  mean: {}, stdDev: {f: [-1, 1]},
  options: {
    borderColor: '#ff6384',
    label: {position: '30%', backgroundColor: '#ff6384cc'},
  },
}, {
  mode: {},
  options: {
    borderColor: '#ff9f40',
    label: {position: 'end', rotation: -90, backgroundColor: '#ff9f40cc'},
  },
}],
options: {
  borderWidth: 0.5, borderColor: '#36a2eb', hoverBorderColor: '#36a2eb',
  backgroundColor: '#36a2eb33',
  scales: {
    x: {title: {display: true, text: "Hours"}},
    y: {title: {display: true, text: "Visitors"}},
  },
},
distribution: [
  [0, 0], [2, 1], [4, 3], [6, 7], [8, 8], [10, 2], [12, 1],
  [14, 6], [16, 9], [18, 8], [20, 5], [22, 0], [24],
],
```

### Template: `cumulative-distribution-function`

A normalized cumulative distribution function computed from a sample.

```{chartjs} template:cumulative-distribution-function
min: 0, max: 24, step: 2,
options: {
  borderColor: '#36a2eb',
  scales: {
    x: {title: {display: true, text: "Hours"}},
    y: {title: {display: true, text: "Visitors"}},
  },
},
annotations: [{
  min: {}, percentile: {p: 5}, quartile: {k: 1}, median: {},
  quantile: {p: 0.01, options: {label: {rotation: -90}}},
}, {
  quartile: {k: 3}, percentile: {p: 95}, max: {},
  quantile: {p: 0.99, options: {label: {rotation: -90}}},
  options: {label: {position: 'end'}},
}, {
  hLine: {y: 0.5},
  options: {borderColor: '#4bc0c0', label: {backgroundColor: '#4bc0c0cc'}},
}],
sample: [
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

A non-normalized cumulative distribution function computed from a distribution.

```{chartjs} template:cumulative-distribution-function
min: 0, max: 24, step: 2, normalize: false,
options: {
  borderColor: '#36a2eb',
  scales: {
    x: {title: {display: true, text: "Hours"}},
    y: {title: {display: true, text: "Visitors (normalized)"}},
  },
},
annotations: [{
  min: {}, percentile: {p: 5}, quartile: {k: 1}, median: {},
  quantile: {p: 0.01, options: {label: {position: '30%', rotation: -90}}},
}, {
  quartile: {k: 3}, percentile: {p: 95}, max: {},
  quantile: {p: 0.99, options: {label: {position: '75%', rotation: -90}}},
  options: {label: {position: 'end'}},
}, {
  count: {f: 0.5},
  options: {borderColor: '#4bc0c0', label: {backgroundColor: '#4bc0c0cc'}},
}],
distribution: [
  [0, 0], [2, 1], [4, 3], [6, 7], [8, 8], [10, 2], [12, 1],
  [14, 6], [16, 9], [18, 8], [20, 5], [22, 0], [24],
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

### Custom annotation

% TODO: Add an example

<script type="module">
const [core, {chart, templates}] =
  await tdoc.imports('tdoc/core.js', 'tdoc/chart.js');

const colors = ['#36a2eb', '#ff6384', '#4bc0c0', '#ff9f40', '#9966ff',
                '#ffcd56', '#c9cbcf'];
const bgColors = colors.map(c => `${c}33`);
const months = ["January", "February", "March", "April", "May", "June", "July",
                "August", "September", "October", "November", "December"];

function data(count, min, max, extra=[]) {
  const values = [];
  for (let i = 0; i < count; ++i) values.push(core.randomInt(min, max));
  values.push(...extra);
  return values;
}

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
    datasets: [{data: data(7, 50, 100)}],
  },
  options: {
    borderWidth: 1, borderColor: colors[0], hoverBorderColor: colors[0],
    backgroundColor: bgColors[0],
    scales: {y: {beginAtZero: true}},
  },
});

chart('h-bar', {
  type: 'bar',
  data: {
    labels: months.slice(0, 7),
    datasets: [{axis: 'y', data: [65, 59, 80, 81, 56, 55, 40]}],
  },
  options: {
    indexAxis: 'y',
    borderWidth: 1, borderColor: colors, hoverBorderColor: colors,
    backgroundColor: bgColors,
  },
});

chart('line', {
  type: 'line',
  data: {
    labels: months.slice(0, 7),
    datasets: [{
      data: data(7, 0, 100),
      borderColor: colors[0], backgroundColor: colors[0],
    }, {
      data: data(7, 50, 100),
      borderColor: colors[1], backgroundColor: colors[1],
    }],
  },
  options: {
    borderWidth: 2,
    scales: {y: {beginAtZero: true}},
  },
});

chart('bubble', {
  type: 'bubble',
  data: {
    datasets: [{data: xyrData(50, 0, 50, 15)}],
  },
  options: {
    borderWidth: 1, borderColor: colors, hoverBorderColor: colors,
    backgroundColor: bgColors,
  },
});

const pieIdx = cs => [1, 0, 5].map(i => cs[i]);
chart('pie', {
  type: 'pie',
  data: {
    labels: ["Red", "Blue", "Yellow"],
    datasets: [{data: [300, 50, 100]}],
  },
  options: {
    aspectRatio: 3 / 2,
    layout: {padding: 20},
    borderWidth: 1, borderColor: pieIdx(colors),
    backgroundColor: pieIdx(bgColors),
    hoverOffset: 50, hoverBorderWidth: 1,
    hoverBorderColor: pieIdx(colors),
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
    aspectRatio: 3 / 2,
    layout: {padding: 20},
    borderAlign: 'inner',
    backgroundColor: pieIdx(colors),
    hoverBorderWidth: 2, hoverBorderColor: pieIdx(colors),
    hoverBackgroundColor: pieIdx(colors),
    plugins: {legend: {display: true, position: 'right'}},
  },
});

const boxViolin = {
  data: {
    labels: ['A', 'B', 'C'],
    datasets: [{
      label: 'Dataset 1',
      data: [data(100, 0, 100), data(100, 0, 20, [110]), data(100, 20, 70)],
      borderColor: colors[0], hoverBorderColor: colors[0],
      backgroundColor: bgColors[0],
    }, {
      label: 'Dataset 2',
      data: [data(100, 60, 100, [5, 10]), data(100, 0, 100), data(100, 0, 20)],
      borderColor: colors[1], hoverBorderColor: colors[1],
      backgroundColor: bgColors[1],
    }],
  },
};
chart('boxplot', {'type': 'boxplot', ...boxViolin});
chart('violin', {'type': 'violin', ...boxViolin});

const errorBar = {
  data: {
    labels: ['A', 'B', 'C'],
    datasets: [{data: [
      {y: 4, yMin: 1, yMax: 6},
      {y: 2, yMin: 1, yMax: 4},
      {y: 5, yMin: 4, yMax: 6},
    ]}],
  },
};
chart('bar-error-bars', {
  type: 'barWithErrorBars', ...errorBar,
  options: {
    borderWidth: 1, borderColor: colors, hoverBorderColor: colors,
    backgroundColor: bgColors,
  },
});
chart('line-error-bars', {
  type: 'lineWithErrorBars', ...errorBar,
  options: {borderColor: colors[0], backgroundColor: colors[0]},
});

chart('venn', {
  type: 'venn',
  data: {
    labels: ['A', 'B', 'A ∩ B'],
    datasets: [{
      data: [
        {sets: ['A'], value: 'A'},
        {sets: ['B'], value: 'B'},
        {sets: ['A', 'B'], value: 'A ∩ B'},
      ],
    }],
  },
  options: {
    borderWidth: 1, borderColor: colors,
    backgroundColor: bgColors,
    scales: {
      x: {ticks: {font: {size: 16}}},   // Labels within the sets
      y: {ticks: {display: false}},     // Labels next to the sets
    },
    plugins: {tooltip: false},
  },
});

const treeData = [
  {name: "1"},
  {name: "11", parent: 0},
  {name: "111", parent: 1},
  {name: "1111", parent: 2},
  {name: "1112", parent: 2},
  {name: "112", parent: 1},
  {name: "1121", parent: 5},
  {name: "1122", parent: 5},
  {name: "113", parent: 1},
  {name: "1131", parent: 8},
  {name: "1132", parent: 8},
  {name: "12", parent: 0, width: 7},
  {name: "121", parent: 11, width: 10},
  {name: "1211", parent: 12},
  {name: "1212", parent: 12},
  {name: "122", parent: 11, width: 5},
  {name: "1221", parent: 15},
  {name: "1222", parent: 15},
  {name: "123", parent: 11, width: 10},
  {name: "1231", parent: 18},
  {name: "1232", parent: 18},
  {name: "13", parent: 0},
  {name: "131", parent: 21},
];
chart('tree', {
  type: 'tree',
  data: {
    labels: treeData.map(d => d.name),
    datasets: [{
      data: treeData,
      edgeLineBorderWidth: ctx => treeData[ctx.parsed.target].width ?? 3,
    }],
  },
  options: {
    tree: {mode: 'tree'},
    borderColor: colors[6] + '99',
    pointRadius: 5,
    pointBorderColor: colors[0], pointBackgroundColor: colors[0],
  },
});

const graphData = await core.fetchJson('/_static/miserables.json',
                                       {method: 'GET'});
chart('graph', {
  type: 'forceDirectedGraph',
  data: {
    labels: graphData.nodes.map(d => d.id),
    datasets: [{
      data: graphData.nodes,
      edges: graphData.links,
    }],
  },
  options: {
    tree: {mode: 'tree'},
    borderColor: colors[6] + '99',
    pointRadius: 5,
    pointBorderColor: colors[0], pointBackgroundColor: colors[0],
    plugins: {deferred: false},  // Rendering fails when deferred
  },
});

templates['random-bars'] = (el, {count, min, max}) => {
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
      borderWidth: 1, borderColor: colors[0], hoverBorderColor: colors[0],
      backgroundColor: bgColors[0],
      scales: {y: {beginAtZero: true}},
      plugins: {legend: {display: false}},
    },
  })
};
</script>
