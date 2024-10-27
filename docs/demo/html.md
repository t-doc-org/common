<!-- Copyright 2024 Remy Blank <remy@c-space.org> -->
<!-- SPDX-License-Identifier: MIT -->

# HTML, CSS, Javascript

The `{exec} html` block allows displaying a complete HTML document, as an
`<iframe>`.

```{exec} html
:when: load
:editable:
:style: height: 14rem
<!DOCTYPE html>
<html lang="en">
<head>
<style>
h1 { margin: 0; font-size: 3em; }
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
