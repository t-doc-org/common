% Copyright 2026 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Frequently asked questions

## Installing

(faq-clean-install)=
### How can I force a clean install?

If the local server refuses to start, it may be due to a broken install. To
force a clean install of the `t-doc-common` package and its dependencies, remove
the `_venv` directory at the root of the document repository.

(faq-previous-version)=
### How can I use the previous version of t-doc?

If the stable version of the `t-doc-common` package is broken, the previous
version of the package can be used until a fix is released.

- Create a text file `t-doc.toml` at the root of the site repository, and set
  its content as follows:

  ```{code-block} toml
  version = 'previous'
  ```

- Start the local server. This will install and run the previous version.

- To return to the stable version, remove the file `t-doc.toml` created above.

(faq-specific-version)=
### How can I use a specific version of t-doc?

- Check the [release notes](release-notes.md) and find the version of the
  `t-doc-common` package to install, e.g. `0.62`.

- Create a text file `t-doc.toml` at the root of the site repository, and set
  its content as follows:

  ```{code-block} toml
  version = '0.62'
  ```

- Start the local server. This will install and run the selected version.

- To return to the stable version, remove the file `t-doc.toml` created above.

## Editing

(faq-changes-not-deployed)=
### Why do my changes not show up on the deployed site?

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

## Troubleshooting

(faq-ssl_ctx)=
### The local server fails with `ERROR: run() got an unexpected keyword argument 'ssl_ctx'`. How can I fix it?

This is a temporary error due to a compatibility issue with `run-stage2.py`.
Running the local server again while connected to the internet should fix the
issue.

(faq-local-server-failure)=
### The local server fails to start. How can I fix it?

- Perform a [clean install](#faq-clean-install) of t-doc and run the server
  again. If this works, you're done.
- Roll back to the [previous version](#faq-previous-version) of t-doc and run
  the server again. If this works, please [report the issue](#faq-report-issue),
  Don't forget to revert to the stable version once the issue is fixed.
- Run the server with `--debug`, copy the full console output and
  [report the issue](#faq-report-issue).

(faq-report-issue)=
### How can I report an issue with t-doc?

Contact your favorite support person by email, and provide as much relevant
information as possible, including:

- A precise description of the issue
- The full error message, if possible with a traceback (run the command with
  `--debug`)
- The site repository
- The operating system running on your computer
