% Copyright 2024 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Create & edit documents

## Clone a repository

Documents are grouped into **repositories**, which represent the unit of
deployment. Each document repository is tracked as a Mercurial repository.

- Clone the repository with (substitute `REPO` with the name of the repository):

  ```{code-block} shell-session
  hg clone -u main https://c-space.net/rc/hg/t-doc/REPO
  ```

- Edit the file `.hg/hgrc` in the cloned repository and **add the following
  lines** (substitute `USER` with your username, `PASSWORD` with your password,
  `FIRST` and `LAST` with your first and last name, and `EMAIL` with your email
  address, e.g. `Joe Smith <joe@example.com>`):

  ```{code-block} ini
  [auth]
  c-space.prefix = https://c-space.net/
  c-space.username = USER
  c-space.password = PASSWORD

  [ui]
  username = FIRST LAST <EMAIL>
  ```

The typical structure of a document repository is shown below. The source files
are located below the `docs` directory.

```{code-block}
:class: line-height-normal
├── .github
│   └── workflows
│       └── publish.yml       A workflow to publish the repository
├── docs
│   ├── conf.py               The Sphinx configuration
│   ├── index.md              The main index page
│   └── ...                   The source documents
├── .gitignore
├── .hgignore
├── LICENSE.txt
├── README.md
├── run.desktop               A desktop entry to run the local server on Linux
└── run.py                    An auto-installing wrapper for the tdoc command
```

## Edit documents

- **Run the local server.**

  `````{tab-set}
  :sync-group: platform
  ````{tab-item} Windows
  :sync: windows
  Double-click the file `run.py` in the repository root. Make sure that `.py`
  files are associated with Python by default.

  Alternatively, open a terminal, change to the repository root, and run:
  ```{code-block} shell-session
  run.py
  ```
  ````
  ````{tab-item} macOS
  :sync: macos
  Open a terminal, change to the repository root, and run:
  ```{code-block} shell-session
  ./run.py
  ```
  ````
  ````{tab-item} Linux
  :sync: linux
  Double-click the file `run.desktop` in the repository root.

  Alternatively, open a terminal, change to the repository root, and run:
  ```{code-block} shell-session
  ./run.py
  ```
  ````
  `````

  The server renders the source files into HTML, and serves the site over HTTP.

  ```{code-block} text
  Running Sphinx
  loading translations [fr]... done
  making output directory... done
  (...)
  build succeeded.

  The HTML pages are in _build\serve-1724331687766143000\html.
  Serving at <http://[::1]:8000/>
  ```

- **Navigate** to [`http://localhost:8000/`](http://localhost:8000/) to view the
  generated pages.

- **Create and edit documents** in the `docs` directory. This can be done with
  any plain text editor.
  - The local server watches the source files and **automatically rebulids the
  HTML** when a file changes.
  - When the build is successful, the browser **automatically reloads** all open
    pages.
  - If a build fails, the errors can be viewed in the terminal.

- **Stop the local server** by clicking the
  <span style="font: var(--fa-font-solid);">&#xf52a;</span> button in the
  header, by typing {kbd}`Ctrl+C` in the terminal, or by closing the terminal
  window.

- Don't forget to **commit changes frequently**.

## Deploy documents

To deploy the repository to [`tdoc.org`](https://t-doc.org), make sure that all
changes have been committed (and that new files have been added with Mercurial),
then push the changes to the server.

```{code-block} shell-session
hg push
```

The changes should be live at `https://t-doc.org/REPO` within a few minutes. If
the build fails, GitHub should send you an email notification. It contains a
link to the build log, which should allow figuring out what went wrong.

Make sure that the `main` bookmark is always active and pointing to the
repository head.
