% Copyright 2024 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Elements

```{metadata}
solutions: hide
```

## SVG

<svg xmlns="http://www.w3.org/2000/svg"
     viewBox="0 0 100 100" width="100" height="100"
     stroke="red" fill="transparent">
  <path d="M -40,-20 A 20,20 0,0,1 0,-20 A 20,20 0,0,1 40,-20
           Q 40,10 0,40 Q -40,10 -40,-20 z"
        transform="translate(50 50) rotate(20)"/>
</svg>

## Solutions

This section has several {rst:dir}`solution` blocks, and the page is
configured to hide solutions by default. Click the
<span class="tdoc fa-eye"></span> / <span class="tdoc fa-eye-slash"></span>
button in the navbar to show or hide them.

```{solution}
This solution follows the per-page setting.
```

```{solution} *Complete* solution
This solution has a custom title.
```

```{solution} Solution (show)
:show:
This solution is always visible.
```

```{solution} Solution (expand)
:expand:
This solution is expanded by default.
```

```{solution}
:class: warning
This solution has a different color, and no drop-down.
```

## IFrames

The presentation below is embedded with the {rst:dir}`iframe` directive.

```{iframe} https://docs.google.com/presentation/d/e/2PACX-1vQEemAMuCYvYvdxAJVRJBFD5NU8NQzasRyRpNau10iIVNGCpZSRgw_5dYTUd8EDhE8YyB_6v8b_2F37/embed?start=false&loop=false&delayms=3000
```

The [YouTube](https://youtube.com/) video below is embedded with the
{rst:dir}`youtube` directive.

```{youtube} aVwxzDHniEw
```

## Tables

<style>
.table.reset.table-example :is(th, td) {
  border-width: 1px;
  padding: 0.2rem 0.5rem;
}
.table.reset.table-example th {
  border-bottom-width: 2px;
}
.table.reset.table-example :is(th, td):first-child {
  width: 0;
  border-right-width: 2px;
}
@media screen {
  .table.reset-print.table-example-print :is(th, td):first-child {
    width: 0;
    border-right: 2px solid var(--pst-color-primary);
  }
}
@media print {
  .table.reset-print.table-example-print :is(th, td) {
    border: 1px solid black;
    padding: 0.2rem 0.5rem;
  }
  .table.reset-print.table-example-print th {
    border-bottom-width: 2px;
  }
  .table.reset-print.table-example-print :is(th, td):first-child {
    width: 0;
    border-right-width: 2px;
  }
}
</style>

This table is a normal Markdown table and gets styled via the `table` class.
These styles are reset by applying the `reset` class, then overridden via an
embedded stylesheet. Note that the CSS rules for the `reset` class have
[specificity](https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Cascade/Specificity)
(0, 2, x), so **the overrides need to have specificity (0, 3, x)**. This can be
achieved e.g. by adding a custom class to identify the table (`table-example`
here), then specify all three classes in the override rules
(`.table.reset.table-example`).

{.reset .table-example}
|           | $A$ | $B$ | $C$ |
| :-------- | :-: | :-: | :-: |
| $x$       |     |     |     |
| $y$       |     |     |     |
| $f(x, y)$ |     |     |     |

The next table is also a normal Markdown table, but its styles are reset for
print media only by applying the `reset-print` class, then overridden. On screen
it looks like a normal table.

{.reset-print .table-example-print}
|           | $A$ | $B$ | $C$ |
| :-------- | :-: | :-: | :-: |
| $x$       |     |     |     |
| $y$       |     |     |     |
| $f(x, y)$ |     |     |     |
