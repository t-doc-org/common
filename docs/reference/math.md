% Copyright 2025 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Math

## JSXGraph

`````{rst:directive} .. jsxgraph:: [template:]name
This directive creates a graph based on
[JSXGraph](https://jsxgraph.uni-bayreuth.de/wp/).

- [JSXGraph API documentation](https://jsxgraph.uni-bayreuth.de/docs/symbols/JXG.html)
- [JSXGraph examples](https://jsxgraph.uni-bayreuth.de/wiki/index.php/Category:Examples)

The graphs are constructed in JavaScript, by importing the {js:mod}`jsxgraph`
module and calling {js:func}`~jsxgraph.initBoard` for each {rst:dir}`jsxgraph`
directive, referencing it by name.

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

Alternatively, templates can be instantiated by prefixing the template name with
`template:`.

````{code-block}
```{jsxgraph} template:grid
width: 17.5, height: 5, grid: {minorElements: 9},
```
````

The aspect ratio of graph containers with `keepAspectRatio: true` (the default)
is set automatically from the `boundingBox`. Otherwise, the aspect ratio
defaults to `1 / 1`, and can be overridden with the
{rst:dir}`:style: <jsxgraph:style>` option.

Defaults can be set via the `jsxgraph:` {rst:dir}`metadata`, and are merged into
[`JXG.Options`](https://jsxgraph.uni-bayreuth.de/docs/symbols/src/src_options.js.html).

{.rubric}
Options
```{rst:directive:option} class: name [name...]
:type: IDs
A space-separated list of CSS classes to add to the graph container.
```
```{rst:directive:option} style: property: value; [property: value; ...]
CSS styles to apply to the graph container.
```
`````

### Templates

Templates are instantiated by specifying the template name prefixed by
`template:` as the directive argument. The template arguments are provided in
the directive content as a [JSON5](https://spec.json5.org/) object (without
enclosing `{}`).

The predefined templates are described below. Custom templates can be created in
JavaScript via {js:data}`~jsxgraph.templates`.

#### `grid`

This template renders a grid.

- `width` (default: 35): The width of the grid.
- `height` (default: 10): The height of the grid.
- `grid`:
  [`Grid`](https://jsxgraph.uni-bayreuth.de/docs/symbols/Grid.html)
  attribute overrides.
- `board`:
  [`Board`](https://jsxgraph.uni-bayreuth.de/docs/symbols/JXG.Board.html)
  attribute overrides.

````{code-block}
```{jsxgraph} template:grid
width: 17.5, height: 5, grid: {minorElements: 9},
```
````

#### `axes`

This template renders a set of axes and an optional grid.

- `boundingBox` (default: `[-11, 11, 11, -11]`): The bounding box of the graph.
- `majorX`, `majorY`, `major`: The distance between major ticks on the X axis,
  Y axis, or both. The default is `1`.
- `minorX`, `minorY`, `minor`: The number of minor ticks between major ticks
  on the X axis, Y axis, or both. The default is `0`.
- `labelsX`, `labelsY`, `labels`: The labels to draw for major ticks on the X
  axis, Y axis or both. When a number is given, only the labels for multiples
  of that number are drawn. When an array is given, only the listed labels are
  drawn. The default is to draw all labels.
- `grid`:
  [`Grid`](https://jsxgraph.uni-bayreuth.de/docs/symbols/Grid.html)
  attribute overrides, or `false` to disable the grid. The default is to draw
  grid lines at major ticks of both axes.
- `board`:
  [`Board`](https://jsxgraph.uni-bayreuth.de/docs/symbols/JXG.Board.html)
  attribute overrides.

````{code-block}
```{jsxgraph} template:axes
boundingBox: [-2, 5, 25, -5],
majorX: 5, minorX: 4, majorY: 2, minorY: 1,
grid: {majorStep: 1},
```
````

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

```{js:data} attrs
An object containing named attribute sets. Custom sets can be defined by
assigning to object attributes. The following sets are pre-defined:

- `nonInteractive`: Disable interactive features.
```

```{js:function} withAxesLabels(xs, ys)
Return mix-in board attributes to draw only selected labels on the default axes.
For number arguments, the labels that are their multiples are drawn. For array
arguments, only the listed values are drawn.

:arg !number|Array xs: The labels to draw on the X axis.
:arg !number|Array ys: The labels to draw on the Y axis.
:returns: An attribute object.
```

```{js:function} initBoard(el, attrs[, fn])
Render the content of a {rst:dir}`jsxgraph` directive.

In addition to board attributes, `attrs` can specify per object type defaults
for the graph in the `defaults` key, similar to how global defaults are
specified in
[JXG.Options](https://jsxgraph.uni-bayreuth.de/docs/symbols/JXG.Options.html).

:arg !string|HTMLElement el: The name of the {rst:dir}`jsxgraph` directive to
construct, or the wrapper DOM element that should contain the graph.
:arg !Object|Array attrs: The board attributes, passed to
`JSXGraph.initBoard()`. If an `Array` of attributes is provided, they are
merged.
:arg !function fn: An optional function that is called with the
[`Board`](https://jsxgraph.uni-bayreuth.de/docs/symbols/JXG.Board.html) as an
argument.
:returns: A `Promise` that resolves to the
[`Board`](https://jsxgraph.uni-bayreuth.de/docs/symbols/JXG.Board.html).
```

`````{js:data} templates
An object containing named templates. In addition to the
[pre-defined templates](#templates) described above, custom templates can be
added by setting functions as object attributes. A template function is called
for each {rst:dir}`jsxgraph` directive that specifies the template name. The
function receives the wrapper DOM element as its first argument, and
the content of the directive as a JSON object as its second argument.

````{code-block} html
```{jsxgraph} template:regular-polygon
sides: 4,
```
```{jsxgraph} template:regular-polygon
sides: 5,
```

<script type="module">
const [{initBoard, templates}] = await tdoc.imports('tdoc/jsxgraph.js');

templates['regular-polygon'] = (el, {sides}) => {
  return initBoard(el, {
    boundingBox: [-1.3, 1.3, 1.3, -1.3],
  }, board => {
    const s1 = 1 / sides;
    board.create('regularpolygon', [
      [Math.cos(Math.PI * (-0.5 - s1)), Math.sin(Math.PI * (-0.5 - s1))],
      [Math.cos(Math.PI * (-0.5 + s1)), Math.sin(Math.PI * (-0.5 + s1))],
      sides,
    ]);
  });
};
</script>
````
`````
