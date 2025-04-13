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
let drawing, drawingSvg;
const drawState = {
    tool: 'stylus', eraser: false,
    size: 3, color: '#ff0000', marker: false,
};
globalThis.tdocDraw = () => {
    const ds = document.documentElement.dataset;
    if (ds.tdocDraw !== undefined) {
        drawing.unmount();
        delete ds.tdocDraw;
        return;
    }
    ds.tdocDraw = '';
    if (drawing) {
        drawing.mount(drawingSvg);
        return;
    }

    function setState(opts) {
        Object.assign(drawState, opts);
        const mode = drawState.eraser ? 'eraseLine' :
                     drawState.tool === 'arrow' ? 'line' : drawState.tool;
        if (drawing.mode !== mode) drawing.mode = mode;
        drawing.brush.arrowEnd = drawState.tool === 'arrow';
        drawing.brush.size = drawState.size * (drawState.marker ? 8 : 1);
        drawing.brush.color = drawState.color
                              + (drawState.marker ? '40' : 'ff');
    }

    drawingSvg = qs(document, '.bd-content').appendChild(elmt`\
<svg id="tdoc-drawing" xmlns="http://www.w3.org/2000/svg"\
 xmlns:xlink="http://www.w3.org/1999/xlink"></svg>`);
    drawing = createDrauu({el: drawingSvg});
    setState({});
    // TODO: Don't capture 'keydown' events on window
    // TODO: Use bootstrap tooltips instead of title=
    const toolbar = qs(document, '.header-article-items__start')
        .appendChild(elmt`\
<div class="header-article-item tdoc-draw-toolbar">\
<div class="tdoc-tool dropdown-center">\
<button class="btn" title="Tool" data-bs-toggle="dropdown"></button>\
<ul class="dropdown-menu">\
<li><a class="dropdown-item fa-paintbrush" data-tool="stylus"\
 title="Brush"></a></li>\
<li><a class="dropdown-item fa-pencil" data-tool="draw"\
 title="Pencil"></a></li>\
<li><a class="dropdown-item fa-pen-ruler" data-tool="line"\
 title="Line"></a></li>\
<li><a class="dropdown-item fa-arrow-right" data-tool="arrow"\
 title="Arrow"></a></li>\
<li><a class="dropdown-item fa-square" data-tool="rectangle"\
 title="Rectangle"></a></li>\
<li><a class="dropdown-item fa-circle" data-tool="ellipse"\
 title="Ellipse"></a></li>\
</ul>\
</div>\
<input type="checkbox" name="eraser" class="btn fa-eraser"\
 data-mode="eraseLine" title="Eraser">\
<button name="clear" class="btn fa-trash" title="Clear"></button>\
<input class="tdoc-size" type="range" min="1" max="8" step="1"\
 value="${drawState.size}" title="Stroke width">\
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
    const toolButton = qs(toolbar, '.tdoc-tool button');
    for (const el of qsa(toolbar, '.tdoc-tool .dropdown-item')) {
        const tool = el.dataset.tool, icon = el.classList[1];
        if (drawState.tool === tool) toolButton.classList.add(icon);
        el.addEventListener('click', () => {
            toolButton.classList.remove(toolButton.classList[1]);
            toolButton.classList.add(icon);
            setState({tool});
        });
    }
    qs(toolbar, '[name=eraser]').addEventListener('click', e => {
        setState({eraser: e.target.checked});
    });
    qs(toolbar, '[name=clear]').addEventListener('click', () => {
        drawing.clear();
    });
    qs(toolbar, '.tdoc-size').addEventListener('input', e => {
        setState({size: +e.target.value});
    });
    const colorButton = qs(toolbar, '.tdoc-color button');
    for (const el of qsa(toolbar, '.tdoc-color .dropdown-item')) {
        const color = rgb2hex(el.style.color);
        if (drawState.color === color) colorButton.style.color = color;
        el.addEventListener('click', () => {
            colorButton.style.color = color;
            setState({color});
        });
    }
    qs(toolbar, '[name=marker]').addEventListener('click', e => {
        setState({marker: e.target.checked});
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
