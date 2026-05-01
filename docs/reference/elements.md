% Copyright 2024 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Elements

```{role} py(code)
:language: python
```

## Solution

````{rst:directive} .. solution:: [title]
This directive adds an admonition of type `solution`. The title defaults to
"Solution", and the body is collapsed by default. The solution can be toggled by
clicking on the title bar. Holding {kbd}`Ctrl` while clicking toggles all
admonitions on the page.

The `solutions:` key in the document {rst:dir}`metadata` controls how solutions
are displayed.

- `dynamic` (default): Solutions are hidden by default, but can be made visible
  to everyone in real-time by members of the group `solutions:show` using the
  <button class="tdoc fa-eye"></button> /
  <button class="tdoc fa-eye-slash"></button> button.
- `show`: Solutions are shown on the page.
- `hide`: Solutions are hidden when the page loads. They can be shown or hidden
  with the <button class="tdoc fa-eye"></button> /
  <button class="tdoc fa-eye-slash"></button> button in the navbar.

{.rubric}
Options
```{rst:directive:option} class: name [name...]
:type: IDs
A space-separated list of CSS classes to add to the admonition. The default is
`note dropdown`.
```
```{rst:directive:option} name: name
:type: ID
A reference target for the admonition.
```
```{rst:directive:option} expand
When set, the admonition is expanded by default.
```
```{rst:directive:option} show
When set, the admonition is always shown, even if solutions are hidden or
removed.
```
````

## IFrame

`````{rst:directive} .. iframe:: url
This directive adds an
[`<iframe>`](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/iframe)
element loading the given URL.

{.rubric}
Options
````{rst:directive:option} allow: directive; [directive; ...]
The
[permission policy](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/iframe#allow)
for the `<iframe>`{l=html}
([supported directives](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Permissions-Policy#directives)).
The default is:

```
autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture;
  screen-wake-lock; web-share
```
````

```{rst:directive:option} class: name [name...]
:type: IDs
A space-separated list of CSS classes to add to the `<iframe>`{l=html}.
```
```{rst:directive:option} credentialful
Indicate that the `<iframe>`{l=html} should **not** be loaded in
[credentialless](https://developer.mozilla.org/en-US/docs/Web/Security/IFrame_credentialless) mode. The default is credentialless mode.
```
```{rst:directive:option} referrerpolicy: value
Indicate the referrer to send when fetching the `<iframe>`{l=html} source
([supported values](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/iframe#referrerpolicy)).
```
```{rst:directive:option} sandbox: token [token ...]
Control the restrictions applied to the content embedded in the
`<iframe>`{l=html}
([supported tokens](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/iframe#sandbox)).
```
```{rst:directive:option} style: property: value; [property: value; ...]
CSS styles to apply to the `<iframe>`{l=html}, e.g. `width: 80%;`.
```
```{rst:directive:option} title: text
A concise description of the content of the `<iframe>`{l=html}, typically used
by assistive technologies.
```
`````

````{rst:directive} .. youtube:: id
This directive adds an
[`<iframe>`](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/iframe)
element loading a YouTube video. The argument is the ID of the video, e.g.
`aVwxzDHniEw`. All the options of {rst:dir}`iframe` are supported.
````

## Table

`````{rst:directive} .. flex-table::
This directive defines an HTML `<table>`{l=html} using a more flexible syntax
than Markdown tables or other table directives. In particular, it allows
assigning CSS classes to individual rows and cells, and allows cells to span
multiple rows and / or columns. The directive content defines the content of the
table, using the following syntax:

- Each line of the directive content defines a row.
- Each cell in a row starts with a `|` character.
- A row can optionally start with
  [attributes](https://myst-parser.readthedocs.io/en/latest/syntax/optional.html#attributes)
  that are applied to the row. In addition to classes and identifiers, the
  following attributes are recognized:
  - `t`: Determines if the row is a header row (`h`) or a body row (`b`).
    Consecutive header rows are grouped in a `<thead>`{l=html}, while body rows
    are grouped in a `<tbody>`{l=html}. Rows that don't specify a type use the
    type of the previous row. The default for the first row is `b`.
- The content of a cell can optionally start with
  [attributes](https://myst-parser.readthedocs.io/en/latest/syntax/optional.html#attributes)
  that are applied to the cell. In addition to classes and identifiers, the
  following attributes are recognized:
  - `cols`: Sets the `colspan` attribute of the cell tag.
  - `rows`: Sets the `rowspan` attribute of the cell tag.
  - `t`: Determines if the cell is a heading cell (`h`) or a data cell (`d`).
    Heading cells are rendered as `<th>`{l=html}, and data cells are rendered as
    `<td>`{l=html}. Cells that don't specify a type default to `h` in header
    rows and `d` in body rows.
- The cell content is parsed as inline markup, i.e. it can include styling,
  inline math, etc. `|` characters within the cell content must be escaped as
  `\|`.

````{code-block}
```{flex-table}
{t=h}|Name|Age|Shoe size
{t=b}|{t=h}Joe|23|43
     |{t=h}Jack|18|41
     |{t=h}Jim|{cols=2}unknown
```
````

Tables have no styling by default, but the following classes are set up in the
stylesheet and can be used in the {rst:dir}`:class: <flex-table:class>` option.

- `grid`: Formats the table as a grid, using a `1px` solid border on all cells.
  The following classes can be set on table cells:
  - `.l`: Aligns the cell content to the left.
  - `.r`: Aligns the cell content to the right.
- `function-table`: Formats the table as a function value and / or sign table.
  The following classes can be set on table cells:
  - `.l`: Aligns the cell content to the left.
  - `.r`: Aligns the cell content to the right.
  - `.g`: Applies a grey background to the cell. Typically used where the
    function is undefined.
  - `.w`: Sets `min-width: 5rem` on the cell.

{.rubric}
Options
```{rst:directive:option} class: name [name...]
:type: IDs
A space-separated list of CSS classes to add to the `<table>`{l=html}.
```
```{rst:directive:option} name: name
:type: ID
A reference target for the table.
```
`````
