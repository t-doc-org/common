% Copyright 2024 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# HTML, CSS, JavaScript

```{metadata}
styles:
  - demo-html-styles.css
scripts:
  - src: demo-html-script.js
    type: module
```

## Inline document

The [`{exec} html`](../reference/exec.md#html) directive allows displaying a
complete HTML document as an `<iframe>`. The `<iframe>` defaults to a 16/9
aspect ratio, but its size can be adjusted with
{rst:dir}`:output-style: <exec:output-style>`.

```{exec} html
:when: load
:editor:
:style: height: 14rem
<!DOCTYPE html>
<html lang="en">
<head>
<style>
h1 { margin: 0; font-size: 3rem; }
</style>
<script>
document.addEventListener('DOMContentLoaded', () => {
  document.querySelector('h1').appendChild(document.createTextNode('world!'));
});
</script>
</head>
<body>
  <h1>Hello, </h1>
  <p>A link to <a href="https://t-doc.org/">this site</a>.
</body>
</html>
```

### Partial content

Browsers are smart enough to render `<iframe>` tags with partial content
correctly. So an [`{exec} html`](../reference/exec.md#html) block can specify
just an HTML snippet, and optionally styles (with a `<style>` element):

```{exec} html
:when: load
:editor:
:output-style: height: 7rem
<style>
h1 { margin: 0; font-size: 5rem; }
</style>
<h1>Hello, world!</h1>
```

Or scripts (with a `<script>` element):

```{exec} html
:when: load
:editor:
:output-style: height: 3rem
Please click <button>here</button>
<script>
document.querySelector('button')
  .addEventListener('click', () => alert('Click!'));
</script>
```

## Web application

Markdown already allows adding arbitrary HTML. Page-specific stylesheets and
scripts can be added with the `styles` and `scripts` entries of a
{rst:dir}`metadata` directive.

<div class="tdoc-web-app">
  Please click <button>here</button> (count: <span>0</span>)
</div>
