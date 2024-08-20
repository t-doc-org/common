<!-- Copyright 2024 Caroline Blank <caro@c-space.org> -->
<!-- Copyright 2024 Remy Blank <remy@c-space.org> -->
<!-- SPDX-License-Identifier: MIT -->

# Install & upgrade

(requirements)=
## Requirements

t-doc requires the following software to be installed:

- [Python](https://www.python.org/) 3.12 or later
- [Graphviz](https://graphviz.org/), for `{graphviz}` directives
- [Mercurial](https://www.mercurial-scm.org/), for managing source files

### Windows

- Install [Python](https://www.python.org/) 3.12.
  ```{code-block} shell-session
  winget install --id Python.Python.3.12
  ```

- Install [Graphviz](https://graphviz.org/). The installer must be run
  interactively and **the "Add Graphviz to the system PATH for all users"
  option must be enabled**.
  ```{code-block} shell-session
  winget install --id Graphviz.Graphviz --interactive
  ```

- Install [TortoiseHg](https://tortoisehg.bitbucket.io/).
  ```{code-block} shell-session
  winget install --id TortoiseHg.TortoiseHg
  ```

  ```{admonition} TODO
  TODO: Describe how to update .hgrc to configure the name and email address.
  ```

- (Optional, Windows 10) Install
  [Windows Terminal](https://github.com/microsoft/terminal) (it's already
  installed on Windows 11 and later).
  ```{code-block} shell-session
  winget install --id Microsoft.WindowsTerminal
  ```

### Linux, macOS

- Install [Python](https://www.python.org/), [Graphviz](https://graphviz.org/)
  and [Mercurial](https://www.mercurial-scm.org/) through your system's package
  manager.

(install)=
## Install

- Install the [required packages](#requirements).

- Install the `t-doc-common` package.
  ```{code-block} shell-session
  python -m pip install --user t-doc-common
  ```

(upgrade)=
## Upgrade

- Upgrade the `t-doc-common` package and any out-of-date dependencies.
  ```{code-block} shell-session
  python -m pip install --user --upgrade t-doc-common
  ```

## Development

(dev-install)=
### Install

- Install the [required packages](#requirements) for your system.

- Clone the `t-doc/common` repository (substitute `USER` with your username).
  ```{code-block} shell-session
  hg clone https://USER@c-space.net/rc/hg/t-doc/common
  cd common
  ```

- Enable git subrepositories.
  ```{code-block} shell-session
  echo -e '[subrepos]\ngit:allowed = true\n' >> .hg/hgrc
  ```

- Checkout the subrepositories and activate the `main` bookmark.
  ```{code-block} shell-session
  hg checkout main
  ```

- Install the `t-doc-common` package from editable sources.
  ```{code-block} shell-session
  python -m pip install --user --editable .
  ```

(dev-upgrade)=
### Upgrade

- Pull missing changesets from the `t-doc/common` repository.
  ```{code-block} shell-session
  cd common
  hg pull
  ```

- Update to the branch head.
  ```{code-block} shell-session
  hg update --check
  ```

- Upgrade the `t-doc-common` package metadata and any out-of-date dependencies.
  ```{code-block} shell-session
  python -m pip install --user --upgrade --editable .
  ```
