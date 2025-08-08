% Copyright 2025 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Math

## JSXGraph

%This section renders live graphs using {rst:dir}`jsxgraph` directives.

```{jsxgraph} sincos
:style: aspect-ratio: 16 / 9;
```

<script type="module">
const [{JXG, render}] = await tdoc.imports('tdoc/jsxgraph.js');

const attrs = {
    boundingBox: [-7, 1.3, 7, -1.3],
    keepAspectRatio: false,
    axis: true,
    grid: true,
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
};

render('sincos', attrs, board => {
    board.create('functiongraph',
        [x => Math.sin(x)],
        {name: `\\(sin(x)\\)`, strokeColor: JXG.palette.blue,
         label: {position: '0.6fr left'}});
    board.create('functiongraph',
        [x => Math.cos(x)],
        {name: `\\(cos(x)\\)`, strokeColor: JXG.palette.red,
         label: {position: '0.69fr right'}});
});
</script>
