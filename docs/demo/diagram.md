% Copyright 2024 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Diagrams

```{metadata}
mermaid:
  theme: forest
```

## Mermaid

The default theme is set in the page {rst:dir}`metadata`.

### Flowchart

([Documentation](https://mermaid.js.org/syntax/flowchart.html))

This flowchart has links and tooltips on the boxes.

```{mermaid}
title: t-doc.org site structure
config:
  flowchart:
    curve: linear
    nodeSpacing: 20
    padding: 10
---
flowchart LR;
    root(t-doc.org)
    common(common)
    maths(maths)
    informatique(informatique)

    root --> common & maths & informatique

    click root "https://t-doc.org/" "Home page"
    click common "https://common.t-doc.org/" "Theme & extension"
    click maths "https://maths.t-doc.org/" "Math course"
    click informatique "https://informatique.t-doc.org/" "Computer science course"
```

This flowchart has labels on the edges, sets the theme in the frontmatter with a
static background, and has a hand-drawn look.

```{mermaid}
:class: background-light
title: How to repair a lamp
config:
  theme: default
  look: handDrawn
---
flowchart TD
  A(["Lamp doesn't work"]) --> B{"Lamp<br>plugged in?"}
  B -->|No| C(["Plug in lamp"])
  B -->|Yes| D{"Bulb<br>burned out?"}
  D -->|Yes| E(["Replace bulb"])
  D -->|No| F(["Repair lamp"])
```

### Entity relationship diagram

([Documentation](https://mermaid.js.org/syntax/entityRelationshipDiagram.html))

```{mermaid}
erDiagram
  direction LR
  customer ||--o{ order : places
  customer {
    string name
    integer custNumber
    string sector
  }
  order ||--|{ item : contains
  order {
    integer orderNumber
    string deliveryAddress
  }
  item {
    string productCode
    integer quantity
    real pricePerUnit
  }
```

### Pie chart

([Documentation](https://mermaid.js.org/syntax/pie.html))

```{mermaid}
width: 100
config:
  pie:
    useWidth: 10
---
pie title Pets adopted by volunteers
  "Dogs" : 386
  "Cats" : 85
  "Rats" : 15
```

### XY chart

([Documentation](https://mermaid.js.org/syntax/xyChart.html))

```{mermaid}
config:
  xyChart:
    height: 400
    xAxis:
      labelPadding: 10
    yAxis:
      labelPadding: 20
---
xychart
    title "Sales Revenue"
    x-axis [jan, feb, mar, apr, may, jun, jul, aug, sep, oct, nov, dec]
    y-axis 0 --> 11000
    bar [5000, 6000, 7500, 8200, 9500, 10500, 11000, 10200, 9200, 8500, 7000, 6000]
    line [5000, 6000, 7500, 8200, 9500, 10500, 11000, 10200, 9200, 8500, 7000, 6000]
```

## Graphviz

```{graphviz}
:class: align-center
digraph {
    A -> B
    A -> C
    B -> D
    C -> D
}
```
