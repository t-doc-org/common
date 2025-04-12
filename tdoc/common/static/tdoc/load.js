// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {domLoaded, elmt, on, qs, qsa} from './core.js';
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
    if (ds.tdocDraw === 'active') {
        delete ds.tdocDraw;
        return;
    }
    ds.tdocDraw = 'active';
    if (drawing) return;
    const svg = qs(document, '.bd-content').appendChild(elmt`\
<svg id="tdoc-drawing" xmlns="http://www.w3.org/2000/svg" \
 xmlns:xlink="http://www.w3.org/1999/xlink"></svg>`);
    drawing = createDrauu({
        el: svg,
        brush: {mode: 'stylus', color: 'red', size: 3},
    });
    // TODO: Make tools radio buttons, or maybe a select
    // TODO: Button: clear
    // TODO: Colors, as a select
    // TODO: Don't capture 'keydown' events on window
    const toolbar = qs(document, '.header-article-items__start')
        .appendChild(elmt`\
<div class="header-article-item tdoc-draw-toolbar">\
<button class="tdoc-tool-stylus fa-pen" data-mode="stylus"\
 title="Stylus"></button>\
<button class="tdoc-tool-draw fa-pencil" data-mode="draw"\
 title="Pencil"></button>\
<button class="tdoc-tool-line fa-pen-ruler" data-mode="line"\
 title="Line"></button>\
<button class="tdoc-tool-arrow fa-arrow-right" data-mode="line" data-arrow="y"\
 title="Arrow"></button>\
<button class="tdoc-tool-rect fa-square" data-mode="rectangle"\
 title="Rectangle"></button>\
<button class="tdoc-tool-ellipse fa-circle" data-mode="ellipse"\
 title="Ellipse"></button>\
<button class="tdoc-tool-eraser fa-eraser" data-mode="eraseLine"\
 title="Eraser"></button>\
<input class="tdoc-size" type="range" min="1" max="10" step="0.5"\
 value="${drawing.brush.size}" title="Size">\
</div>`);
    const toolBtns = qsa(toolbar, '[class^=tdoc-tool-]');
    for (const el of toolBtns) {
        console.log(el.dataset.mode, drawing.mode, !!el.dataset.arrow, !!drawing.brush.arrowEnd);
        el.classList.toggle('active',
                            el.dataset.mode === drawing.mode
                            && !!el.dataset.arrow === !!drawing.brush.arrowEnd);
        el.addEventListener('click', e => {
            drawing.mode = e.target.dataset.mode;
            drawing.brush.arrowEnd = !!e.target.dataset.arrow;
            for (const t of toolBtns) t.classList.remove('active');
            e.target.classList.add('active');
        });
    }
    qs(toolbar, '.tdoc-size').addEventListener('input', e => {
        drawing.brush.size = +e.target.value;
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
