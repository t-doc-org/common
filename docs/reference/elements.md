% Copyright 2024 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Elements

## Document metadata

````{rst:directive} .. metadata::
This directive allows adding document metadata to a page. The content of the
directive is a [YAML](https://yaml.org/) document which is converted to a Python
{py:class}`dict` and merged into the document metadata.

In addition to Sphinx-specific
[metadata fields](https://www.sphinx-doc.org/en/master/usage/restructuredtext/field-lists.html#special-metadata-fields), the following top-level keys are
interpreted.

`date`
: The date to use in headers and footers when printing. Defaults to the current
  date.

`exec`
: A map of per-language configuration for client-side code execution.

  ```{code-block} yaml
  exec:
    python:
      packages: [sqlite3]
  ```

`mathjax`
: A map of
  [MathJax configuration](https://docs.mathjax.org/en/stable/web/configuration.html)
  overrides.

  `output`
  : The default output processor (`chtml`, `svg`). The default is `svg`.

`mermaid`
: A map of config properties for {rst:dir}`mermaid` diagrams.

`page-break-avoid`
: A level or list of levels of sections in which page breaks should be avoided.

`page-break-force`
: A level or list of levels of sections after which a page break should be
  forced.

`print-styles`
: A CSS stylesheet URL to use when printing. Relative URLs are resolved relative
  to the `_static` directory. The following print stylesheets are provided:

  - `tdoc/print.css`
    - Header, left: The value of the `subject` metadata.
    - Header, right: The first-level title of the document.
    - Footer, left: The site author.
    - Footer, center: The page number and the total number of pages.
    - Footer, right: The value of the `date` metadata.
  - `tdoc/print-exam.css`
    - Header, left: The value of the `subject` metadata.
    - Header, center: The first-level title of the document.
    - Header, right: The value of the `date` metadata.
    - Footer, left: The site author.
    - Footer, center: The page number and the total number of pages.

`scripts`
: A list of scripts to reference from the page header through `<script>`{l=html}
  elements. The list items can be either strings (the URL of the script) or
  maps. For maps, the `src` key specifies the URL of the script, and other keys
  are added to the `<script>`{l=html} element. Relative URLs are resolved
  relative to the `_static` directory.

  ```{code-block} yaml
  scripts:
    - classic-script.js
    - src: module-script.js
      type: module
    - https://code.jquery.com/jquery-3.7.1.min.js
  ```

`styles`
: A list of CSS stylesheets to reference from the page header through
  `<link>`{l=html} elements. The list items can be either strings (the URL of
  the stylesheet) or maps. For maps, the `src` key specifies the URL of the
  stylesheet, and other keys are added to the `<link>`{l=html} element. Relative
  URLs are resolved relative to the `_static` directory.

  ```{code-block} yaml
  styles:
    - custom-styles.css
    - src: print-styles.css
      media: print
    - https://example.com/styles.css
  ```

`subject`
: The subject covered by the document. This may be used by print stylesheets in
  headers or footers.

`versions`
: A map overriding the versions of JavaScript dependencies on a page. The keys
  are dependency identifiers and the values can be either version numbers or
  full URLs. See
  [`deps.py`](https://github.com/t-doc-org/common/blob/main/tdoc/common/deps.py)
  for the list of dependencies and their default version.

  ```{code-block} yaml
  versions:
    polyscript: 0.17.30
    pyodide: https://cdn.jsdelivr.net/pyodide/v0.27.7/full
  ```
````

## Default directive options

`````{rst:directive} .. defaults:: directive
This directive sets default options for a directive type for the current
document, starting from the current location. All directives of the given type
that follow the {rst:dir}`defaults` block take their default option values from
that block. Options that are specified in the directive itself override the
default.

A document can contain multiple {rst:dir}`defaults` blocks for the same
directive type. Each occurrence replaces the previous one, i.e. they don't
combine.

````{code-block}
```{exec} python
# Use the directive's default options
```

```{defaults} exec
:when: load
:class: hidden
```

```{exec} python
# Use ':when: load' and ':class: hidden'
```

```{exec} python
:when: click
# Use ':when: click' and ':class: hidden'
```

```{defaults} exec
:when: never
```

```{exec} python
# Use ':when: never' and no :class:
```
````
`````

## Solution

````{rst:directive} .. solution:: [title]
This directive adds an admonition of type `solution`. The title defaults to
"Solution", and the body is collapsed by default. The solution can be toggled by
clicking on the title bar. Holding {kbd}`Ctrl` while clicking toggles all
admonitions on the page.

The `solutions:` key in the [document metadata](#document-metadata) controls how
solutions are displayed.

- `show` (default): Solutions are shown on the page.
- `hide`: Solutions are hidden when the page loads. They can be shown or hidden
  with the <button class="tdoc fa-eye"></button> /
  <button class="tdoc fa-eye-slash"></button> button in the navbar.
- `dynamic`: Solutions are hidden by default, but can be made visible to
  everyone in real-time by members of the group `solutions:show` using the
  <button class="tdoc fa-eye"></button> /
  <button class="tdoc fa-eye-slash"></button> button.

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
