<!-- Copyright 2024 Remy Blank <remy@c-space.org> -->
<!-- SPDX-License-Identifier: MIT -->

# Embedding

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

## Youtube

### www.youtube.com

<iframe style="width: 100%; aspect-ratio: 16/9;"
  src="https://www.youtube.com/embed/aVwxzDHniEw?si=mBuOoRm8wMx88AAC"
  title="YouTube video player" frameborder="0"
  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope;
    picture-in-picture; web-share"
  referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

### www.youtube-nocookie.com

<iframe style="width: 100%; aspect-ratio: 16/9;"
  src="https://www.youtube-nocookie.com/embed/aVwxzDHniEw?si=mBuOoRm8wMx88AAC"
  title="YouTube video player" frameborder="0"
  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope;
    picture-in-picture; web-share"
  referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

### Credentialless

<iframe credentialless style="width: 100%; aspect-ratio: 16/9;"
  src="https://www.youtube.com/embed/aVwxzDHniEw?si=mBuOoRm8wMx88AAC"
  title="YouTube video player" frameborder="0"
  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope;
    picture-in-picture; web-share"
  referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>
