% Copyright 2024 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Install & upgrade

```{toctree}
:maxdepth: 1
:hidden:
release_notes
```

## Requirements

t-doc requires the following software to be installed:

- [Python](https://www.python.org/) 3.12 or later
- [Graphviz](https://graphviz.org/), for `graphviz` directives
- [Mercurial](https://www.mercurial-scm.org/), for managing source files

### Windows

- Install [Python](https://www.python.org/).

  ```{code-block} shell-session
  winget install --id Python.Python.3.12
  ```

  - Check that Python can be launched from the command-line, by running:

    ```{code-block} shell-session
    python
    ```

    If this opens the Microsoft Store, open Windows settings, search for "App
    execution aliases", and disable the "App Installer" entries for `python.exe`
    and `python3.exe`.

- Install [Graphviz](https://graphviz.org/). The installer must be run
  interactively and the **"Add Graphviz to the system PATH for all users"**
  option must be enabled.

  ```{code-block} shell-session
  winget install --id Graphviz.Graphviz --interactive
  ```

- Install [TortoiseHg](https://tortoisehg.bitbucket.io/).

  ```{code-block} shell-session
  winget install --id TortoiseHg.TortoiseHg
  ```

  - Open the TortoiseHg settings, go to your user's global settings, then click
    "Edit file" and add the following to the configuration (substitute `FIRST`
    and `LAST` with your first and last name, and `EMAIL` with your email
    address, e.g. `Joe Smith <joe@example.com>`):

    ```ini
    [ui]
    username = FIRST LAST <EMAIL>
    ```

- (Optional, Windows 10) Install
  [Windows Terminal](https://github.com/microsoft/terminal) (it's already
  installed on Windows 11 and later).

  ```{code-block} shell-session
  winget install --id Microsoft.WindowsTerminal
  ```

### macOS

- Install [Python](https://www.python.org/), [Graphviz](https://graphviz.org/)
  and [Mercurial](https://www.mercurial-scm.org/) either by hand or through a
  package manager like [Homebrew](https://brew.sh/).

### Linux

- Install [Python](https://www.python.org/), [Graphviz](https://graphviz.org/)
  and [Mercurial](https://www.mercurial-scm.org/) through your system's package
  manager.

## Install

- Install the [required packages](#requirements).
- The `t-doc-common` package will be installed automatically when
  [starting the local server](edit.md#edit-documents).

## Upgrade

The [local server](edit.md#edit-documents) indicates when an upgrade is
available.

- Check the changes introduced in the new version in the
  [release notes](release_notes.md).
- Restart the local server. When prompted, accept the upgrade.

## Troubleshooting

### Force a clean install

If the local server refuses to start, it may be due to a broken install. To
force a clean install of the `t-doc-common` package and its dependencies, remove
the `_venv` directory at the root of the document repository.

### Install a specific version

If the latest version of the `t-doc-common` package is broken, a previous
version of the package can be used until a fix is released.

- Find the version of the `t-doc-common` package to install in the
  [release notes](release_notes.md) (the example below uses version `0.28`).
- Open a terminal at the root of the document repository.
- Set the `RUN_REQUIREMENTS` environment variable to the desired version
  specification, then run the desired command through the
  `run-tdoc@t-doc-common.py` script.

  `````{tab-set}
  :sync-group: platform
  ````{tab-item} Windows
  :sync: windows
  ```{code-block} shell-session
  set RUN_REQUIREMENTS=t-doc-common==0.28
  run-tdoc@t-doc-common.py serve
  ```
  ````
  ````{tab-item} macOS
  :sync: macos
  ```{code-block} shell-session
  RUN_REQUIREMENTS=t-doc-common==0.28 ./run-tdoc@t-doc-common.py serve
  ```
  ````
  ````{tab-item} Linux
  :sync: linux
  ```{code-block} shell-session
  RUN_REQUIREMENTS=t-doc-common==0.28 ./run-tdoc@t-doc-common.py serve
  ```
  ````
  `````
