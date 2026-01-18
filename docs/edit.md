% Copyright 2024 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Create & edit documents

## Clone a repository

Documents are grouped into **sites**, which represent the unit of deployment.
Each site is tracked as a Mercurial repository.

- Clone the repository with (substitute `SITE` with the name of the site):

  ```{code-block} shell-session
  hg clone -u main https://rc.t-doc.org/hg/SITE
  ```

  If the command asks for a username and password, ensure you have set up the
  Mercurial configuration as described in "[Install](install.md#install)".

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
    rebuild, and report the issue to t-doc's authors.

- **Stop the local server** by clicking the
  <span class="fa fa-door-closed"></span> button in the header, by typing
  {kbd}`Ctrl+C` in the terminal, or by closing the terminal window.

- Don't forget to **commit changes frequently**.

## Deploy documents

To deploy the site to [`tdoc.org`](https://t-doc.org/):

- Make sure that all changes have been committed (and that new files have been
  added with Mercurial).

- **Push the changes** to the server.

  ```{code-block} shell-session
  hg push
  ```

- The changes should be live at `https://SITE.t-doc.org/` within a few minutes. If
  the build fails, GitHub should send you an email notification. It contains a
  link to the build log, which should allow figuring out what went wrong.

## Troubleshooting

### The local server fails with `CERTIFICATE_VERIFY_FAILED`

Install or upgrade the [`certifi`](https://pypi.org/project/certifi/) package.

```{code-block} shell-session
python -m pip install --upgrade certifi
```

### Changes don't show up on the deployed site

- Go to the [`t-doc-org`](https://github.com/t-doc-org) organization page and
  check the "Publish" status for the site. If it is failing, click on the badge
  and check the logs of the failing workflow.

- Check that the `main` bookmark is active and pointing to the repository head.
  Run:

  ```{code-block} shell-session
  hg id
  ```

  The command should output the current revision, followed by `tip main`. If it
  doesn't, the bookmark can be moved to the current revision with:

  ```{code-block} shell-session
  hg bookmark main
  ```
