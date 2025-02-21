% Copyright 2024 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Python libraries

The modules described below are packaged into a library and made available to
Python code executed through the [`{exec} python`](exec.md#python) directive.
Additionally, all files in the directory `_python` (next to `conf.py`) are also
included recursively in the library.

## `tdoc.core`

````{py:module} tdoc.core
This module
([source](https://github.com/t-doc-org/common/blob/main/tdoc/common/python/core.py))
provides basic functionality for [`{exec} python`](exec.md#python) blocks. It
doesn't need to be imported explicitly: all its public symbols are available in
the global scope of  [`{exec} python`](exec.md#python) blocks.
````

```{py:function} new_id() -> str
Generate a unique ID, usable in the `id=` attribute of an HTML element.
```

```{py:function} render(html, name='') -> asyncio.Future
Render an HTML snippet as an output block. Output blocks are displayed ordered
by name. If an output block with the same name already exists, it is replaced
with the new one.
:arg str | Iterator(str) html: The HTML snippet to be rendered.
:arg str name: The name of the output block.
:returns: A `Future` that resolves to the size of the output block, as a
`(width, height)` tuple.
```

```{py:function} input(prompt=None) -> str
Request a single line of text from the user, and wait for them to submit a
reply.

**Note:** This function relies on an
[experimental feature](https://github.com/WebAssembly/js-promise-integration)
that is currently only implemented in Google Chrome and Microsoft Edge
([details](../demo/python.md#call-async-functions-synchronously)). For a more
portable alternative, use {py:func}`input_line`.
:arg str prompt: An optional prompt to display before the input field.
```

```{py:function} input_line(prompt=None) -> str
:async:
Request a single line of text from the user, and wait for them to submit a
reply.
:arg str prompt: An optional prompt to display before the input field.
```

```{py:function} input_text(prompt=None) -> str
:async:
Request a multi-line text from the user, and wait for them to submit a reply.
:arg str prompt: An optional prompt to display before the input field.
```

```{py:function} input_buttons(prompt, labels) -> int
:async:
Present a list of buttons and wait for the user to click one of them.
:arg str prompt: An optional prompt to display before the buttons.
:arg list(str) labels: The labels of the buttons to display.
:returns: The index in `labels` of the button that was clicked.
```

```{py:function} pause(prompt=None, label="@icon{forward-step}")
:async:
Present a button, and wait for the user to click it.
:arg str prompt: An optional prompt to display before the button.
:arg str label: The label of the button. If the label has the format
`@icon{...}`, the corresponding icon from
[Font Awesome](https://fontawesome.com/icons/categories) is used.
```

````{py:function} redirect(stdout=None, stderr=None)
Return a context manager that temporarily replaces {py:data}`sys.stdout` and /
or {py:data}`sys.stderr` with the given stream(s). This function must be used
instead of direct assignment or {py:func}`contextlib.redirect_stdout` /
{py:func}`contextlib.redirect_stderr` to avoid redirecting the output of all
code blocks on the same page.

:arg stdout: The new value to set as {py:data}`sys.stdout`.
:arg stderr: The new value to set as {py:data}`sys.stderr`.

```{exec} python
:when: load
import io
out = io.StringIO()
with redirect(stdout=out):
    print("Hello, world!")
print(f"Captured output: {out.getvalue().rstrip()}")
```
````

## `tdoc.svg`

````{py:module} tdoc.svg
This module
([source](https://github.com/t-doc-org/common/blob/main/tdoc/common/python/svg.py))
allows creating [SVG](https://developer.mozilla.org/en-US/docs/Web/SVG) images
using simple drawing primitives and rendering them in an output block.

To create an SVG image, instantiate the {py:class}`Image` class,
[add elements](#tdoc.svg.Container) to it, then display it with
{py:func}`~tdoc.core.render`. Animations can be implemented by repeatedly
rendering images.

```{exec} python
:when: load
:editor:
from tdoc import svg

# Create the image.
img = svg.Image(400, 100, stroke='black', fill='transparent',
                style='width: 100%; height: 100%')

# Add a red dashed circle.
img.circle(200, 50, 45, stroke=svg.Stroke('red', dash_array='4 2'))

# Add two lines, grouped to avoid repeating the blue stroke.
g = img.group(stroke=svg.Stroke('blue', width=2))
g.line(0, 0, 400, 100)
g.line(0, 100, 400, 0)

# Add a partially-transparent ellipse.
img.ellipse(200, 50, 195, 35, fill=svg.Fill('#f0f0f0', opacity=0.8))

# Display the image.
render(img)
```
````

### Containers

The following classes implement concrete containers. `kwargs` are forwarded to
{py:class}`Container`.

````{py:class} Image(width, height, *, stylesheet=None, **kwargs)
Represents an
[`<svg>`](https://developer.mozilla.org/en-US/docs/Web/SVG/Element/svg)
element, a complete SVG image. The viewport of the image is set to
`(0, 0, width, height)`, with the `(0, 0)` coordinate at the top left, the `x`
axis pointing to the right and the `y` axis pointing down.
:arg int width,height: The size of the image in pixels.
:arg str stylesheet: A [CSS](https://developer.mozilla.org/en-US/docs/Web/CSS)
stylesheet that is scoped to the image.
````

````{py:class} Group(**kwargs)
Represents a
[`<g>`](https://developer.mozilla.org/en-US/docs/Web/SVG/Element/g)
element, a visible group of shapes.
````

````{py:class} Symbol(**kwargs)
Represents a
[`<symbol>`](https://developer.mozilla.org/en-US/docs/Web/SVG/Element/symbol)
element, an invisible group of shapes that can be referenced by {py:class}`Use`
elements.
````

---

All concrete containers inherit from {py:class}`Container`, which itself
inherits from {py:class}`Shape`. `kwargs` are forwarded to {py:class}`Shape`.

````{py:class} Container(**kwargs)
A container of shapes. It is itself a {py:class}`Shape`, so it can be added to
other containers.

```{py:attribute} children
:type: list
The list of contained shapes.
```
```{py:method} add(child)
Add a child to the container. Returns `child`.
```
```{py:method} circle(x, y, r, **kwargs) -> Circle
Add a
[`<circle>`](https://developer.mozilla.org/en-US/docs/Web/SVG/Element/circle) to
the container.
:arg x,y: The coordinates of the center of the circle.
:arg r: The radius of the circle.
```
```{py:method} ellipse(x, y, rx, ry, **kwargs) -> Ellipse
Add an
[`<ellipse>`](https://developer.mozilla.org/en-US/docs/Web/SVG/Element/ellipse)
to the container.
:arg x,y: The coordinates of the center of the ellipse.
:arg rx,ry: The horizontal and vertical radii of the ellipse.
```
```{py:method} line(x1, y1, x2, y2, **kwargs) -> Line
Add a
[`<line>`](https://developer.mozilla.org/en-US/docs/Web/SVG/Element/line) to the
container.
:arg x1,y1: The start coordinates of the line.
:arg x2,y2: The end coordinates of the line.
```
```{py:method} path(*path, **kwargs) -> Path
Add a
[`<path>`](https://developer.mozilla.org/en-US/docs/Web/SVG/Element/path) to the
container.
:arg path: A sequence of strings or tuples defining the
[path to be drawn](https://developer.mozilla.org/en-US/docs/Web/SVG/Attribute/d).
```
```{py:method} polygon(*points, **kwargs) -> Polygon
Add a
[`<polygon>`](https://developer.mozilla.org/en-US/docs/Web/SVG/Element/polygon)
to the container.
:arg points: A sequence of `(x, y)` tuples defining the
[points of the polygon](https://developer.mozilla.org/en-US/docs/Web/SVG/Attribute/points).
```
```{py:method} polyline(*points, **kwargs) -> Polyline
Add a
[`<polyline>`](https://developer.mozilla.org/en-US/docs/Web/SVG/Element/polyline)
to the container.
:arg points: A sequence of `(x, y)` tuples defining the
[points of the polyline](https://developer.mozilla.org/en-US/docs/Web/SVG/Attribute/points).
```
```{py:method} rect(x, y, width, height, *, rx=None, ry=None, **kwargs) -> Rect
Add a
[`<rect>`](https://developer.mozilla.org/en-US/docs/Web/SVG/Element/rect) to the
container.
:arg x,y: The origin of the rectangle.
:arg width,height: The size of the rectangle.
:arg rx,ry: The horizontal and vertical corner radii of the rectangle.
```
```{py:method} text(x, y, text, **kwargs) -> Text
Add a
[`<text>`](https://developer.mozilla.org/en-US/docs/Web/SVG/Element/text) to the
container.
:arg x,y: The coordinates of the start of the text (baseline).
:arg text: The text to be displayed.
```
```{py:method} group(**kwargs) -> Group
Add a
[`<g>`](https://developer.mozilla.org/en-US/docs/Web/SVG/Element/g) to the
container.
```
```{py:method} symbol(**kwargs) -> Symbol
Add a
[`<symbol>`](https://developer.mozilla.org/en-US/docs/Web/SVG/Element/symbol)
to the container.
```
```{py:method} use(href, *, x=0, y=0, **kwargs) -> Use
Add a
[`<use>`](https://developer.mozilla.org/en-US/docs/Web/SVG/Element/use) to the
container.
:arg href: The shape to reference, an object with an `id` attribute (typically a
concrete shape instance).
:arg x,y: The coordinates of the shape's origin.
```
````

### Shapes

The following classes implement concrete shapes. `kwargs` are forwarded to
{py:class}`Shape`.

````{py:class} Circle(x, y, r, **kwargs)
Represents a
[`<circle>`](https://developer.mozilla.org/en-US/docs/Web/SVG/Element/circle)
element.
:arg x,y: The coordinates of the center of the circle.
:arg r: The radius of the circle.
````

````{py:class} Ellipse(x, y, rx, ry, **kwargs)
Represents an
[`<ellipse>`](https://developer.mozilla.org/en-US/docs/Web/SVG/Element/ellipse)
element.
:arg x,y: The coordinates of the center of the ellipse.
:arg rx,ry: The horizontal and vertical radii of the ellipse.
````

````{py:class} Line(x1, y1, x2, y2, **kwargs)
Represents a
[`<line>`](https://developer.mozilla.org/en-US/docs/Web/SVG/Element/line)
element.
:arg x1,y1: The start coordinates of the line.
:arg x2,y2: The end coordinates of the line.
````

````{py:class} Path(*path, **kwargs)
Represents a
[`<path>`](https://developer.mozilla.org/en-US/docs/Web/SVG/Element/path)
element.
:arg path: A sequence of strings or tuples defining the
[path to be drawn](https://developer.mozilla.org/en-US/docs/Web/SVG/Attribute/d).
````

````{py:class} Polygon(*points, **kwargs)
Represents a
[`<polygon>`](https://developer.mozilla.org/en-US/docs/Web/SVG/Element/polygon)
element.
:arg points: A sequence of `(x, y)` tuples defining the
[points of the polygon](https://developer.mozilla.org/en-US/docs/Web/SVG/Attribute/points).
````

````{py:class} Polyline(*points, **kwargs)
Represents a
[`<polyline>`](https://developer.mozilla.org/en-US/docs/Web/SVG/Element/polyline)
element.
:arg points: A sequence of `(x, y)` tuples defining the
[points of the polyline](https://developer.mozilla.org/en-US/docs/Web/SVG/Attribute/points).
````

````{py:class} Rect(x, y, width, height, *, rx=None, ry=None, **kwargs)
Represents a
[`<rect>`](https://developer.mozilla.org/en-US/docs/Web/SVG/Element/rect)
element.
:arg x,y: The origin of the rectangle.
:arg width,height: The size of the rectangle.
:arg rx,ry: The horizontal and vertical corner radii of the rectangle.
````

````{py:class} Text(x, y, text, **kwargs)
Represents a
[`<text>`](https://developer.mozilla.org/en-US/docs/Web/SVG/Element/text)
element.
:arg x,y: The coordinates of the start of the text (baseline).
:arg text: The text to be displayed.
````

````{py:class} Use(href, *, x=0, y=0, **kwargs)
Represents a
[`<use>`](https://developer.mozilla.org/en-US/docs/Web/SVG/Element/use)
element.
:arg href: The shape to reference, an object with an `id` attribute (typically a
concrete shape instance).
:arg x,y: The coordinates of the shape's origin.
````

---

All concrete shapes, as well as all container classes, inherit from
{py:class}`Shape`.

````{py:class} Shape(*, klass=None, style=None, stroke=None, fill=None, transform=None)
A geometrical shape that can be painted.

:arg str klass: The element's `class` attribute, to be referenced in an
{py:class}`Image` stylesheet (`class` is a reserved word in Python, so it cannot
be used as an argument name).
:arg str style: The element's `style` attribute.
:arg str | Stroke stroke: The stroke with which to paint the shape.
:arg str | Fill fill: The fill to use to paint the shape.
:arg Transform transform: A transform to apply to the shape.

```{py:property} id
:type: str
The unique ID of the element.
```
````

### Attributes

Attribute instances are passed as arguments to shapes.

````{py:class} Stroke(color=None, *, width=None, opacity=None, dash_array=None, dash_offset=None, line_cap=None, line_join=None, miter_limit=None)
Represents a set of attributes describing a
[stroke](https://developer.mozilla.org/en-US/docs/Web/SVG/Attribute/stroke), to
be passed as a `stroke` argument.
````

````{py:class} Fill(color=None, *, opacity=None, rule=None)
Represents a set of attributes describing a
[fill](https://developer.mozilla.org/en-US/docs/Web/SVG/Attribute/fill), to be
passed as a `fill` argument.
````

````{py:class} Transform
Represents a set of attributes describing a
[transform](https://developer.mozilla.org/en-US/docs/Web/SVG/Attribute/transform),
to be passed as a `transform` argument.

```{py:method} matrix(a=0, b=0, c=0, d=0, e=0, f=0)
Add a
[matrix](https://developer.mozilla.org/en-US/docs/Web/SVG/Attribute/transform#matrix)
to the transform.
```
```{py:method} translate(x=0, y=0)
Add a
[translation](https://developer.mozilla.org/en-US/docs/Web/SVG/Attribute/transform#translate)
to the transform.
```
```{py:method} scale(x=0, y=None)
Add a
[scaling](https://developer.mozilla.org/en-US/docs/Web/SVG/Attribute/transform#scale)
to the transform.
```
```{py:method} rotate(angle, x=None, y=None)
Add a
[rotation](https://developer.mozilla.org/en-US/docs/Web/SVG/Attribute/transform#rotate)
(in degrees) to the transform.
```
```{py:method} skew_x(angle)
Add an
[X skew](https://developer.mozilla.org/en-US/docs/Web/SVG/Attribute/transform#skewx)
(in degrees) to the tranform.
```
```{py:method} skew_y(angle)
Add a
[Y skew](https://developer.mozilla.org/en-US/docs/Web/SVG/Attribute/transform#skewy)
(in degrees) to the tranform.
```
````

The {py:mod}`tdoc.svg` module exports convenience functions with the same names
as the methods of {py:class}`Transform` that create a new {py:class}`Transform`
and add a transform to it.
