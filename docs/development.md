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

## Run

Commands can be run with the development setup via its `run.py` script. The
script runs commands within the
[virtual environment](https://docs.python.org/3/library/venv.html) installed
into `_venv`.

- **Run the local server with debug settings**, as specified by the
  `command-dev` default defined in
  [`run.toml`](https://github.com/t-doc-org/common/blob/main/config/run.toml).

  `````{tab-set}
  :sync-group: platform
  ````{tab-item} Windows
  :sync: windows
  ```{code-block} shell-session
  run.py
  ```
  ````
  ````{tab-item} macOS
  :sync: macos
  ```{code-block} shell-session
  ./run.py
  ```
  ````
  ````{tab-item} Linux
  :sync: linux
  ```{code-block} shell-session
  ./run.py
  ```
  ````
  `````

- **Run the local server against a specific site.** The command below assumes
  that the site checkout is in the same directory as the `common` checkout.

  ```{code-block}
  :class: line-height-normal
  ├── common
  └── site
  ```

  `````{tab-set}
  :sync-group: platform
  ````{tab-item} Windows
  :sync: windows
  ```{code-block} shell-session
  cd site
  ..\common\run.py
  ```
  ````
  ````{tab-item} macOS
  :sync: macos
  ```{code-block} shell-session
  cd site
  ../common/run.py
  ```
  ````
  ````{tab-item} Linux
  :sync: linux
  ```{code-block} shell-session
  cd site
  ../common/run.py
  ```
  ````
  `````

- To make the local server **trigger a rebuild whenever code within `common`
  changes**, add the following line to the
  [`[defaults]`](reference/config.md#defaults) section of `run.local.toml`. This
  is useful when working on code related to building sites or on client-side
  code.

  ```{code-block}
  command-dev_20 = ["--watch=../common/tdoc"]
  ```

- To make the local server **restart for each rebuild**, add the following line
  to the [`[defaults]`](reference/config.md#defaults) section of
  `run.local.toml`. This is useful when working on the local server itself or on
  API code.

  ```{code-block}
  command-dev_21 = ["--restart-on-change"]
  ```

- **Create a persistent database for the local server.** This requires
  configuring the path to the database in the
  [`[store]`](reference/config.md#store) section of `tdoc.local.toml`.

  ```{code-block}
  [store]
  path = "tmp/store.sqlite"
  ```

  `````{tab-set}
  :sync-group: platform
  ````{tab-item} Windows
  :sync: windows
  ```{code-block} shell-session
  run.py tdoc store create --dev
  ```
  ````
  ````{tab-item} macOS
  :sync: macos
  ```{code-block} shell-session
  ./run.py tdoc store create --dev
  ```
  ````
  ````{tab-item} Linux
  :sync: linux
  ```{code-block} shell-session
  ./run.py tdoc store create --dev
  ```
  ````
  `````

- **Get help for `tdoc` sub-commands.**

  `````{tab-set}
  :sync-group: platform
  ````{tab-item} Windows
  :sync: windows
  ```{code-block} shell-session
  run.py tdoc --help
  ```
  ````
  ````{tab-item} macOS
  :sync: macos
  ```{code-block} shell-session
  ./run.py tdoc --help
  ```
  ````
  ````{tab-item} Linux
  :sync: linux
  ```{code-block} shell-session
  ./run.py tdoc --help
  ```
  ````
  `````
