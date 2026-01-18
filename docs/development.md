% Copyright 2024 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Development

This page describes how to set up t-doc for development. It isn't necessary for
creating and editing documents.

## Install

- Install the [required packages](install.md#requirements) for your system.

- Install [Node.js](https://nodejs.org), include the `npm` package manager and
  make sure it's on the system `PATH`.

  `````{tab-set}
  :sync-group: platform
  ````{tab-item} Windows
  :sync: windows
  ```{code-block} shell-session
  winget install --id OpenJS.NodeJS.LTS
  ```
  ````
  ````{tab-item} macOS
  :sync: macos
  Install Node.js manually or via a package manager like
  [Homebrew](https://brew.sh/)
  ````
  ````{tab-item} Linux
  :sync: linux
  Install Node.js via your system's package manager.
  ````
  `````

- Install the [`build`](https://pypi.org/project/build/),
  [`hatchling`](https://pypi.org/project/hatchling/) and
  [`uv`](https://pypi.org/project/uv/) packages.

  `````{tab-set}
  :sync-group: platform
  ````{tab-item} Windows
  :sync: windows
  ```{code-block} shell-session
  python -m pip install build hatchling uv
  ```
  ````
  ````{tab-item} macOS
  :sync: macos
  ```{code-block} shell-session
  python -m pip install --user build hatchling uv
  ```
  ````
  ````{tab-item} Linux
  :sync: linux
  ```{code-block} shell-session
  python -m pip install --user build hatchling uv
  ```
  ````
  `````

- Clone the `common` repository.

  ```{code-block} shell-session
  hg clone -u main https://rc.t-doc.org/hg/common
  cd common
  ```

- Run the local server [as usual](edit.md#edit-documents). This installs the
  `t-doc-common` package as editable into the virtual environment `_venv/dev`.

## Upgrade

- Pull missing changesets from the `common` repository.

  ```{code-block} shell-session
  hg pull
  ```

- Update to the branch head.

  ```{code-block} shell-session
  hg update --check
  ```

- Update the generated files.

  ```{code-block} shell-session
  uv build
  ```

- If any Python dependencies need to be upgraded, delete the `_venv/dev`
  directory. It will be re-created when the local server is run the next time.
