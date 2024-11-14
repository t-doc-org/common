% Copyright 2024 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Embedding

## Math

The equation $ax^2 + bx + c = 0$ has two solutions:

$$
&x_1=\frac{-b-\sqrt{D}}{2a}\quad\textrm{and}\quad x_2=\frac{-b+\sqrt{D}}{2a}\\
\\
&\textrm{with } D=b^2-4ac
$$

## SVG

<svg xmlns="http://www.w3.org/2000/svg"
     viewBox="0 0 100 100" width="100" height="100"
     stroke="red" fill="transparent">
  <path d="M -40,-20 A 20,20 0,0,1 0,-20 A 20,20 0,0,1 40,-20
           Q 40,10 0,40 Q -40,10 -40,-20 z"
        transform="translate(50 50) rotate(20)"/>
</svg>

## Graphviz

```{graphviz}
digraph {
    A -> B
    A -> C
    B -> D
    C -> D
}
```
