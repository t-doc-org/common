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

- Create a text file `run.local.toml` at the root of the site repository, and
  set its content as follows:

  ```{code-block} toml
  version = "previous"
  ```

- Start the local server. This will install and run the previous version.

- To return to the stable version, remove the file `run.local.toml` created
  above.

(faq-specific-version)=
### How can I use a specific version of t-doc?

- Check the [release notes](/release-notes.md) and find the version of the
  `t-doc-common` package to install, e.g. `0.62`.

- Create a text file `run.local.toml` at the root of the site repository, and
  set its content as follows (substitute `0.62` with the desired version):

  ```{code-block} toml
  version = "0.62"
  ```

- Start the local server. This will install and run the selected version.

- To return to the stable version, remove the file `run.local.toml` created
  above.

## Editing

(faq-new-remote-head)=
### Why does `hg push` fail with "push creates new remote head"?

When `hg push` fails with "push creates new remote head", it means that the
remote server has changes that aren't available locally, usually pushed by
someone else. These changes must first be pulled from the remote and merged
before the push can succeed. **Do not** use `hg push --force` to try and
force-push the new head.

```{code-block} shell-session
hg pull
hg merge
# Resolve conflicts if any, and check the merge result.
hg commit
```

It may be worth reading a [Mercurial tutorial](edit.md#mercurial) to get
familiar with basic version control workflows.

(faq-changes-not-deployed)=
### Why do my changes not show up on the deployed site?

- Check the "Publish" status on the badge in the left sidebar. If it is failing,
  click the badge and check the logs of the failing workflow.

- Check that the `main` bookmark is active and pointing to the repository head.
  Run:

  ```{code-block} shell-session
  hg id
  ```

  The command should output the current revision, followed by `tip main`. If it
  doesn't, the bookmark must be moved to the current revision and pushed with:

  ```{code-block} shell-session
  hg bookmark main
  hg push -B main
  ```

## Troubleshooting

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

Contact your favorite t-doc support person by email, and provide as much
relevant information as possible, including:

- A precise description of the issue
- The full error message, if possible with a traceback (run the command with
  `--debug`)
- The site repository
- The operating system running on your computer

## Licensing

(faq-adapted-material)=
### Can I copy documents from other t-doc sites?

Documents copied from other sites to your own site and modified are called
"adapted material" and are explicitly allowed by the license
([CC-BY-NC-SA](https://creativecommons.org/licenses/by-nc-sa/4.0/)), as long as
all the clauses of the license are respected.

Note in particular the section about attribution
([3.a.](https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode.en#s3a))
(and see the FAQ about [document headers](#faq-document-header)) and ShareAlike
([3.b.](https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode.en#s3b)).

(faq-document-header)=
### Should I update the header of documents copied from other t-doc sites?

Documents normally start with a header of the form:

```
% Copyright 2025 John Doe <john.doe@example.com>
% SPDX-License-Identifier: CC-BY-NC-SA-4.0
```

The first line is a copyright notice; the second is a license notice. The
[CC-BY-NC-SA](https://creativecommons.org/licenses/by-nc-sa/4.0/) license
requires both of them to be retained
([3.a.1.A.](https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode.en#s3a1A)
and [3.b.](https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode.en#s3b)).
In practice, this means:

- When copying documents from another site, **the header must remain
  unchanged**.

- When later modifying such a copied document, you can add your own copyright
  notice, but **the existing copyright and license notices must remain
  unchanged**. For example, if the document above is modified, the header can
  be changed to:

  ```
  % Copyright 2025 John Doe <john.doe@example.com>
  % Copyright 2026 Robert Smith <robert.smith@example.com>
  % SPDX-License-Identifier: CC-BY-NC-SA-4.0
  ```

- It isn't necessary to explicitly track which parts of a document are
  copyrighted to whom. This information is already available in the site
  repository history.

- **The license notice must never be changed.**
