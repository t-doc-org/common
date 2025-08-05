% Copyright 2024 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Elements

## Document metadata

This section configures page metadata with a {rst:dir}`metadata` directive to
hide solutions by default.

```{metadata}
solutions: hide
```

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

## Flex tables

### Function value table

The {rst:dir}`flex-table` below uses the class `function-table` to render the
value table of $f(x)=2x+1$.

```{flex-table}
:class: function-table
|$x$|$0$|$1$|$2$|$3$|$4$
|$f(x)$|$1$|$3$|$5$|$7$|$9$
```

### Function sign table

The {rst:dir}`flex-table` below uses the class `function-table` to render the
sign table of $f(x)=\dfrac{\sqrt{-x+2}}{2x(2x+1)}$.

```{flex-table}
:class: function-table
|$x$|{.l .w}$\tiny-\;\infty$|$-\frac{1}{2}$|{.w}|$0$|{.w}|$2$|{.r .w}$\tiny+\;\infty$
|$\sqrt{-x+2}$|$+$||$+$||$+$|$0$|{.g}
|$2x$|$-$||$-$|{.g}$0$|$+$||$+$
|$2x+1$|$-$|{.g}$0$|$+$||$+$||$+$
|$\dfrac{\sqrt{-x+2}}{2x(2x+1)}$|$+$|{.g}|$-$|{.g}|$+$|$0$|{.g}
```

## IFrames

The [YouTube](https://youtube.com/) video below is embedded with the
{rst:dir}`youtube` directive.

```{youtube} aVwxzDHniEw
```

The presentation below is embedded with the {rst:dir}`iframe` directive.

```{iframe} https://docs.google.com/presentation/d/e/2PACX-1vQEemAMuCYvYvdxAJVRJBFD5NU8NQzasRyRpNau10iIVNGCpZSRgw_5dYTUd8EDhE8YyB_6v8b_2F37/embed?start=false&loop=false&delayms=3000
```

## Grid layouts

The {rst:dir}`list-grid` below creates a 2-column layout. A heading is used to
label the columns.

```{list-grid}
:style: grid-template-columns: 5fr 3fr;
- # Cell 1
  Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do
  eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad
  minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip
  ex ea commodo consequat. Duis aute irure dolor in reprehenderit in
  voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur
  sint occaecat cupidatat non proident, sunt in culpa qui officia
  deserunt mollit anim id est laborum.
- # Cell 2
  |Key|Value|
  |:-:|:---:|
  |a|1|
  |b|2|
  |c|3|
```

## Numbering

This sections uses the {rst:role}`num` role to create numbered sub-sections that
reference each other with the {rst:role}`numref` role, and separately numbered
unreferenced quotes using {rst:role}`nump`.

### Exercise {num}`ex:first`

Read these quotes, then move on to exercises {numref}`ex:second` &
{numref}`ex:third`.

{attribution="Terry Pratchett, Mort"}
> **Quote {nump}`quote`:** "It would seem that you have no useful skill or talent
> whatsoever," he said. "Have you thought of going into teaching?""

{attribution="Terry Pratchett, Hogfather"}
> **Quote {nump}`quote`:** Real stupidity beats artificial intelligence every
> time.

### Exercise {num}`ex:second`

You've already read the quotes from {numref}`exercise %s<ex:first>`. Read this
one as well, then go to {numref}`exercise %s<ex:third>`.

{attribution="Douglas Adams, The Hitchhiker’s Guide to the Galaxy"}
> **Quote {nump}`quote`:** For a moment, nothing happened. Then, after a second
> or so, nothing continued to happen.

### Exercise {num}`ex:third`

This is the last quote.

{attribution="Iain M. Banks, Consider Phlebas"}
> **Quote {nump}`quote`:** I had nightmares I thought were really horrible until
> I woke up and remembered what reality was at the moment.

## Blocks

The sections below define exercises where the solutions are defined next to
their exercise in the source document using {rst:dir}`block` directives, and
grouped together at the bottom with a {rst:dir}`blocks` directive. The exercises
are numbered with the {rst:role}`num` role.

### Exercises

#### Exercise {num}`block-ex:a`

This is exercise {numref}`block-ex:a`.

```{block} solution
This is the solution to exercise {numref}`block-ex:a`.
```

#### Exercise {num}`block-ex:b`

This is exercise {numref}`block-ex:b`.

```{block} solution
This is the solution to exercise {numref}`block-ex:b`.
```

#### Exercise {num}`block-ex:c`

This is exercise {numref}`block-ex:c`.

```{block} solution
This is the solution to exercise {numref}`block-ex:c`.
```

### Solutions

```{blocks} solution
```
