// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {domLoaded, elmt, on, qs, qsa, rgb2hex} from './core.js';
import {createDrauu} from '../drauu/index.mjs';

// Prevent doctools.js from capturing editor key events, in case keyboard
// shortcuts are enabled.
domLoaded.then(() => {
    if (typeof BLACKLISTED_KEY_CONTROL_ELEMENTS !== 'undefined') {
        BLACKLISTED_KEY_CONTROL_ELEMENTS.add('DIV');
    }
});

// Handle admonition expansion. The button is needed to enable keyboard focus.
domLoaded.then(() => {
    for (const el of qsa(document, '.admonition.dropdown')) {
        const title = qs(el, '.admonition-title')
        on(title).click(() => el.classList.toggle('expand'));
        // Enable keyboard navigation.
        on(title.appendChild(elmt`<button></button>`)).click(e => {
            el.classList.toggle('expand');
            e.stopPropagation();
        });
    }
});


// Handle the "draw" button.
let drawing;
globalThis.tdocDraw = () => {
    const ds = document.documentElement.dataset;
    if (ds.tdocDraw !== undefined) {
        delete ds.tdocDraw;
        return;
    }
    ds.tdocDraw = '';
    if (drawing) return;

    const markerFact = 8;
    function brushSize() {
        return drawing.brush.size
            / (drawing.brush.color.slice(7) !== 'ff' ? markerFact : 1)
    }
    function setBrush(opts) {
        const col = opts.color ?? drawing.brush.color.slice(0, 7);
        const tr = opts.transparent ?? (drawing.brush.color.slice(7) !== 'ff');
        const size = opts.size ?? brushSize();
        drawing.brush = {
            ...drawing.brush,
            color: col + (tr ? '40' : 'ff'),
            size: size * (tr ? markerFact : 1),
        };
    }

    const svg = qs(document, '.bd-content').appendChild(elmt`\
<svg id="tdoc-drawing" xmlns="http://www.w3.org/2000/svg"\
 xmlns:xlink="http://www.w3.org/1999/xlink"></svg>`);
    drawing = createDrauu({
        el: svg,
        brush: {mode: 'stylus', color: `#ff0000ff`, size: 3},
    });
    // TODO: Use mount() / unmount() in addition to data-tdoc-drawing
    // TODO: Don't capture 'keydown' events on window
    // TODO: Use bootstrap tooltips instead of title=
    const toolbar = qs(document, '.header-article-items__start')
        .appendChild(elmt`\
<div class="header-article-item tdoc-draw-toolbar">\
<input type="radio" name="tool" class="btn fa-pen" data-mode="stylus"\
 title="Stylus">\
<input type="radio" name="tool" class="btn fa-pencil" data-mode="draw"\
 title="Pencil">\
<input type="radio" name="tool" class="btn fa-pen-ruler" data-mode="line"\
 title="Line">\
<input type="radio" name="tool" class="btn fa-arrow-right"\
 data-mode="line" data-arrow="y" title="Arrow">\
<input type="radio" name="tool" class="btn fa-square"\
 data-mode="rectangle" title="Rectangle">\
<input type="radio" name="tool" class="btn fa-circle" data-mode="ellipse"\
 title="Ellipse">\
<input type="radio" name="tool" class="btn fa-eraser"\
 data-mode="eraseLine" title="Eraser">\
<button name="clear" class="btn fa-trash" title="Clear"></button>\
<input class="tdoc-size" type="range" min="1" max="8" step="1"\
 value="${brushSize()}" title="Size">\
<div class="tdoc-color dropdown-center">\
<button class="btn fa-square" title="Color" data-bs-toggle="dropdown"></button>\
<ul class="dropdown-menu">\
<li><a class="dropdown-item fa-square" style="color: #ff0000;"></a></li>\
<li><a class="dropdown-item fa-square" style="color: #008000;"></a></li>\
<li><a class="dropdown-item fa-square" style="color: #0000ff;"></a></li>\
<li><a class="dropdown-item fa-square" style="color: #00e0e0;"></a></li>\
<li><a class="dropdown-item fa-square" style="color: #ff00ff;"></a></li>\
<li><a class="dropdown-item fa-square" style="color: #f0f000;"></a></li>\
</ul>\
</div>\
<input type="checkbox" name="marker" class="btn fa-marker" title="Marker">\
</div>`);
    const toolBtns = qsa(toolbar, '[name=tool]');
    for (const el of toolBtns) {
        if (el.dataset.mode === drawing.mode
                && !!el.dataset.arrow === !!drawing.brush.arrowEnd) {
            el.checked = true;
        }
        el.addEventListener('click', e => {
            drawing.mode = e.target.dataset.mode;
            drawing.brush.arrowEnd = !!e.target.dataset.arrow;
        });
    }
    qs(toolbar, '[name=clear]').addEventListener('click', () => {
        drawing.clear();
    });
    qs(toolbar, '.tdoc-size').addEventListener('input', e => {
        setBrush({size: +e.target.value});
    });
    const colorButton = qs(toolbar, '.tdoc-color button');
    for (const el of qsa(toolbar, '.tdoc-color .dropdown-item')) {
        const color = rgb2hex(el.style.color);
        if (color == drawing.brush.color.slice(0, 7)) {
            colorButton.style.color = color;
        }
        el.addEventListener('click', () => {
            colorButton.style.color = color;
            setBrush({color});
        });
    }
    qs(toolbar, '[name=marker]').addEventListener('click', e => {
        setBrush({transparent: e.target.checked});
    });
};

// Handle the "terminate server" button.
globalThis.tdocTerminate = async ret => {
    await fetch(`${location.origin}/*terminate?r=${ret ?? 0}`,
                {method: 'POST', cache: 'no-cache', referrer: ''});
};

// Handle the "toggle solutions" button.
globalThis.tdocToggleSolutions = () => {
    const ds = document.documentElement.dataset;
    if (ds.tdocSolutions === 'hide') {
        delete ds.tdocSolutions;
    } else {
        ds.tdocSolutions = 'hide';
    }
};
