% Copyright 2026 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Configuration

```{role} py(code)
:language: python
```

## Sphinx configuration

The Sphinx configuration is located in the file `docs/conf.py`. The options that
aren't specific to t-doc are described in the Sphinx documentation
([configuration](https://www.sphinx-doc.org/en/master/usage/configuration.html),
[extensions](https://www.sphinx-doc.org/en/master/usage/extensions/index.html)).
t-doc defines additional options described below.

t-doc provides defaults for many options in the
[`tdoc.common.defaults`](https://github.com/t-doc-org/common/blob/main/tdoc/common/defaults.py)
module, which is intended to be wildcard-imported into `conf.py`.

```{code-block} python
from tdoc.common.defaults import *
```

```{confval} license
:type: {py}`str`
:default: {py}`""`
The license under which the site content is distributed.
```

```{confval} license_url
:type: {py}`str`
:default: Set automatically for some licenses, {py}`""` otherwise.
The URL of a page showing the full content of the license under which the site
content is distributed.
```

```{confval} tdoc
:type: {py}`dict`
:default: {py}`{}`
A {py:class}`dict` that is converted to JSON and made available to JavaScript
as `tdoc.conf`.
```

```{confval} tdoc_api
:type: {py}`str`
:default: {py}`""`
The base URL of the t-doc API server. When empty, the URL is set automatically
for `t-doc.org` and its subdomains.
```

```{confval} tdoc_repos
:type: {py}`str`
:default: {py}`"https://rc.t-doc.org/"`
The base URL of the site repositories.
```

```{confval} tdoc_domain_storage
:type: {py}`str`
:default: {py}`{}`
t-doc sites are deployed as sub-domains (e.g. `common.t-doc.org`) of an apex
domain (e.g. `t-doc.org`). The apex site provides access to a subset of its
`localStorage` to sub-domains, e.g. for login information. This option
configures the domain-wide storage; the following keys can be set:

- `origin`: The origin of the apex domain (default: `https://t-doc.org`). This
  option must be set on all sites.
- `allowed_origins`: A regexp matching origins that are allowed to read and
  write to domain-wide storage. This option must be set on the apex site.
- `allowed_keys`: The storage keys that can be read and written. This option
  must be set on the apex site.

See the
[configuration for `t-doc.org`](https://github.com/t-doc-org/t-doc-org.github.io/blob/main/docs/conf.py)
for an example.
```

```{confval} tdoc_enable_sab
:type: {py}`str`, one of `no`, `cross-origin-isolation`, `sabayon`
:default: {py}`"no"`
The strategy to use to work around the absence of `SharedArrayBuffer`.
- `no`: Don't set up a workaround.
- `cross-origin-isolation`: Install a service worker that adds cross-origin
  isolation headers.
- `sabayon`: Install a service worker running
  [Sabayon](https://github.com/WebReflection/sabayon).
```

## CLI and API configuration

The `tdoc` CLI and the API server read their configuration from a
[TOML](https://toml.io/en/) file.

- By default, the CLI looks for a file named `tdoc.local.toml` starting in the
  current directory and moving up the hierarchy. The default can be overridden
  with the `--config` option or the `TDOC_CONFIG` environment variable.
- The API server reads the file `tdoc.local.toml` at the root of the `common`
  repository.

If not specified otherwise, configuration values that represent paths interpret
relative paths as relative to the directory containing the config file.

### `[import-files]`

This table defines files to be copied from outside the repository. The files are
copied by the local server whenever they change. This allows keeping sets of
files in sync between repositories, while keeping the repositories hermetic.

The keys of the `[import-files]` table determine the destination directory below
`docs/_import` into which the files are copied (using the same hierarchy as the
source), and the values define the source files.

- Table values use the following keys:
  - `src`: The path to the directory containing the source files. Relative paths
    are interpreted relative to the directory containing the config file.
  - `include`: An array of
    [glob patterns](https://docs.python.org/3/library/pathlib.html#pattern-language)
    matching paths relative to `src` of files to include in the import.
  - `exclude`: An array of
    [glob patterns](https://docs.python.org/3/library/pathlib.html#pattern-language)
    matching paths relative to `src` of files to exclude from the import. If a
    file matches both `include` and `exclude`, then it isn't imported.

- String values are a shortcut for:

  ```{code-block} toml
  KEY = {src = "VALUE", include = ["**/*.export/**', '**/*.export.*"], exclude = ["_import/**"]}
  ```

**Example:**

```{code-block} toml
:caption: `site1/tdoc.local.toml`
[import-files]
site2 = "../site2/docs"
```

### `[logging]`

This table configures the logging subsystem.

- `level` (default: `"NOTSET"`): The overall
  [log level](https://docs.python.org/3/library/logging.html#logging-levels).
- `transport` (default: `"queue"`): Either `"queue"` to run the log handlers in
  a separate thread and passing log records via a queue, or `"none"` to run the
  log handlers in-line with the log statements.

### `[[logging.databases]]`

These tables define logging handlers that store records in a SQLite database.

- [Common database options](#common-database-options)
- `enabled` (default: `true`): Enables or disables the handler.
- `level` (default: `"NOTSET"`): The
  [log level](https://docs.python.org/3/library/logging.html#logging-levels)
  for this handler.
- `flush_interval` (default: `5`): The interval in seconds at which queued log
  records are flushed to the database.
- `purge_interval` (default: `"1h"`): The interval at which stored log records
  that are out of retention are removed from the database.
- `retain` (default: `"90d"`): The stored log record retention. Log records that
  are older than the retention are remove from the database.

### `[[logging.files]]`

These tables define logging handlers that store records in text files.

- `compress` (default: `true`): When `true`, compress log files after rotation.
- `enabled` (default: `true`): Enables or disables the handler.
- `format` (default: `"{asctime} {ilevel} [{ctx:20}] [{module}] {message}"`):
  The {}-based
  [format string](https://docs.python.org/3/library/logging.html#logrecord-attributes)
  to use for writing to the file.
- `level` (default: `"NOTSET"`): The
  [log level](https://docs.python.org/3/library/logging.html#logging-levels)
  for this handler.
- `path`: The path to the log file.
- `rotate`: The log file
  {py:class}`rotation parameters <logging.handlers.TimedRotatingFileHandler>`,
  as a table with the following keys:
  - `when` (default: `"W6"`): The type of rotation interval.
  - `interval` (default: `1`): The number of intervals after which to rotate the
    log file.
  - `keep` (default: `4`): The number of rotated files to keep.

### `[logging.stream]`

This table configures the logging handler that outputs log records to `stderr`.

- `enabled` (default: `true`): Enables or disables the handler.
- `format` (default: `"{ilevel} [{ctx:20}] {message}"`): The {}-based
  [format string](https://docs.python.org/3/library/logging.html#logrecord-attributes)
  to use for output.
- `level` (default: `"NOTSET"`): The
  [log level](https://docs.python.org/3/library/logging.html#logging-levels)
  for this handler.

### `[oidc.token]`

This table configures options related to
[JSON Web Tokens](https://openid.net/developers/how-connect-works/) (JWT).

- `algorithms` (default: `["RS256"]`): The set of JWT signature algorithms to
  accept.
- `verify_leeway_secs` (default: `60`): The maximum clock skew in seconds to
  accept when verifying JWTs.

### `[[oidc.issuers]]`

These tables configure [OIDC](https://openid.net/developers/how-connect-works/)
issuers.

- `enabled` (default: `true`): Enables or disables an issuer.
- `client_id`: The client ID to use when communicating with the issuer.
- `client_secret`: The client secret to use when communicating with the issuer.
- `create_users`: An array of spec tables that define how to auto-create t-doc
  users from OIDC tokens. When an unknown user tries to log in, their OIDC token
  is matched against the claims in this array. The first matching entry causes
  a new t-doc user to be created. If no entries match, the login is rejected.
  - `claims`: A table whose keys specify OIDC token keys, and values specify the
    allowed token values. String values are regexps matched against the token
    value. Other value types are compared for equality.
  - `username`: The key of the OIDC token whose value should be used as the new
    user's username.
- `issuer`: The issuer URI.
- `label`: The label to use for the issuer in the login dialog.

The following example defines a Google issuer, with automatic user creation for
users in the `example.com` domain whose email was verified, using their email
address as a username.

```{code-block} toml
[[oidc.issuers]]
label = "Google"
issuer = "https://accounts.google.com"
client_id = "123456789012-a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6.apps.googleusercontent.com"
client_secret = "GOCSPX-0123456789abcdefghijklmnopqr"
create_users = [
   {claims = {hd = 'example\.com', email_verified = true}, username = "email"},
]
```

### `[repo]`

This table configures options related to repository access.

- `bcrypt_rounds` (default: `10`): The number of rounds to use when encrypting
  generated repository passwords with bcrypt.

### `[store]`

This table configures the database that stores site and user data.

- [Common database options](#common-database-options)
- `poll_interval` (default: `1`): The interval in seconds at which to poll the
  database for cross-process notifications.

### Common database options

- `path`: The path to the database file.
- `pool_size` (default: `16`): The size of the read connection pool.
- `pragma`: A table of pragmas to set on database connections.
- `timeout` (default: `5`): The timeout in seconds for waiting for a locked
  database.
- `write_isolation_level` (default: `"immediate"`): The transaction behavior;
  one of `"deferred"`, `"exclusive"` or `"immediate"`.

## `run.py` configuration

The `run.py` script fetches its [TOML](https://toml.io/en/) configuration from
[`config/run.toml`](https://github.com/t-doc-org/common/blob/main/config/run.toml)
in the `common` repository, and merges it with two optional files located in the
same directory as the script, `run.toml` (versioned) and `run.local.toml`
(unversioned). The local files override the remote one.

### Top-level keys

- `hermetic`: When `true`, install the exact versions specified by the versioned
  [requirements files](https://github.com/t-doc-org/common/blob/main/config/).
  When `false`, only specify the version of the package itself, but not of its
  dependencies.
- `package`: The name of the Python package to use.
- `version`: The version of the Python package to use, either a version or a tag
  listed in the `[tags]` table, or `"dev"` to use an editable package (only
  relevant for the `common` repository).

### `[defaults]`

- `command`: The default command and arguments to use when no command is
  specified.
- `command_*`: Additional arguments to append to `command`. The values are
  appended in key order.
- `command-dev`: The default command and arguments to use when no command is
  specified, and `version` is `"dev"`.
- `command-dev_*`: Additional arguments to append to `command-dev`. The values
  are appended in key order.

### `[tags]`

This table defines tags that can be used in `version`, typically to define
release tracks. The keys are tag names, and the values are the versions
corresponding to the tag.
