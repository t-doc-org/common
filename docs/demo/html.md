<!-- Copyright 2024 Remy Blank <remy@c-space.org> -->
<!-- SPDX-License-Identifier: MIT -->

# HTML, CSS, Javascript

The `{exec} html` block allows displaying complete HTML documents within a page,
as `<iframe>` blocks.

```{exec} html
:when: load
:editable:
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
</body>
</html>
```
