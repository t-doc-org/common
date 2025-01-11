% Copyright 2024 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Development

This page describes how to set up t-doc for development. It isn't necessary for
creating and editing documents.

## Install

- Install the [required packages](install.md#requirements) for your system.

- Clone the `t-doc/common` repository (substitute `USER` with your username).

  ```{code-block} shell-session
  hg clone https://USER@c-space.net/rc/hg/t-doc/common
  cd common
  ```

- Checkout and activate the `main` bookmark.

  ```{code-block} shell-session
  hg checkout main
  ```

- Run the local server with `TDOC_VERSION=dev`. This installs the `t-doc-common`
  package as editable into the virtual environment `_venv/dev`.

  `````{tab-set}
  :sync-group: platform
  ````{tab-item} Windows
  :sync: windows
  ```{code-block} shell-session
  set TDOC_VERSION=dev
  run.py --debug serve
  ```
  ````
  ````{tab-item} macOS
  :sync: macos
  ```{code-block} shell-session
  TDOC_VERSION=dev ./run.py --debug serve
  ```
  ````
  ````{tab-item} Linux
  :sync: linux
  ```{code-block} shell-session
  TDOC_VERSION=dev ./run.py --debug serve
  ```
  ````
  `````

## Upgrade

- Pull missing changesets from the `t-doc/common` repository.

  ```{code-block} shell-session
  hg pull
  ```

- Update to the branch head.

  ```{code-block} shell-session
  hg update --check
  ```

- If any dependencies need to be upgraded, delete the `_venv/dev` directory. It
  will be re-created when the local server is run the next time with
  `TDOC_VERSION=dev`.

- Alternatively, the `t-doc-common` package metadata and any out-of-date
  dependencies can be updated in-place.

  `````{tab-set}
  :sync-group: platform
  ````{tab-item} Windows
  :sync: windows
  ```{code-block} shell-session
  _venv\dev\Scripts\pip.exe install --upgrade --editable .
  ```
  ````
  ````{tab-item} macOS
  :sync: macos
  ```{code-block} shell-session
  _venv/dev/bin/pip install --user --upgrade --editable .
  ```
  ````
  ````{tab-item} Linux
  :sync: linux
  ```{code-block} shell-session
  _venv/dev/bin/pip install --user --upgrade --editable .
  ```
  ````
  `````
