% Copyright 2024 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Release notes

(release-0-50)=
## 0.50 *(2025-06-22)*

- Integrated table-based dynamic quizzes into the {rst:dir}`quiz` directive.
- Fixed an issue with line numbers in tracebacks in
  [`{exec} micropython`](/reference/exec.md#micropython).
- [Full changelog](https://github.com/t-doc-org/common/compare/0.49...0.50)

(release-0-49)=
## 0.49 *(2025-06-14)*

- Renamed "quizz" to "quiz" everywhere. English is hard.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.48...0.49)

(release-0-48)=
## 0.48 *(2025-06-13)*

- Added the {rst:dir}`quiz` directive and associated roles to create interactive
  quizzes.
- Reduced the latency of database change notifications, to make them practically
  instantaneous.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.47...0.48)

(release-0-47)=
## 0.47 *(2025-05-25)*

- Added the {rst:dir}`poll` directive to perform live audience polls.
- Improved the performance of incremental rebuilds.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.46...0.47)

(release-0-46)=
## 0.46 *(2025-05-20)*

- Fixed the rendering of {rst:role}`numref` references to {rst:role}`num` roles.
- Added automatic store upgrades.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.45...0.46)

(release-0-45)=
## 0.45 *(2025-05-17)*

- Made automatic rebuilds in the dev server incremental. This significantly
  speeds up the edit-view loop.
- **This release breaks the rendering of {rst:role}`numref` references to
  {rst:role}`num` roles.** The links are correct, but their numbering is wrong.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.44...0.45)

(release-0-44)=
## 0.44 *(2025-05-16)*

- Added a config value to set the default solution visibility.
- Fixed an internal error in unauthenticated API requests.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.43...0.44)

(release-0-43)=
## 0.43 *(2025-05-15)*

- Added dynamic control of the visibility of solutions.
- Added support for user authentication.
- Added an event streaming API to enable more dynamic pages.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.42...0.43)

(release-0-42)=
## 0.42 *(2025-04-21)*

- Added a visual indication that editor content is unchanged.
- Added a mechanism to show removed solutions.
- Prepared for per-site subdomains.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.41...0.42)

(release-0-41)=
## 0.41 *(2025-04-13)*

- Added functionality to draw over page content.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.40...0.41)

(release-0-40)=
## 0.40 *(2025-04-11)*

- Added a metadata setting to remove the content of {rst:dir}`solution`
  directives from the output.
- Added an option to open the site in a browser when running the local server.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.39...0.40)

(release-0-39)=
## 0.39 *(2025-03-20)*

- Added table-based quiz generation functionality.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.38...0.39)

(release-0-38)=
## 0.38 *(2025-03-01)*

- Added a menu entry to read `main.py` in
  [`{exec} micropython`](/reference/exec.md#micropython).
- Simplified math typesetting in quiz prompts.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.37...0.38)

(release-0-37)=
## 0.37 *(2025-02-21)*

- Added support for programming MicroPython devices through
  [`{exec} micropython`](/reference/exec.md#micropython).
- [Full changelog](https://github.com/t-doc-org/common/compare/0.36...0.37)

(release-0-36)=
## 0.36 *(2025-02-13)*

- Improved command-line option parsing.
- Moved the check for upgrades to the `run.py` script.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.35...0.36)

(release-0-35)=
## 0.35 *(2025-02-06)*

- Simplified the generation of color output on the terminal.
- Refactored internals to enable running single-file scripts within the venv.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.34...0.35)

(release-0-34)=
## 0.34 *(2025-02-02)*

- Enabled loading packages for [`{exec} python`](/reference/exec.md#python)
  blocks.
  - Bundled the `micropip`, `packaging` and `sqlite3` packages.
- Enabled calling `async` functions synchronously on Chrome-based browsers.
- Added {py:func}`tdoc.core.input`.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.33...0.34)

(release-0-33)=
## 0.33 *(2025-01-25)*

- Fixed the breakage in CLI sub-commands.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.32...0.33)

