% Copyright 2024 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# t-doc

This site describes the **documentation system** that forms the base of the
[t-doc.org](https://t-doc.org) site. It is distributed as a single Python package
([`t-doc-common`](https://pypi.org/project/t-doc-common/)) under the
[MIT](https://opensource.org/license/mit) license, and consists of the following
components:

- A **Sphinx theme** that fine-tunes the
  [Sphinx Book Theme](https://sphinx-book-theme.readthedocs.io/).
- A **Sphinx extension** that adds functionality through
  [roles and directives](reference/elements.md).
- A **[local server](edit.md#edit-documents)** that automatically rebuilds
  documents when their source changes.
- A **[automatic deployment system](edit.md#deploy-documents).** that builds
  sites and deploys them to [GitHub Pages](https://pages.github.com/) on every
  version control push.

t-doc builds on the following software:

- **[Sphinx](https://www.sphinx-doc.org/):** A documentation generation system.
- **[MyST](https://mystmd.org/):** A
  [Markdown](https://en.wikipedia.org/wiki/Markdown) flavor for technical and
  scientific communication and publication.
- **[MyST Parser](https://myst-parser.readthedocs.io/):** A Sphinx extension to
  parse MyST source documents.
- **[Sphinx Book Theme](https://sphinx-book-theme.readthedocs.io/):** A theme
  with a modern book-like look and feel, based on the
  [PyData Sphinx Theme](https://pydata-sphinx-theme.readthedocs.io/).
- **[Sphinx Design](https://sphinx-design.readthedocs.io/):** A Sphinx extension
  for screen-size responsive web components.
- **[MathJax](https://www.mathjax.org/):** A display engine for mathematics.
- **[CodeMirror](https://codemirror.net/):** A code editor component.
- **[Pyodide](https://pyodide.org/):** A Python distribution for the browser
  based on [WebAssembly](https://webassembly.org/), integrated through
  [Polyscript](https://pyscript.github.io/polyscript/).
- **[SQLite WASM](https://sqlite.org/wasm/):** A build of
  [SQLite](https://sqlite.org/) to [WebAssembly](https://webassembly.org/) that
  enables the use of SQLite in the browser.

A huge thank you to the developers and maitainers of these packages, for
building awesome software and making it available for free!

## Navigation

```{toctree}
:maxdepth: 1
install
edit
development
reference/index
demo/index
```
