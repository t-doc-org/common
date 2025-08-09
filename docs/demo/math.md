% Copyright 2025 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Math

## JSXGraph

This section renders live graphs using {rst:dir}`jsxgraph` directives. The
graphs are interactive: some points can be dragged, and the graphs can be panned
and zoomed by holding {kbd}`Shift`.

### Sine and cosine

```{jsxgraph} sincos
:style: aspect-ratio: 16 / 9;
```

### Centroid

Drag $P_1$, $P_2$ and $P_3$.

```{jsxgraph} centroid
```

<script type="module">
const [{initBoard, JXG}] = await tdoc.imports('tdoc/jsxgraph.js');

initBoard('sincos', {
    boundingBox: [-7, 1.3, 7, -1.3], keepAspectRatio: false,
    axis: true, grid: true,
    defaults: {
        functiongraph: {
            withLabel: true,
            label: {
                distance: 1.5,
                offset: [0, 0],
                anchorX: 'middle',
                anchorY: 'middle',
            },
        },
    },
}, board => {
    board.create('functiongraph',
        [x => Math.sin(x)],
        {name: `\\(sin(x)\\)`, strokeColor: JXG.palette.blue,
         label: {position: '0.6fr left'}});
    board.create('functiongraph',
        [x => Math.cos(x)],
        {name: `\\(cos(x)\\)`, strokeColor: JXG.palette.red,
         label: {position: '0.69fr right'}});
});

initBoard('centroid', {
    boundingBox: [-3.2, 3.2, 3.2, -3.2],
    defaults: {
        line: {strokeWidth: 1.5},
    },
}, board => {
    const is = [0, 1, 2];
    const p = is.map(i => board.create('point',
        [3 * Math.cos(i * 2 * Math.PI / 3) + 0.5 * (i - 1),
         3 * Math.sin(i * 2 * Math.PI / 3)],
        {name: `\\(P_${i + 1}\\)`}));
    is.map(i => board.create('segment',
        [p[i], p[(i + 1) % 3]], {strokeColor: JXG.palette.black}));
    const m = is.map(i => board.create('midpoint',
        [p[(i + 1) % 3], p[(i + 2) % 3]], {name: `\\(M_${i + 1}\\)`}));
    const med = is.map(i => board.create('segment',
        [p[i], m[i]], {strokeColor: JXG.palette.blue}));
    board.create('intersection', [med[0], med[1]], {name: '\\(C\\)'});
});
</script>