(release-0-32)=
## 0.32 *(2025-01-25)*

- Made it simpler to run a local server with a store.
- Added a script to test all document repositories.
- **This release breaks certain CLI sub-commands.**
- [Full changelog](https://github.com/t-doc-org/common/compare/0.31...0.32)

(release-0-31)=
## 0.31 *(2025-01-12)*

- Added the t-doc version in the content footer.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.30...0.31)

(release-0-30)=
## 0.30 *(2025-01-12)*

- Finalized the auto-install and upgrade functionality.
- On Windows, made the `run.py` script pause on termination due to an exception,
  so that the console window doesn't close immediately.
- Enabled development in an isolated virtual environment.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.29...0.30)

(release-0-29)=
## 0.29 *(2025-01-09)*

- Added a wrapper script for the `tdoc` command to auto-install and upgrade
  `t-doc-common`.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.28...0.29)

(release-0-28)=
## 0.28 *(2025-01-09)*

- Fixed an issue with missing `_static` directories.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.27...0.28)

(release-0-27)=
## 0.27 *(2025-01-03)*

- Added packaging of Python modules in the `_python` directory.
- Added {py:func}`tdoc.core.redirect` to redirect `stdout` / `stderr`.
- Fixed the overflow of wide non-editable {rst:dir}`exec` blocks.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.26...0.27)

(release-0-26)=
## 0.26 *(2024-12-27)*

- Added quiz functionality.
- Fixed issues with non-ID characters in {rst:dir}`{exec} :after: <exec:after>`
  and {rst:dir}`{exec} :then: <exec:then>`.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.25...0.26)

(release-0-25)=
## 0.25 *(2024-12-15)*

- Made editor IDs globally unique, to allow moving across documents.
- Made the "Toggle solutions" button conditional on the presence of solutions.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.24...0.25)

(release-0-24)=
## 0.24 *(2024-12-14)*

- Enabled saving the content of editors to browser local storage and restoring
  it on reload.
- Renamed `{exec} :editable:` to {rst:dir}`{exec} :editor: <exec:editor>`.
- Added links to the documentation of major dependencies.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.23...0.24)

(release-0-23)=
## 0.23 *(2024-12-07)*

- Converted the dev server to WSGI.
- Added support for a backend store to the dev server.
- Fixed more cosmetic issues with collapsed admonitions.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.22...0.23)

(release-0-22)=
## 0.22 *(2024-11-26)*

- Added some basic cryptographic helpers for secret management.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.21...0.22)

(release-0-21)=
## 0.21 *(2024-11-23)*

- Added the {rst:dir}`defaults` directive.
- Fixed a cosmetic issue with collapsed admonitions.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.20...0.21)

(release-0-20)=
## 0.20 *(2024-11-21)*

- Added the {rst:role}`num` role.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.19...0.20)

(release-0-19)=
## 0.19 *(2024-11-17)*

- Fixed the un-collapsing of admonitions through click events.
- Fixed the full-screen mode of [`{exec} html`](/reference/exec.md#html).
- [Full changelog](https://github.com/t-doc-org/common/compare/0.18...0.19)

(release-0-18)=
## 0.18 *(2024-11-14)*

- Added the {rst:dir}`youtube` and {rst:dir}`iframe` directives.
- Removed the dependency on `sphinx_togglebutton`.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.17...0.18)

(release-0-17)=
## 0.17 *(2024-11-09)*

- Added the {rst:dir}`solution` directive and the "Toggle solutions" navbar
  button.
- Fixed the flickering on page load due to `sphinx_togglebutton`.
- Added an option to exclude files from watching in the dev server.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.16...0.17)

(release-0-16)=
## 0.16 *(2024-11-03)*

- Added support for [`{exec} html`](/reference/exec.md#html).
- Added support for styling editors and output blocks with
  {rst:dir}`{exec} :style: <exec:style>` and
  {rst:dir}`{exec} :output-style: <exec:output-style>`.
- Added the {rst:dir}`metadata` directive.
- The rendered HTML output is now fully self-contained.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.15...0.16)

