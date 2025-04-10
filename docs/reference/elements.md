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

`exec`
: A mapping of per-language configuration for client-side code execution.

  ```{code-block} yaml
  exec:
    python:
      packages: [sqlite3]
  ```

`scripts`
: A list of scripts to reference from the page header through `<script>`
  elements. The list items can be either strings (the URL of the script) or
  maps. For maps, the `src` key specifies the URL of the script, and other keys
  are added to the `<script>` element. Relative URLs are resolved relative to
  the `_static` directory.

  ```{code-block} yaml
  scripts:
    - classic-script.js
    - src: module-script.js
      type: module
    - https://code.jquery.com/jquery-3.7.1.min.js
  ```

`styles`
: A list of CSS stylesheets to reference from the page header through `<link>`
  elements. The list items can be either strings (the URL of the stylesheet) or
  maps. For maps, the `src` key specifies the URL of the stylesheet, and other
  keys are added to the `<link>` element. Relative URLs are resolved relative to
  the `_static` directory.

  ```{code-block} yaml
  styles:
    - custom-styles.css
    - src: print-styles.css
      media: print
    - https://example.com/styles.css
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
"Solution", and the body is collapsed by default.

The `solutions:` key in the [document metadata](#document-metadata) controls how
solutions are displayed.

- `show` (default): Solutions are shown on the page.
- `hide`: Solutions are hidden when the page loads. They can be shown or hidden
  by clicking the "Toggle solutions" (<span class="tdoc-icon fa-eye"></span> /
  <span class="tdoc-icon fa-eye-slash"></span>) button in the navbar.
- `remove`: Solutions are removed from the page altogether. When using the local
  server, this option behaves like `solutions: hide`.

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

## IFrames

````{rst:directive} .. youtube:: id
This directive adds an
[`<iframe>`](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/iframe)
element loading a YouTube video. The argument is the ID of the video, e.g.
`aVwxzDHniEw`. All the options of {rst:dir}`iframe` are supported.
````

`````{rst:directive} .. iframe:: url
This directive adds an
[`<iframe>`](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/iframe)
element loading the given URL.

{.rubric}
Options
````{rst:directive:option} allow: directive; [directive; ...]
The
[permission policy](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/iframe#allow)
for the `<iframe>`
([supported directives](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Permissions-Policy#directives)).
The default is:

```
autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture;
  screen-wake-lock; web-share
```
````

```{rst:directive:option} class: name [name...]
:type: IDs
A space-separated list of CSS classes to add to the `<iframe>`.
```
```{rst:directive:option} credentialful
Indicate that the `<iframe>` should **not** be loaded in
[credentialless](https://developer.mozilla.org/en-US/docs/Web/Security/IFrame_credentialless) mode. The default is credentialless mode.
```
```{rst:directive:option} referrerpolicy: value
Indicate the referrer to send when fetching the `<iframe>` source
([supported values](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/iframe#referrerpolicy)).
```
```{rst:directive:option} sandbox: token [token ...]
Control the restrictions applied to the content embedded in the `<iframe>`
([supported tokens](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/iframe#sandbox)).
```
```{rst:directive:option} style: property: value; [property: value; ...]
CSS styles to apply to the `<iframe>`, e.g. `width: 80%`.
```
```{rst:directive:option} title: text
A concise description of the content of the `<iframe>`, typically used by
assistive technologies.
```
`````

## Code execution

See "[](exec.md)".

## Numbering

````{rst:role} num
This role performs automatic numbering, optionally creating reference targets.
The role content is either a label (e.g. `` {num}`label` ``) or an explicit
title and a label (e.g. `` {num}`Exercise %s<label>` ``). In the latter case,
the title must contain the string `%s`, which gets substituted with the number.

The label is composed of a counter identifier and an optional target name,
separated by `:`. Distinct identifiers are numbered separately, and the counters
persist across pages. Instances with a target (e.g. `` {num}`ex:target` ``) can
be referenced with the {rst:role}`numref` role (e.g. `` {numref}`ex:target` ``).

```{code-block} md
## Exercise {num}`ex:intro`

As an introduction to ...

## Exercise {num}`ex`

After completing {numref}`exercise %s<ex:intro>`, ...
```
````
