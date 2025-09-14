% Copyright 2025 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Math

## JSXGraph

``````{rst:directive} .. jsxgraph:: [name]
This directive creates a graph based on
[JSXGraph](https://jsxgraph.uni-bayreuth.de/wp/). The graphs are constructed in
JavaScript, by importing the
{js:mod}`jsxgraph` module and calling {js:func}`~jsxgraph.initBoard` for each
{rst:dir}`jsxgraph` directive, referencing it by name. Alternatively, a template
can be instantiated with the {rst:dir}`:template: <jsxgraph:template>` option.

The aspect ratio of graph containers with `keepAspectRatio: true` (the default)
is set automatically from the `boundingBox`. Otherwise, the aspect ratio
defaults to `1 / 1`, and can be overridden with the
{rst:dir}`:style: <jsxgraph:style>` option.

- [JSXGraph API documentation](https://jsxgraph.uni-bayreuth.de/docs/symbols/JXG.html)
- [JSXGraph examples](https://jsxgraph.uni-bayreuth.de/wiki/index.php/Category:Examples)

````{code-block} html
```{jsxgraph} sin
:style: aspect-ratio: 16 / 9;
```

<script type="module">
const [{initBoard}] = await tdoc.imports('tdoc/jsxgraph.js');
initBoard('sin', {
    boundingBox: [-7, 1.3, 7, -1.3], keepAspectRatio: false,
    axis: true, grid: true,
}, board => {
    board.create('functiongraph', [x => Math.sin(x)]);
});
</script>
````

{.rubric}
Options
```{rst:directive:option} class: name [name...]
:type: IDs
A space-separated list of CSS classes to add to the graph container.
```
```{rst:directive:option} style: property: value; [property: value; ...]
CSS styles to apply to the graph container.
```
`````{rst:directive:option} template: name(args...)
Instantiate a graph template using the given arguments. The arguments are given
as a [JSON5](https://spec.json5.org/) array. {rst:dir}`jsxgraph` directives
instantiating a template must not have a name.

The following templates are predefined. Custom templates can be created in
JavaScript via {js:func}`~jsxgraph.template`.

- `grid(width = 35, height = 10, grid = {}, board = {})`{l=js}\
  Render a grid.
  - `width`, `height`: The width and height of the grid.
  - `grid`:
    [`Grid`](https://jsxgraph.uni-bayreuth.de/docs/symbols/Grid.html)
    attribute overrides.
  - `board`:
    [`Board`](https://jsxgraph.uni-bayreuth.de/docs/symbols/JXG.Board.html)
    attribute overrides.

  ````{code-block}
  ```{jsxgraph}
  :template: grid(17.5, 5, {minorElements: 9})
  ```
  ````

- `axes(boundingBox = [-11, 11, 11, -11], opts = {}, board = {})`{l=js}\
  Render a set of axes and an optional grid.
  - `boundingBox`: The bounding box of the graph.
  - `opts`: Optional
    - `majorX`, `majorY`, `major`: The distance between major ticks on the X
      axis, Y axis, or both. The default is `1`.
    - `minorX`, `minorY`, `minor`: The number of minor ticks between major ticks
      on the X axis, Y axis, or both. The default is `0`.
    - `labelsX`, `labelsY`, `labels`: The labels to draw for major ticks on the
      X axis, Y axis or both. When a number is given, only the labels for
      multiples of that number are drawn. When an array is given, only the
      listed labels are drawn. The default is to draw all labels.
    - `grid`:
      [`Grid`](https://jsxgraph.uni-bayreuth.de/docs/symbols/Grid.html)
      attribute overrides, or `false` to disable the grid. The default is to
      draw grid lines at major ticks of both axes.
  - `board`:
    [`Board`](https://jsxgraph.uni-bayreuth.de/docs/symbols/JXG.Board.html)
    attribute overrides.

  ````{code-block}
  ```{jsxgraph}
  :template: |
  : axes([-2, 5, 25, -5],
  :      {majorX: 5, minorX: 4, majorY: 2, minorY: 1, grid: {majorStep: 1}})
  ```
  ````
`````
``````

### `tdoc/jsxgraph.js`

`````{js:module} jsxgraph
This module
([source](https://github.com/t-doc-org/common/blob/main/tdoc/common/static/tdoc/jsxgraph.js))
provides functionality related to {rst:dir}`jsxgraph` directives.
`````

```{js:data} JXG
The [`JXG`](https://jsxgraph.uni-bayreuth.de/docs/symbols/JXG.html) namespace of
the JSXGraph library.
```

```{js:data} nonInteractive
Mix-in board attributes to disable interactive features.
```

```{js:function} withAxesLabels(xs, ys)
Return mix-in board attributes to to draw only selected labels on the default
axes. For number arguments, the labels that are their multiples are drawn. For
array arguments, only the listed values are drawn.

:arg !number|Array xs: The labels to draw on the X axis.
:arg !number|Array ys: The labels to draw on the Y axis.
:returns: An attribute object.
```

```{js:function} merge(...attrs)
Merge multiple attributes objects. `Array` arguments have their items merged
recursively.

:arg !Array[Object|Array] attrs: The attribute objects to merge. Later arguments
override earlier ones.
:returns: The merged attribute object.
```

```{js:function} initBoard(el, attrs[, fn])
Render the content of a {rst:dir}`jsxgraph` directive.

In addition to board attributes, `attrs` can specify per object type defaults
for the graph in the `defaults` key, similar to how global defaults are
specified in
[JXG.Options](https://jsxgraph.uni-bayreuth.de/docs/symbols/JXG.Options.html).

:arg !string el: The name of the {rst:dir}`jsxgraph` directive to construct,
or the wrapper DOM element that should contain the graph.
:arg !Object|Array attrs: The board attributes, passed to
`JSXGraph.initBoard()`. If an `Array` of attributes is provided, they are merged
with {js:func}`~merge`.
:arg !function fn: An optional function that is called with the
[`Board`](https://jsxgraph.uni-bayreuth.de/docs/symbols/JXG.Board.html) as an
argument.
:returns: A `Promise` that resolves to the
[`Board`](https://jsxgraph.uni-bayreuth.de/docs/symbols/JXG.Board.html).
```

`````{js:function} template(name, fn)
Render all {rst:dir}`jsxgraph` directives referencing the template with the
given name.

:arg !string name: The name of the template.
:arg !function fn: A function to be called for each {rst:dir}`jsxgraph`
directive to render. The function receives the wrapper DOM element as its first
argument, and the arguments of the {rst:dir}`:template: <jsxgraph:template>`
option as remaining arguments.

````{code-block} html
```{jsxgraph}
:template: regular-polygon(4)
```
```{jsxgraph}
:template: regular-polygon(5)
```

<script type="module">
const [{initBoard, template}] = await tdoc.imports('tdoc/jsxgraph.js');
template('regular-polygon', (el, n) => {
    initBoard(el, {
        boundingBox: [-1.3, 1.3, 1.3, -1.3],
    }, board => {
        const n1 = 1 / n;
        board.create('regularpolygon', [
            [Math.cos(Math.PI * (-0.5 - n1)), Math.sin(Math.PI * (-0.5 - n1))],
            [Math.cos(Math.PI * (-0.5 + n1)), Math.sin(Math.PI * (-0.5 + n1))],
            n,
        ]);
    });
});
</script>
````
`````
