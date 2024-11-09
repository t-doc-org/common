% Copyright 2024 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Directives

## Document metadata

This section configures page metadata with a {rst:dir}`metadata` directive to
hide solutions by default.

```{metadata}
hide-solutions: true
```

## Solution

This section has several {rst:dir}`solution` blocks, and the page is
configured to hide solutions by default. Click the "Toggle solutions" button in
the navbar to show or hide them.

```{solution}
This solution follows the per-page setting.
```

```{solution} Solution (show)
:show:
This solution is always visible.
```

```{solution} *Complete* solution
This solution has a custom title.
```

```{solution}
:class: warning
This solution has a different color, and no drop-down.
```
