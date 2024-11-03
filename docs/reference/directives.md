% Copyright 2024 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Directives

## Document metadata

````{rst:directive} .. {metadata}::
This directive allows adding document metadata to a page. The content of the
directive is a [YAML](https://yaml.org/) document which is converted to a Python
{py:class}`dict` and merged into the document metadata.

In addition to Sphinx-specific
[metadata fields](https://www.sphinx-doc.org/en/master/usage/restructuredtext/field-lists.html#special-metadata-fields), the following top-level keys are
interpreted.

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

## Code execution

See "[Code execution](exec)`.
