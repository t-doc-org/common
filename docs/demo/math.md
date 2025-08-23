% Copyright 2025 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Math

## Math notation

The equation $ax^2 + bx + c = 0$ has two solutions in $\mathbb{C}$:

$$
&x_1=\frac{-b-\sqrt{D}}{2a}\quad\textrm{and}\quad x_2=\frac{-b+\sqrt{D}}{2a}\\
\\
&\textrm{with } D=b^2-4ac
$$

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

## JSXGraph

This section renders live graphs using {rst:dir}`jsxgraph` directives. The
graphs are interactive: some points can be dragged, and some of the graphs can
be panned and zoomed by holding {kbd}`Shift`.

### Sine and cosine

```{jsxgraph} sincos
:style: aspect-ratio: 16 / 9;
```

### Centroid

Drag the points $P_1$, $P_2$ and $P_3$.

```{jsxgraph} centroid
:style: width: 50%;
```

### Trigonometric circle

Drag the point $P$ on the circle.

```{jsxgraph} trig-circle
```

<script type="module">
const [{initBoard, JXG}] = await tdoc.imports('tdoc/jsxgraph.js');

initBoard('sincos', {
    boundingBox: [-7, 1.3, 7, -1.3], keepAspectRatio: false,
    axis: true, grid: true,
    defaults: {
        functiongraph: {
            withLabel: true,
            label: {
                distance: 1.5,
                offset: [0, 0],
                anchorX: 'middle',
                anchorY: 'middle',
            },
        },
    },
}, board => {
    board.create('functiongraph',
        [x => Math.sin(x)],
        {name: `\\(sin(x)\\)`, strokeColor: JXG.palette.blue,
         label: {position: '0.6fr left'}});
    board.create('functiongraph',
        [x => Math.cos(x)],
        {name: `\\(cos(x)\\)`, strokeColor: JXG.palette.red,
         label: {position: '0.69fr right'}});
});

initBoard('centroid', {
    boundingBox: [-3.2, 3.2, 3.2, -3.2],
    defaults: {
        line: {strokeWidth: 1.5},
    },
}, board => {
    const is = [0, 1, 2];
    const p = is.map(i => board.create('point',
        [3 * Math.cos(i * 2 * Math.PI / 3) + 0.5 * (i - 1),
         3 * Math.sin(i * 2 * Math.PI / 3)],
        {name: `\\(P_${i + 1}\\)`}));
    is.map(i => board.create('segment',
        [p[i], p[(i + 1) % 3]], {strokeColor: JXG.palette.black}));
    const m = is.map(i => board.create('midpoint',
        [p[(i + 1) % 3], p[(i + 2) % 3]], {name: `\\(M_${i + 1}\\)`}));
    const med = is.map(i => board.create('segment',
        [p[i], m[i]], {strokeColor: JXG.palette.blue}));
    board.create('intersection', [med[0], med[1]], {name: '\\(C\\)'});
});

