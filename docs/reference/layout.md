% Copyright 2025 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Layout

## Spacing

````{rst:role} hspace
This role inserts a `<span>` with `display: inline-block`, and sets the content
of the role as the element's `width:` property. The content must include a
[length unit](https://developer.mozilla.org/en-US/docs/Web/CSS/length), e.g.
`em`.

```{code-block}
The quick brown fox {hspace}`3em` jumps over {hspace}`3em` the lazy dog.
```
````

````{rst:role} vspace
This role inserts a `<span>` with `display: block`, and sets the content of the
role as the element's `height:` property. The content must include a
[length unit](https://developer.mozilla.org/en-US/docs/Web/CSS/length), e.g.
`lh` to specify a number of lines.

```{code-block}
Calculate the sum of the integers from 1 to 10.
{vspace}`3lh`
Calculate the product of the integers from 1 to 10.
{vspace}`3lh`
```
````

## Leader

````{rst:role} leader
This role adds a leader line. The content of the role is the character to use
for the leader line, optionally followed by `|` and the width of the leader
(including a
[length unit](https://developer.mozilla.org/en-US/docs/Web/CSS/length)). If no
width is given, the leader extends until the end of the line.

```{code-block}
$2 + 3 =$ {leader}`.`

The quick brown {leader}`_|6em` jumps over the {leader}`_|6em` dog.

Give an example.
{leader}`.|100%`{leader}`.|100%`{leader}`.|100%`
```

The stylesheet supports `.`, `_` and `dot` (dot leader). To add support for
other characters, e.g. `*`, define a CSS rule like the following, with the
`contents:` property value long enough to exceed the page width.

```{code-block}
.tdoc-leader.c\*::after {
  content: "****************************************************************"
           "****************************************************************"
           "****************************************************************"
           "****************************************************************";
}
```
````

## Numbering

````{rst:role} num
This role performs automatic numbering across all documents, optionally creating
reference targets. The role content is either a label (e.g. `` {num}`label` ``)
or an explicit title and a label (e.g. `` {num}`Exercise %s<label>` ``). In the
latter case, the title must contain the string `%s`, which gets substituted with
the number.

The label is composed of a counter identifier and an optional target name,
separated by `:`. Distinct identifiers are numbered separately, and the counters
persist across pages. Instances with a target (e.g. `` {num}`ex:target` ``) can
be referenced with the {rst:role}`numref` role (e.g. `` {numref}`ex:target` ``).

```{code-block}
## Exercise {num}`ex:intro`

As an introduction to ...

## Exercise {num}`ex`

After completing {numref}`exercise %s<ex:intro>`, ...
```
````

````{rst:role} num1
This role is identical to {rst:role}`num`, but the numbering is per first-level
page name prefix. For example, numbering is continous across the pages
`abc/page1` and `abc/page2`, but is reset for `def/page3`.
````

````{rst:role} num2
This role is identical to {rst:role}`num`, but the numbering is per second-level
page name prefix. For example, numbering is continous across the pages
`abc/def/page1` and `abc/def/page2`, but is reset for `abc/ghi/page3`.
````

````{rst:role} nump
This role is identical to {rst:role}`num`, but the numbering is per page.
````

## Points

`````{rst:role} points
This role specifies a number of points, typically for an exercise or an exam
question. The content of the role is structured as follows:

- A points value, as a floating-point number.
- Optionally, a `!` following the value to indicate that the value should not be
  included in the sum of points. The points value is enclosed in parentheses in
  the points table. This is typically used for bonus questions.
- Optionally, a `:` followed by a label
  [format string](https://docs.python.org/3/library/string.html#formatstrings).
  A single argument is provided for formatting: the value of a {rst:role}`num`
  role located at the same level as the {rst:role}`points` role, typically a
  heading, or the empty string if there is none. The default is `"{0}"`.

The points values can be collected into a {rst:dir}`flex-table` with
`:class: points`. Cells with `points=` attributes are substituted with cells
derived from the {rst:role}`points` roles. The following attribute values are
supported:

- `points=label`: Replace the cell with a list of cells containing the labels
  of the points values.
- `points=value`: Replace the cell with a list of cells containing the formatted
  points values.
- `points=empty`: Replace the cell with a list of empty cells, one for each
  points value.
- `points=sum`: Replace the cell with a cell containing the formatted sum of the
  points values, excluding those postfixed with `!`.

````{code-block}
```{flex-table}
:class: points grid
{t=h}|{.l}Exercise    |{points=label}|Total
{t=b}|{t=h .l}Points  |{points=value}|{points=sum}
     |{t=h .l}Obtained|{points=empty}|
```

## Exercise {nump}`ex:intro`{points}`2`

Calculate...

## Exercise {nump}`ex`{points}`3`

Prove that...

## Bonus {nump}`bonus`{points}`1!:Bonus {0}`

Explain how...
````

The points values are formatted using
[format strings](https://docs.python.org/3/library/string.html#formatstrings)
specified in {rst:dir}`metadata`.

- `points:format:`: A format string to format a {py:class}`float` value. The
  default is `"{0:.3g}"`.
- `points:text:` A single or a pair of format strings to format the text that is
  substituted for the {rst:role}`points` roles. When a pair is provided, the
  first element is used when the points value is `1` (singular), and the second
  is used for all other values (plural). The default is
  `[" ({0} point)", " ({0} points)"]`.
`````

## Grid

`````{rst:directive} .. list-grid::
This directive creates a
[CSS grid layout](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_grid_layout)
([guide](https://css-tricks.com/snippets/css/complete-guide-grid/)). The
geometry of the grid is defined in the {rst:dir}`:style: <list-grid:style>`
option, e.g. with the `grid-template-columns` property. The content of the
directive must be a bullet list, and each item is assigned to a grid cell, from
left to right and from top to bottom.

{.rubric}
Options
```{rst:directive:option} cell-style: property: value; [property: value; ...]
CSS styles to apply to the grid cell elements.
```
```{rst:directive:option} class: name [name...]
:type: IDs
A space-separated list of CSS classes to add to the grid container element.
```
```{rst:directive:option} style: property: value; [property: value; ...]
CSS styles to apply to the grid container element.
```
`````

## Block

````{rst:directive} .. block:: type
This directive is a container for arbitrary markdown. Its content isn't rendered
in the location where it is defined, but is instead moved to the
{rst:dir}`blocks` directive with the same type on the page.

The typical use case is defining the solutions to exercises next to their
exercise in the source document, and rendering them in a separate section.
````

````{rst:directive} .. blocks:: type
This directive renders the content of all the {rst:dir}`block` directives of the
given type on the page, in the order in which they appear in the source
document. Each {rst:dir}`block` directive is rendered as a separate section,
using the same section heading as the section containing the {rst:dir}`block`
directive.

{.rubric}
Options
```{rst:directive:option} class: name [name...]
:type: IDs
A space-separated list of CSS classes to add to the rendered block sections.
```
````
