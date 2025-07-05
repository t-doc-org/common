% Copyright 2024 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Development

This page describes how to set up t-doc for development. It isn't necessary for
creating and editing documents.

## Install

- Install the [required packages](install.md#requirements) for your system.

- Install [Node.js](https://nodejs.org), include the `npm` package manager and
  make sure it's on the system `PATH`.

- Install [build](https://pypi.org/project/build/) and
  [hatchling](https://pypi.org/project/hatchling/).

  `````{tab-set}
  :sync-group: platform
  ````{tab-item} Windows
  :sync: windows
  ```{code-block} shell-session
  python -m pip install build hatchling
  ```
  ````
  ````{tab-item} macOS
  :sync: macos
  ```{code-block} shell-session
  python -m pip install --user build hatchling
  ```
  ````
  ````{tab-item} Linux
  :sync: linux
  ```{code-block} shell-session
  python -m pip install --user build hatchling
  ```
  ````
  `````

- Clone the `t-doc/common` repository (substitute `USER` with your username).

  ```{code-block} shell-session
  hg clone https://USER@c-space.net/rc/hg/t-doc/common
  cd common
  ```

- Checkout and activate the `main` bookmark.

  ```{code-block} shell-session
  hg checkout main
  ```

- Run the local server with the environment variable `TDOC_VERSION=dev`. This
  installs the `t-doc-common` package as editable into the virtual environment
  `_venv/dev`. You may also want to use the `--debug` option to get full
  tracebacks.

  `````{tab-set}
  :sync-group: platform
  ````{tab-item} Windows
  :sync: windows
  ```{code-block} shell-session
  set TDOC_VERSION=dev
  run.py tdoc serve --debug
  ```
  ````
  ````{tab-item} macOS
  :sync: macos
  ```{code-block} shell-session
  TDOC_VERSION=dev ./run.py tdoc serve --debug
  ```
  ````
  ````{tab-item} Linux
  :sync: linux
  ```{code-block} shell-session
  TDOC_VERSION=dev ./run.py tdoc serve --debug
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

- Update the generated files.

  ```{code-block} shell-session
  python -m build --no-isolation --wheel
  ```

- If any Python dependencies need to be upgraded, delete the `_venv/dev`
  directory. It will be re-created when the local server is run the next time
  with `TDOC_VERSION=dev`.

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
  _venv/dev/bin/pip install --upgrade --editable .
  ```
  ````
  ````{tab-item} Linux
  :sync: linux
  ```{code-block} shell-session
  _venv/dev/bin/pip install --upgrade --editable .
  ```
  ````
  `````
