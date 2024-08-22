<!-- Copyright 2024 Caroline Blank <caro@c-space.org> -->
<!-- Copyright 2024 Remy Blank <remy@c-space.org> -->
<!-- SPDX-License-Identifier: MIT -->

# Development

## Install

- Install the [required packages](install.md#requirements) for your system.

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
  `````{tab-set}
  :sync-group: platform
  ````{tab-item} Windows
  :sync: windows
  ```{code-block} shell-session
  python -m pip install --editable .
  ```
  ````
  ````{tab-item} Linux, macOS
  :sync: linux
  ```{code-block} shell-session
  python -m pip install --user --editable .
  ```
  You may have to add `$HOME/.local/bin` to your `PATH`.
  ````
  `````

## Upgrade

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
  `````{tab-set}
  :sync-group: platform
  ````{tab-item} Windows
  :sync: windows
  ```{code-block} shell-session
  python -m pip install --upgrade --editable .
  ```
  ````
  ````{tab-item} Linux, macOS
  :sync: linux
  ```{code-block} shell-session
  python -m pip install --user --upgrade --editable .
  ```
  ````
  `````