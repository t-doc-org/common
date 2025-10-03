% Copyright 2025 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Layout

## Spacing

The quick brown fox {hspace}`3em` jumps over {hspace}`3em` the lazy dog.

1.  Write the chemical formula for acetic acid.
    {vspace}`2lh`
2.  Write the chemical equation of the synthesis of water.
    {vspace}`2lh`

## Leaders

{.lower-alpha-paren .vsep-2}
1.  $(x-1)(x+2)=$ {leader}`.`
2.  Which property did you use above? {leader}`_`
3.  The {leader}`.|6em` brown {leader}`_|6em` jumps over the {leader}`dot|6em`
    dog.
4.  Describe the main components of a computer.
    {leader}`.|100%`{leader}`.|100%`{leader}`.|100%`

## Numbering & points

This sections uses the {rst:role}`num` role to create numbered sub-sections that
reference each other with the {rst:role}`numref` role, and separately numbered
unreferenced quotes using {rst:role}`nump`. It also assigns points to each
sub-section with the {rst:role}`points` role, and displays a points table at the
top.

<style>
table.points > thead > tr > th {
  min-width: 3rem;
}
</style>

```{flex-table}
:class: points grid align-left
{t=h}|{.l}Exercise    |{points=label}|Total
{t=b}|{t=h .l}Points  |{points=value}|{points=sum}
     |{t=h .l}Obtained|{points=empty}|
```

### Exercise {num}`ex:first`{points}`2.5`

Read these quotes, then move on to exercises {numref}`ex:second` &
{numref}`ex:third`.

{attribution="Terry Pratchett, Mort"}
> **Quote {nump}`quote`:** "It would seem that you have no useful skill or talent
> whatsoever," he said. "Have you thought of going into teaching?""

{attribution="Terry Pratchett, Hogfather"}
> **Quote {nump}`quote`:** Real stupidity beats artificial intelligence every
> time.

### Exercise {num}`ex:second`{points}`1`

You've already read the quotes from {numref}`exercise %s<ex:first>`. Read this
one as well, then go to {numref}`exercise %s<ex:third>`.

{attribution="Douglas Adams, The Hitchhiker’s Guide to the Galaxy"}
> **Quote {nump}`quote`:** For a moment, nothing happened. Then, after a second
> or so, nothing continued to happen.

### Exercise {num}`ex:third`{points}`2`

This is the last quote.

{attribution="Iain M. Banks, Consider Phlebas"}
> **Quote {nump}`quote`:** I had nightmares I thought were really horrible until
> I woke up and remembered what reality was at the moment.

### Bonus {num}`bonus`{points}`1!:B{0}`

{attribution="Martha Wells, Network Effect"}
> **Quote {nump}`quote`:** "Can I ask you a question?" I never know how to
> answer this. Should I go with my first impulse, which is always "no" or just
> give in to the inevitable?

### Bonus {num}`bonus`{points}`0.5!:B{0}`

{attribution="Neal Stephenson, Anathem"}
> **Quote {nump}`quote`:** Technically, of course, he was right. Socially, he
> was annoying us.

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

## Admonitions


````{admonition} Horizontal alignment
:class: note dropdown expand
The `pydata_sphinx_theme` CSS breaks the layout of its content, in particular
horizontal alignment. We fix it by patching the CSS file after copying the
asset.

- Item 1
- Item 2

# Math

```{math}
:class: align-left
x_{1,2}=\frac{-b\pm\sqrt{b^2-4ac}}{2a}
```
```{math}
:class: align-center
x_{1,2}=\frac{-b\pm\sqrt{b^2-4ac}}{2a}
```
```{math}
:class: align-right
x_{1,2}=\frac{-b\pm\sqrt{b^2-4ac}}{2a}
```

# Tables

```{flex-table}
:class: grid align-left
{t=h}|$x$|0|1|2|3
{t=b}|{t=h}$f(x)$|1|3|5|7
```
```{flex-table}
:class: grid
{t=h}|$x$|0|1|2|3
{t=b}|{t=h}$f(x)$|1|3|5|7
```
```{flex-table}
:class: grid align-right
{t=h}|$x$|0|1|2|3
{t=b}|{t=h}$f(x)$|1|3|5|7
```

```{flex-table}
:class: function-table
|$x$|$0$|$1$|$2$|$3$
|$f(x)$|$1$|$3$|$5$|$7$
```
```{flex-table}
:class: function-table align-center
|$x$|$0$|$1$|$2$|$3$
|$f(x)$|$1$|$3$|$5$|$7$
```
```{flex-table}
:class: function-table align-right
|$x$|$0$|$1$|$2$|$3$
|$f(x)$|$1$|$3$|$5$|$7$
```

# JSXGraph

```{jsxgraph}
:template: grid(35, 2)
:style: width: 50%;
:class: align-left
```
```{jsxgraph}
:template: grid(35, 2)
:style: width: 50%;
:class: align-middle
```
```{jsxgraph}
:template: grid(35, 2)
:style: width: 50%;
:class: align-right
```

# Mermaid

```{mermaid}
:class: align-left
config:
  flowchart:
    curve: linear
---
flowchart LR;
    node(Node)
```
```{mermaid}
config:
  flowchart:
    curve: linear
---
flowchart LR;
    node(Node)
```
```{mermaid}
:class: align-right
config:
  flowchart:
    curve: linear
---
flowchart LR;
    node(Node)
```
````
