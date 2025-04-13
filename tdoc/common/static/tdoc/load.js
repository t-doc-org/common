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
    const opacity = 'ff';
    const svg = qs(document, '.bd-content').appendChild(elmt`\
<svg id="tdoc-drawing" xmlns="http://www.w3.org/2000/svg"\
 xmlns:xlink="http://www.w3.org/1999/xlink"></svg>`);
    drawing = createDrauu({
        el: svg,
        brush: {mode: 'stylus', color: `#ff0000${opacity}`, size: 3},
    });
    // TODO: Button: transparent
    // TODO: Button: clear
    // TODO: Use mount() / unmount() in addition to data-tdoc-drawing
    // TODO: Don't capture 'keydown' events on window
    const toolbar = qs(document, '.header-article-items__start')
        .appendChild(elmt`\
<div class="header-article-item tdoc-draw-toolbar">\
<input type="radio" name="tool" class="tdoc btn fa-pen" data-mode="stylus"\
 title="Stylus">\
<input type="radio" name="tool" class="tdoc btn fa-pencil" data-mode="draw"\
 title="Pencil">\
<input type="radio" name="tool" class="tdoc btn fa-pen-ruler" data-mode="line"\
 title="Line">\
<input type="radio" name="tool" class="tdoc btn fa-arrow-right"\
 data-mode="line" data-arrow="y" title="Arrow">\
<input type="radio" name="tool" class="tdoc btn fa-square"\
 data-mode="rectangle" title="Rectangle">\
<input type="radio" name="tool" class="tdoc btn fa-circle" data-mode="ellipse"\
 title="Ellipse">\
<input type="radio" name="tool" class="tdoc btn fa-eraser"\
 data-mode="eraseLine" title="Eraser">\
<input class="tdoc-size" type="range" min="1" max="25" step="0.5"\
 value="${drawing.brush.size}" title="Size">\
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
    qs(toolbar, '.tdoc-size').addEventListener('input', e => {
        // TODO: Make scale exponential
        drawing.brush.size = +e.target.value;
    });
    const colorButton = qs(toolbar, '.tdoc-color button');
    for (const el of qsa(toolbar, '.tdoc-color .dropdown-item')) {
        const color = rgb2hex(el.style.color);
        if (color == drawing.brush.color.slice(0, 7)) {
            colorButton.style.color = color;
        }
        el.addEventListener('click', () => {
            colorButton.style.color = color;
            drawing.brush.color = color + opacity;
        });
    }
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