(release-0-15)=
## 0.15 *(2024-10-19)*

- Added a mechanism to render arbitrary HTML from
  [`{exec} python`](/reference/exec.md#python) blocks.
- Added a Python module to create SVG images.
- Added automatic focusing of [`{exec} python`](/reference/exec.md#python) text
  input elements.
- Fixed the positioning of the "Remove" button on scrollable tables.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.14...0.15)

(release-0-14)=
## 0.14 *(2024-10-03)*

- Added a button to remove {rst:dir}`{exec} <exec>` output.
- Fixed `{exec} :linenos:`.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.13...0.14)

(release-0-13)=
## 0.13 *(2024-09-29)*

- Added support for executing blocks after a block with
  {rst:dir}`{exec} :then: <exec:then>`.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.12...0.13)

(release-0-12)=
## 0.12 *(2024-09-28)*

- Added user input functionality for
  [`{exec} python`](/reference/exec.md#python) blocks.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.11...0.12)

(release-0-11)=
## 0.11 *(2024-09-27)*

- [`{exec} python`](/reference/exec.md#python) now works when offline.
- Fixed an issue that prevented entering the character `/` in editors.
- Disabled the search shortcut, as it can interfere with editors.
- Made the workaround for missing `SharedArrayBuffer` configurable.
  - By default, no workaround is installed, and Polyscript seems to work fine.
  - Cross-origin isolation can be enabled, but this breaks `<iframe>` tags.
  - Alternatively, a [Sabayon](https://github.com/WebReflection/sabayon) service
    worker can be installed.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.10...0.11)

(release-0-10)=
## 0.10 *(2024-09-21)*

- Added initial support for [`{exec} python`](/reference/exec.md#python).
  - Currently, Python code execution only works when online.
- Made the automatic page reloading more reactive.
- Made pages cross-origin isolated even if the server doesn't set the
  appropriate headers.
- **This release breaks `<iframe>` tags in documents.** On Chrome, setting the
  `credentialless` attribute on the `<iframe>` tags fixes the issue, but Firefox
  and Safari don't support it (yet).
- [Full changelog](https://github.com/t-doc-org/common/compare/0.9...0.10)

(release-0-9)=
## 0.9 *(2024-09-12)*

- Added automatic page reloading on successful builds in the dev server.
- Fixed encoding issues with {rst:dir}`{exec} :include: <exec:include>`.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.8...0.9)

(release-0-8)=
## 0.8 *(2024-09-12)*

- Allowed multiple references in {rst:dir}`{exec} :after: <exec:after>`.
- Added support for including external files with
  {rst:dir}`{exec} :include: <exec:include>`.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.7...0.8)

(release-0-7)=
## 0.7 *(2024-09-07)*

- Fine-tuned the {rst:dir}`exec` control buttons.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.6...0.7)

(release-0-6)=
## 0.6 *(2024-09-07)*

- Added support for editable blocks with `{exec} :editable:`.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.5...0.6)

(release-0-5)=
## 0.5 *(2024-08-31)*

- Added on-click execution of {rst:dir}`exec` blocks.
- Added support for dependencies with {rst:dir}`{exec} :after: <exec:after>`.
- Added proper rendering of SQL errors in
  [`{exec} sql`](/reference/exec.md#sql).
- Fixed the handling of `NULL` values in [`{exec} sql`](/reference/exec.md#sql).
- [Full changelog](https://github.com/t-doc-org/common/compare/0.4...0.5)

(release-0-4)=
## 0.4 *(2024-08-22)*

- Added checking for updates in the dev server.
- Added install, use and development documentation.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.3...0.4)

(release-0-3)=
## 0.3 *(2024-08-19)*

- Added automatic rebuilding on source file changes in the dev server.
- [Full changelog](https://github.com/t-doc-org/common/compare/0.2...0.3)

(release-0-2)=
## 0.2 *(2024-08-17)*

- First public release.