initBoard('trig-circle', {
    boundingBox: [-1.5, 6.5, 6.5, -1.5], axis: true,
    pan: {enabled: false}, zoom: {enabled: false}, showFullscreen: true,
    defaultAxes: {
        x: {
            name: '\\(x, \\alpha\\)',
            ticks: {insertTicks: false, ticksDistance: 1, minorTicks: 0},
        },
        y: {
            name: '\\(y, \\alpha\\)',
            ticks: {insertTicks: false, ticksDistance: 1, minorTicks: 0},
        },
    },
    defaults: {
        point: {strokeWidth: 0},
        line: {strokeWidth: 1},
    },
}, board => {
    // Place the circle.
    const c = board.create('circle', [[0, 0], 1], {
        strokeColor: JXG.palette.black,
    });

    // Place the glider point and everything related to the angle.
    const alphaColor = JXG.palette.green;
    const attractors = [];
    for (let i = 0; i < 4; ++i) {
        for (const a of [0, Math.PI / 6, Math.PI / 4, Math.PI / 3]) {
            const b = i * Math.PI / 2 + a;
            attractors.push(board.create('point', [Math.cos(b), Math.sin(b)], {
                fixed: true, visible: false, withLabel: false,
            }));
        }
    }
    const p = board.create('glider', [0.85, -0.5, c], {
        name: '\\(P\\)', label: {strokeColor: alphaColor},
        fillColor: alphaColor, attractors, attractorDistance: 0.1,
    });
    const alpha = () => {
        const a = Math.atan2(p.Y(), p.X());
        return a >= 0 ? a : a + 2 * Math.PI;
    };
    const ax1 = board.create('point', [1, 0], {
        fixed: true, visible: false, withLabel: false,
    });
    board.create('angle', [ax1, [0, 0], p], {
        name: '\\(\\alpha\\)', label: {strokeColor: alphaColor},
        radius: 0.2, orthoType: 'none',
        strokeColor: alphaColor, fillColor: alphaColor, fillOpacity: 0.3,
    });
    board.create('segment', [[0, 0], p], {strokeColor: alphaColor});
    board.create('text',
        [2, 6, () => `\
\\(\\alpha=${alpha().toFixed(2)}\\;rad\
=${(alpha() * 180 / Math.PI).toFixed(1)}\\degree\\)`], {
            strokeColor: alphaColor, fixed: true,
    });

    // Project the glider point onto the axes.
    const px = [() => p.X(), 0];
    const py = [0, () => p.Y()];
    board.create('segment', [p, px], {dash: 2, strokeColor: JXG.palette.black});
    board.create('segment', [p, py], {dash: 2, strokeColor: JXG.palette.black});

    // Place the elements related to the sine.
    const sinColor = JXG.palette.blue;
    board.create('arrow', [[0, 0], py], {
        name: '\\(sin(\\alpha)\\)', withLabel: true,
        label: {
            position: '0.5fr left', anchorX: 'right', anchorY: 'middle',
            distance: 0, offset: [-7, 0], strokeColor: sinColor,
        },
        strokeWidth: 2, strokeColor: sinColor,
    });
    board.create('curve', [a => a, a => Math.sin(a), 0, 2 * Math.PI], {
        strokeColor: sinColor,
    });
    const psin = board.create('point', [alpha, () => p.Y()], {
        withLabel: false, fillColor: sinColor,
    });
    board.create('segment', [p, psin], {
        dash: 2, strokeColor: JXG.palette.black,
    });
    const ax = board.create('point', [alpha, 0], {
        name: '\\(\\alpha\\)', size: 0, label: {strokeColor: alphaColor},
    });
    board.create('segment', [psin, ax], {
        dash: 2, strokeColor: JXG.palette.black,
    });
    board.create('text',
        [2, 5.7, () => `\\(sin(\\alpha)=${Math.sin(alpha()).toFixed(3)}\\)`], {
        strokeColor: sinColor, fixed: true,
    });

    // Place the elments related to the cosine.
    const cosColor = JXG.palette.red;
    board.create('arrow', [[0, 0], px], {
        name: '\\(cos(\\alpha)\\)', withLabel: true,
        label: {
            position: '0.5fr right', anchorX: 'middle', anchorY: 'top',
            distance: 0, offset: [0, -7], strokeColor: cosColor,
        },
        strokeWidth: 2, strokeColor: cosColor,
    });
    board.create('curve', [a => Math.cos(a), a => a, 0, 2 * Math.PI], {
        strokeColor: cosColor,
    });
    const pcos = board.create('point', [() => p.X(), alpha], {
        withLabel: false, fillColor: cosColor,
    });
    board.create('segment', [p, pcos], {
        dash: 2, strokeColor: JXG.palette.black,
    });
    const ay = board.create('point', [0, alpha], {
        name: '\\(\\alpha\\)', size: 0, label: {strokeColor: alphaColor},
    });
    board.create('segment', [ay, pcos], {
        dash: 2, strokeColor: JXG.palette.black,
    });
    board.create('text',
        [2, 5.4, () => `\\(cos(\\alpha)=${Math.cos(alpha()).toFixed(3)}\\)`], {
        strokeColor: cosColor, fixed: true,
    });
});
</script>
