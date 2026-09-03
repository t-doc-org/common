% Copyright 2026 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Fixes

## What is a fix?

A fix is **an action that needs to be performed by a site owner**, optionally
with a deadline, to avoid that their site breaks. The fixes that affect a site
are listed in the build status
<span style="white-space: nowrap;">
(<i class="fa-circle-info tfa" style="color: var(--pst-color-info);"></i> /
<i class="fa-triangle-exclamation tfa"
   style="color: var(--pst-color-warning);"></i> /
<i class="fa-circle-xmark tfa" style="color: var(--pst-color-danger);"></i>
</span>
in the navbar), as well as in the terminal running the local server.

Fixes constitute a **communication channel** from t-doc developers to site
owners, about:

- [Latent issues](#latent-issues) that may become visible only later.
- [Backward-incompatible changes](#backward-incompatible-changes) that require
  timely changes in sites.

```{admonition} Thank you!
:class: tip
Applying fixes in a timely fashion reduces the load on both site owners and
developers. **Thank you for your diligence!**
```

### Latent issues

Some fixes detect issues that don't necessarily cause failing builds, but may
cause them later on (or in a different environment).

**Example:** [`bad-filename`](#bad-filename)

### Backward-incompatible changes

The t-doc developers sometimes need to make backward-incompatible changes to the
Sphinx extension. To **avoid breaking sites**, these changes are introduced in
multiple steps:

1.  New functionality is introduced in a backward-compatible way.
2.  All sites are updated to the new functionality.
3.  Old (unused) functionality is removed.

Historically, the developers used to take care of the whole process. But the
growing volume of content made this approach impractical. The work is now split
as follows:

- **Developers** still take care of (1) and (3).
- **Site owners** are responsible of (2).

The developers publish fixes on this page that describe the required changes,
and instrument the Sphinx extension to detect and report uses of functionality
to be removed. These fixes have a **deadline**, normally one month after (1) is
complete, after which the developers proceed with (3).

## Fixes

### `bad-filename`

This fix indicates that some files in the `docs/` directory have problematic
filenames. While these files may seem to work, they can cause issues across
platforms (e.g. Windows vs. Linux). The following characters are problematic:

- Non-printable: `0x00` - `0x1f`, `0x7f`
- Whitespace: `0x20` (space)
- Reserved: `"`, `*`, `/`, `:`, `<`, `>`, `?`, `\`, `|`
- Non-ASCII: `0x80` - `0x10ffff`

**Action:** Rename the listed files so that their names contain only
non-whitespace and non-reserved
[printable ASCII](https://en.wikipedia.org/wiki/ASCII#Printable_character_table)
characters.
