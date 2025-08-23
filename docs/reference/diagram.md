% Copyright 2025 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Diagrams

## Mermaid

``````{rst:directive} .. mermaid::
This directive creates a diagram based on [Mermaid](https://mermaid.js.org/).
The content of the directive is a diagram description in Mermaid's
[diagram syntax](https://mermaid.js.org/intro/syntax-reference.html).

Diagrams can be configured and styled using
[config properties](https://mermaid.js.org/config/schema-docs/config.html).
The properties can be set via the following mechanisms, with specific mechanisms
overriding more general ones.

- A
  [frontmatter](https://mermaid.js.org/intro/syntax-reference.html#frontmatter-for-diagram-code)
  block in the directive content sets properties for a single diagram.

  `````{note}
  Only the `---` line separating the frontmatter from the diagram code must be
  included; the `---` line preceding the frontmatter must be dropped.

  ````{code-block}
  ```{mermaid}
  title: A simple graph
  config:
    theme: forest
  ---
  flowchart TD;
    A --> B;
    A --> C;
    B --> D;
    C --> D;
  ```
  ````
  `````
- The `mermaid:` {rst:dir}`metadata` sets the default properties for the page.
- The `tdoc_mermaid` setting in `conf.py` (a `dict`) sets the default properties
  for the site.

{.rubric}
Options
```{rst:directive:option} class: name [name...]
:type: IDs
A space-separated list of CSS classes to add to the diagram container.
```
```{rst:directive:option} style: property: value; [property: value; ...]
CSS styles to apply to the diagram container.
```
``````
