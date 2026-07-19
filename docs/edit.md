% Copyright 2024 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Create & edit documents

This page assumes a basic working knowledge of revision control with
[Mercurial](https://www.mercurial-scm.org/). If you aren't familiar with the
tool, the [section below](#mercurial) has some links and hints.

## Clone a repository

Documents are grouped into **sites**, which represent the unit of deployment.
Each site is tracked as a Mercurial repository.

- Clone the site repository with (substitute `SITE` with the name of the site):

  ```{code-block} shell-session
  hg clone -u main https://rc.t-doc.org/hg/SITE
  ```

  If the command asks for a username and password, ensure you have set up the
  Mercurial configuration as described in "[Install](install.md#install)".

- Configure the site via [`conf.py`](reference/config.md#sphinx-configuration),
  and optionally via
  [`tdoc.local.toml`](reference/config.md#cli-and-api-configuration).

The typical structure of a site repository is shown below. The source files are
located below the `docs` directory.

```{code-block}
:class: line-height-normal
├── .github
│   └── workflows
│       └── publish.yml       A workflow to publish the site
├── docs
│   ├── conf.py               The Sphinx configuration
│   ├── index.md              The main index page
│   └── ...                   The source documents
├── .gitignore
├── .hgignore
├── LICENSE.txt
├── README.md
├── run.desktop               A desktop entry to run the local server on Linux
├── run.local.toml            An optional configuration for run.py
├── run.py                    An auto-installing wrapper for the CLI
└── tdoc.local.toml           An optional configuration for the CLI and API
```

## Edit documents

- **Run the local server.**

  `````{tab-set}
  :sync-group: platform
  ````{tab-item} Windows
  :sync: windows
  Double-click the file `run.py` in the repository root. Make sure that `.py`
  files are associated with Python by default.

  Alternatively, open a terminal at the repository root, and run:
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

  The HTML pages are in _build\serve-8000-next\html.
  Serving at <http://localhost:8000/>
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
  - After the initial full build of all pages, the server **rebuilds only pages
    that change**. This is much faster, but can sometimes cause artifacts or
    failures. If this happens, restart the local server to trigger a full
    rebuild, and [report the issue](#faq-report-issue) to the t-doc authors.

- **Stop the local server** by clicking the
  <span class="fa fa-door-closed"></span> button in the navigation bar, by
  typing {kbd}`Ctrl+C` in the terminal, or by closing the terminal window.

- Don't forget to **commit changes frequently**.

## Deploy documents

To deploy the site to [`tdoc.org`](https://t-doc.org/):

- Make sure that all changes have been committed (and that new files have been
  added with Mercurial).

- **Push the changes** to the server.

  ```{code-block} shell-session
  hg push
  ```

- The changes should be live at `https://SITE.t-doc.org/` within a few minutes.
  - If the build fails, the "Publish" badge in the left sidebar will turn red.
    Click the badge to view the build log, which should allow figuring out what
    went wrong.

## Mercurial

Many Mercurial tutorials are available on the internet; here are a few starting
points.

- [Mercurial Kick Start](https://mercurial.aragost.com/kick-start/en/) (also
  available in [French](https://mercurial.aragost.com/kick-start/fr/))
- [HgInit](https://hginit.github.io/)
- [Mercurial: The Definitive Guide](https://mercurial-book.readthedocs.io/en/latest/)
- [Mercurial quick start](https://wiki.mercurial-scm.org/QuickStart)

You will need to learn basic usage of the following commands (add `--help` to
any command to view its documentation):

- `hg clone`: [Clone](#clone-a-repository) a site repository from the remote
  server to a local directory.
- `hg status`: Display the local state of tracked and untracked files.
- `hg diff`: Display the changes against the last recorded state.
- `hg add`: Add new files to be tracked in the repository.
- `hg remove`: Remove files from the repository.
- `hg commit`: Record changes.
- `hg push`: Push recorded changes to the remote server. This also
  [deploys](#deploy-documents) the site.
- `hg pull`: Fetch changes from the remote server.
- `hg merge`: Merge diverging changes histories.
  - The t-doc authors must sometimes make changes to site repositories. You will
    need to merge these changes before pushing your own.
