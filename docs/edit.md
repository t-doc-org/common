% Copyright 2024 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Create & edit documents

## Check out a repository

Documents are grouped into **repositories**, which represent the unit of
deployment. Each document repository is tracked as a Mercurial repository. A
repository can be checked out with (substitute `USER` with your username, and
`REPO` with the name of the repository):

```{code-block} shell-session
hg checkout https://USER@c-space.net/rc/hg/t-doc/REPO
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
├── serve.bat                 A script to run the local server on Windows
└── serve.desktop             A desktop entry to run the local server on Linux
```

## Edit documents

- **Run the local server.**

  `````{tab-set}
  :sync-group: platform
  ````{tab-item} Windows
  :sync: windows
  Double-click the file `serve.bat` in the repository directory.
  ````
  ````{tab-item} macOS
  :sync: macos
  Open a terminal, change to the repository directory, and run:
  ```{code-block} shell-session
  tdoc serve
  ```
  ````
  ````{tab-item} Linux
  :sync: linux
  Double-click the file `serve.desktop` in the repository directory.

  Alternatively, open a terminal, change to the repository directory, and run:
  ```{code-block} shell-session
  tdoc serve
  ```
  ````
  `````

  The server renders the source files into HTML, and serves the result over
  HTTP.

  ```{code-block} text
  Running Sphinx v8.0.2
  loading translations [fr]... done
  making output directory... done
  (...)
  build succeeded.

  The HTML pages are in _build\serve-1724331687766143000\html.
  Serving at <http://[::1]:8000/>
  ```

- **Navigate** to [http://localhost:8000/](http://localhost:8000/) to view the
  generated pages.

- **Create and edit documents** in the `docs` directory. This can be done with
  any plain text editor.
  - The local server watches the source files and **automatically rebulids the
  HTML** when a file changes.
  - If a build is successful, the browser **automatically reloads** all open
    pages.
  - If a build fails, the errors can be viewed in the terminal.

- **Stop the local server** with {kbd}`Ctrl+C` in the terminal, or by closing
  the terminal window.

- Don't forget to **commit changes frequently**.

## Deploy documents

To deploy the repository to `tdoc.org`, make sure that all changes have been
committed (and that new files have been added with Mercurial), then push the
changes to the server.

```{code-block} shell-session
hg push
```

The changes should be live at `https://t-doc.org/REPO` within a few minutes. If
the build fails, GitHub will send you an email notification. It contains a link
to the build log, which should allow figuring out what went wrong.
