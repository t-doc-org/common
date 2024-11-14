% Copyright 2024 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Release notes

(release-0-18)=
## 0.18

- Added the `youtube` and `iframe` directives.
- Removed the dependency on `sphinx_togglebutton`.

(release-0-17)=
## 0.17

- Added the `solution` directive and the "Toggle solutions" navbar button.
- Fixed the flickering on page load due to `sphinx_togglebutton`.
- Added an option to exclude files from watching in the dev server.

(release-0-16)=
## 0.16

- Added support for `{exec} html`.
- Added support for styling editors and output blocks with `{exec} :style:` and
  `{exec} :output-style:`.
- Added the `metadata` directive.
- The rendered HTML output is now fully self-contained.

(release-0-15)=
## 0.15

- Added a mechanism to render arbitrary HTML from `{exec} python` blocks.
- Added a Python module to create SVG images.
- Added automatic focusing of `{exec} python` text input elements.
- Fixed the positioning of the "Remove" button on scrollable tables.

(release-0-14)=
## 0.14

- Added a button to remove `{exec}` output.
- Fixed `{exec} :linenos:`.

(release-0-13)=
## 0.13

- Added support for executing blocks after a block with `{exec} :then:`.

(release-0-12)=
## 0.12

- Added user input functionality for `{exec} python` blocks.

(release-0-11)=
## 0.11

- `{exec} python` now works when offline.
- Fixed an issue that prevented entering the character `/` in editors.
- Disabled the search shortcut, as it can interfere with editors.
- Made the workaround for missing `SharedArrayBuffer` configurable.
  - By default, no workaround is installed, and Polyscript seems to work fine.
  - Cross-origin isolation can be enabled, but this breaks `<iframe>` tags.
  - Alternatively, a [Sabayon](https://github.com/WebReflection/sabayon) service
    worker can be installed.

(release-0-10)=
## 0.10

- Added initial support for `{exec} python`.
  - Currently, Python code execution only works when online.
- Made the automatic page reloading more reactive.
- Made pages cross-origin isolated even if the server doesn't set the
  appropriate headers.

```{admonition} Warning
:class: warning
**This release breaks `<iframe>` tags in documents.** On Chrome, setting the
`credentialless` attribute on the `<iframe>` tags fixes the issue, but Firefox
and Safari don't support it (yet).
```

(release-0-9)=
## 0.9

- Added automatic page reloading on successful builds in the dev server.
- Fixed encoding issues with `{exec} :include:`.

(release-0-8)=
## 0.8

- Allowed multiple references in `{exec} :after:`.
- Added support for including external files with `{exec} :include:`.

(release-0-7)=
## 0.7

- Fine-tuned the `exec` control buttons.

(release-0-6)=
## 0.6

- Added support for editable blocks with `{exec} :editable:`.

(release-0-5)=
## 0.5

- Added on-click execution of `exec` blocks.
- Added support for dependencies with `{exec} :after:`.
- Added proper rendering of SQL errors in `{exec} sql`.
- Fixed the handling of `NULL` values in `{exec} sql`.

(release-0-4)=
## 0.4

- Added checking for updates in the dev server.
- Added install, use and development documentation.

(release-0-3)=
## 0.3

- Added automatic rebuilding on source file changes in the dev server.

(release-0-2)=
## 0.2

- First public release.
