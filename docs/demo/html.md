<!-- Copyright 2024 Remy Blank <remy@c-space.org> -->
<!-- SPDX-License-Identifier: MIT -->

# HTML, CSS, JavaScript

The `{exec} html` block allows displaying a complete HTML document as an
`<iframe>`.

## Full document

The `<iframe>` defaults to a 16/9 aspect ratio, but its size can be adjusted
with `:output-style:`.

```{exec} html
:when: load
:editable:
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

## Partial document

Browsers are smart enough to render `<iframe>` tags with partial content
correctly. So an `{exec} html` block can contain an HTML snippet only, and
optionally styles (with a `<style>` element):

```{exec} html
:when: load
:editable:
:output-style: height: 7rem
<style>
h1 { margin: 0; font-size: 5rem; }
</style>
<h1>Hello, world!</h1>
```

Or scripts (with a `<script>` element):

```{exec} html
:when: load
:editable:
:output-style: height: 3rem
Please click <button>here</button>
<script>
document.querySelector('button')
  .addEventListener('click', () => alert('Click!'));
</script>
```

