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

- Install the `t-doc-common` package.

  `````{tab-set}
  :sync-group: platform
  ````{tab-item} Windows
  :sync: windows
  ```{code-block} shell-session
  python -m pip install t-doc-common
  ```
  ````
  ````{tab-item} macOS
  :sync: macos
  ```{code-block} shell-session
  python -m pip install --user t-doc-common
  ```
  You may have to add `$HOME/.local/bin` to your `PATH`.
  ````
  ````{tab-item} Linux
  :sync: linux
  ```{code-block} shell-session
  python -m pip install --user t-doc-common
  ```
  You may have to add `$HOME/.local/bin` to your `PATH`.
  ````
  `````

## Upgrade

- Check the changes introduced in the new version in the
  [release notes](release_notes).

- Upgrade the `t-doc-common` package and any out-of-date dependencies.

  `````{tab-set}
  :sync-group: platform
  ````{tab-item} Windows
  :sync: windows
  ```{code-block} shell-session
  python -m pip install --upgrade t-doc-common
  ```
  If you get the following error, then a
  [local server](../edit.md#edit-documents) is running. Stop it with
  {kbd}`Ctrl+C` or by closing its terminal window, then try again.
  ```
  ERROR: Could not install packages due to an OSError: [WinError 32] The process
  cannot access the file because it is being used by another process:
  'c:\\users\\...\\scripts\\tdoc.exe'
  ```
  ````
  ````{tab-item} macOS
  :sync: macos
  ```{code-block} shell-session
  python -m pip install --user --upgrade t-doc-common
  ```
  ````
  ````{tab-item} Linux
  :sync: linux
  ```{code-block} shell-session
  python -m pip install --user --upgrade t-doc-common
  ```
  ````
  `````
