% Copyright 2024 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Install & upgrade

```{toctree}
:maxdepth: 1
:hidden:
release-notes
```

## Requirements

t-doc requires the following software to be installed:

- [Python](https://www.python.org/) 3.13
- [Graphviz](https://graphviz.org/), for `graphviz` directives
- [Mercurial](https://www.mercurial-scm.org/), for managing source files

### Windows

- Install [Python](https://www.python.org/).

  ```{code-block} shell-session
  winget install --id Python.Python.3.13
  ```

  - Check that Python can be launched from the command-line, by running:

    ```{code-block} shell-session
    python
    ```

    If this opens the Microsoft Store, open Windows settings, search for "App
    execution aliases", and disable the "App Installer" entries for `python.exe`
    and `python3.exe`.

  - Install the [`certifi`](https://pypi.org/project/certifi/) package.

    ```{code-block} shell-session
    python -m pip install certifi
    ```

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

- (Optional, Windows 10) Install
  [Windows Terminal](https://github.com/microsoft/terminal) (it's already
  installed on Windows 11 and later).

  ```{code-block} shell-session
  winget install --id Microsoft.WindowsTerminal
  ```

#### Upgrades

Available upgrades for these packages can be displayed and installed with
`winget upgrade`.

```{code-block} shell-session
winget upgrade
winget upgrade --id Python.Python.3.13
python -m pip install --upgrade certifi
winget upgrade --id Graphviz.Graphviz
winget upgrade --id TortoiseHg.TortoiseHg
winget upgrade --id Microsoft.WindowsTerminal
```

### macOS

- Install [Python](https://www.python.org/), [Graphviz](https://graphviz.org/)
  and [Mercurial](https://www.mercurial-scm.org/) manually or via a package
  manager like [Homebrew](https://brew.sh/).

### Linux

- Install [Python](https://www.python.org/), [Graphviz](https://graphviz.org/)
  and [Mercurial](https://www.mercurial-scm.org/) via your system's package
  manager.

## Install

- Install the [required packages](#requirements).

- If this is the first time you access a t-doc repository, generate a repository
  access password.
  - Go to [`tdoc.org`](https://t-doc.org/) and ensure you are logged in.
  - In the navigation bar, select "<span class="fa fa-user"></span> &rarr;
    <span class="fa fa-gear"></span> Settings", then open "Repository access".
  - Click "Reset" to generate the password. Keep the dialog open for the next
    step.

- Edit the Mercurial configuration for your user. If the file doesn't exist yet,
  create it as an empty plain-text file.

  - **Windows:** `%USERPROFILE%\.hgrc` (typically `C:\Users\USERNAME\.hgrc`)
  - **macOS, Linux:** `$HOME\.hgrc` (typically `/home/USERNAME/.hgrc`)

  Copy the `[auth]` section from the dialog above (if you generated a new
  password) or from another install (if you already had a password), and paste
  it into the configuration. Also, add a `[ui]` section and specify your
  username (substitute `FIRST` and `LAST` with your first and last name, and
  `EMAIL` with your email address, e.g. `Joe Smith <joe@example.com>`). Save the
  file.

  ```{code-block} ini
  [auth]
  t-doc.prefix = https://rc.t-doc.org/
  t-doc.username = USER_ID
  t-doc.password = PASSWORD

  [ui]
  username = FIRST LAST <EMAIL>
  ```

- Everything else will be installed automatically when
  [starting the local server](edit.md#edit-documents).

## Upgrade

The [local server](edit.md#edit-documents) indicates when an upgrade is
available.

- Check the changes introduced in the new version in the
  [release notes](release-notes.md).
- Restart the local server. When prompted, accept the upgrade.

## Troubleshooting

### Force a clean install

If the local server refuses to start, it may be due to a broken install. To
force a clean install of the `t-doc-common` package and its dependencies, remove
the `_venv` directory at the root of the document repository.

### Use the previous version

If the stable version of the `t-doc-common` package is broken, the previous
version of the package can be used until a fix is released.

- Create a text file `t-doc.toml` at the root of the site repository, and set
  its content as follows:

  ```{code-block} toml
  version = 'previous'
  ```

- Start the local server. This will install and run the previous version.

- To return to the stable version, remove the file `t-doc.toml` created above.

### Install a specific version

- Check the [release notes](release-notes.md) and find the version of the
  `t-doc-common` package to install, e.g. `0.62`.

- Create a text file `t-doc.toml` at the root of the site repository, and set
  its content as follows:

  ```{code-block} toml
  version = '0.62'
  ```

- Start the local server. This will install and run the selected version.

- To return to the stable version, remove the file `t-doc.toml` created above.
