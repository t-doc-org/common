// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import * as api from './api.js';
import {
    addTooltip, domLoaded, elmt, htmlData, on, page, qs, qsa, rgb2hex, Stored,
    StoredJson,
} from './core.js';
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

// Handle the "terminate server" button.
tdoc.terminateServer = async () => await api.terminate();

// Handle the "toggle solutions" button.
const toggleSolutionsBtn = qs(document, '.btn-toggle-solutions');
function updateSolutionsTooltip() {
    const title = (htmlData.tdocSolutionsState ?? 'hide') === 'hide' ?
                  "Show solutions" : "Hide solutions";
    bootstrap.Tooltip.getInstance(toggleSolutionsBtn)
        .setContent({'.tooltip-inner': title});
}
if (toggleSolutionsBtn) {
    on(toggleSolutionsBtn)['show.bs.tooltip'](updateSolutionsTooltip);
    if (htmlData.tdocSolutions === 'dynamic') {
        api.events.sub({add: [new api.Watch(
            {name: 'solutions', page: page.path},
            data => {
                htmlData.tdocSolutionsState = data.show ?? 'hide';
                updateSolutionsTooltip();
            })]});
        api.user.onChange(async () => {
            if (await api.user.member_of('solutions:write')) {
                htmlData.tdocSolutionsCtrl = '';
            } else {
                delete htmlData.tdocSolutionsCtrl;
            }
        });
    }
}

tdoc.toggleSolutions = () => {
    const show = (htmlData.tdocSolutionsState ?? 'hide') === 'hide' ? 'show'
                 : 'hide'
    if (htmlData.tdocSolutions === 'dynamic') {
        if (htmlData.tdocSolutionsCtrl !== undefined) api.solutions(show);
    } else {
        htmlData.tdocSolutionsState = show;
        updateSolutionsTooltip();
    }
};

// Handle the "draw" button.
let drawing, drawingSvg;
const drawState = new StoredJson('tdoc:drawState', {});
drawState.value.eraser = false;
tdoc.draw = () => {
    if (htmlData.tdocDraw !== undefined) {
        drawing.unmount();
        delete htmlData.tdocDraw;
        return;
    }
    htmlData.tdocDraw = '';
    if (drawing) {
        drawing.mount(drawingSvg);
        return;
    }

    function setState(opts) {
        const st = drawState.update(v => Object.assign(v, opts));
        const mode = st.eraser ? 'eraseLine' :
                     st.tool === 'arrow' ? 'line' : st.tool;
        if (drawing.mode !== mode) drawing.mode = mode;
        drawing.brush.arrowEnd = st.tool === 'arrow';
        drawing.brush.size = st.size * (st.marker ? 8 : 1);
        drawing.brush.color = st.color + (st.marker ? '40' : 'ff');
    }

    drawingSvg = qs(document, '.bd-content').appendChild(elmt`\
<svg id="tdoc-drawing" xmlns="http://www.w3.org/2000/svg"\
 xmlns:xlink="http://www.w3.org/1999/xlink"></svg>`);
    drawing = createDrauu({el: drawingSvg});
    setState({});
    const toolbar = qs(document, '.header-article-items__start')
        .appendChild(elmt`\
<div class="header-article-item tdoc-draw-toolbar">\
<div class="tdoc-tool dropdown-center">\
<button class="btn" data-bs-toggle="dropdown"></button>\
<ul class="dropdown-menu">\
<li><a class="dropdown-item fa-paintbrush" data-tool="stylus"\
 data-bs-toggle="tooltip" data-bs-title="Brush"></a></li>\
<li><a class="dropdown-item fa-pencil" data-tool="draw"\
 data-bs-toggle="tooltip" data-bs-title="Pencil"></a></li>\
<li><a class="dropdown-item fa-pen-ruler" data-tool="line"\
 data-bs-toggle="tooltip" data-bs-title="Line"></a></li>\
<li><a class="dropdown-item fa-arrow-right" data-tool="arrow"\
 data-bs-toggle="tooltip" data-bs-title="Arrow"></a></li>\
<li><a class="dropdown-item fa-square" data-tool="rectangle"\
 data-bs-toggle="tooltip" data-bs-title="Rectangle"></a></li>\
<li><a class="dropdown-item fa-circle" data-tool="ellipse"\
 data-bs-toggle="tooltip" data-bs-title="Ellipse"></a></li>\
</ul>\
</div>\
<input type="checkbox" name="eraser" class="btn fa-eraser"\
 data-bs-toggle="tooltip" data-bs-title="Eraser"\
${drawState.value.eraser ? ' checked="checked"' : ''}>\
<button name="clear" class="btn fa-trash" data-bs-toggle="tooltip"\
 data-bs-title="Clear"></button>\
<input type="range" class="tdoc-size" min="1" max="8" step="1"\
 data-bs-toggle="tooltip" data-bs-title="Stroke width">\
<div class="tdoc-color dropdown-center">\
<button class="btn fa-square" data-bs-toggle="dropdown"></button>\
<ul class="dropdown-menu">\
<li><a class="dropdown-item fa-square" style="color: #ff0000;"></a></li>\
<li><a class="dropdown-item fa-square" style="color: #008000;"></a></li>\
<li><a class="dropdown-item fa-square" style="color: #0000ff;"></a></li>\
<li><a class="dropdown-item fa-square" style="color: #00e0e0;"></a></li>\
<li><a class="dropdown-item fa-square" style="color: #ff00ff;"></a></li>\
<li><a class="dropdown-item fa-square" style="color: #f0f000;"></a></li>\
</ul>\
</div>\
<input type="checkbox" name="marker" class="btn fa-marker"\
 data-bs-toggle="tooltip" data-bs-title="Marker"\
${drawState.value.marker ? ' checked="checked"' : ''}>\
</div>`);

    for (const el of qsa(toolbar, '[data-bs-toggle=tooltip]')) {
        addTooltip(el, {placement: el.classList.contains('dropdown-item') ?
                                   'right' : 'bottom'});
    }

    const toolBtn = qs(toolbar, '.tdoc-tool button');
    for (const el of qsa(toolbar, '.tdoc-tool .dropdown-item')) {
        const tool = el.dataset.tool, icon = el.classList[1];
        if (drawState.value.tool === tool) toolBtn.classList.add(icon);
        el.addEventListener('click', () => {
            toolBtn.classList.remove(toolBtn.classList[1]);
            toolBtn.classList.add(icon);
            setState({tool});
        });
    }
    if (toolBtn.classList[1] === undefined) {
        setState({tool: 'stylus'});
        toolBtn.classList.add('fa-paintbrush');
    }

    qs(toolbar, '[name=eraser]').addEventListener('click', e => {
        setState({eraser: e.target.checked});
    });
    qs(toolbar, '[name=clear]').addEventListener('click', () => {
        drawing.clear();
    });

    const sizeSlider = qs(toolbar, '.tdoc-size');
    if (!(drawState.value.size && +sizeSlider.min <= drawState.value.size
            && drawState.value.size <= +sizeSlider.max)) {
        setState({size: 3});
    }
    sizeSlider.value = drawState.value.size;
    sizeSlider.addEventListener('input', e => {
        setState({size: +e.target.value});
    });

    const colorBtn = qs(toolbar, '.tdoc-color button');
    for (const el of qsa(toolbar, '.tdoc-color .dropdown-item')) {
        const color = rgb2hex(el.style.color);
        if (drawState.value.color === color) colorBtn.style.color = color;
        el.addEventListener('click', () => {
            colorBtn.style.color = color;
            setState({color});
        });
    }
    if (!colorBtn.style.color) {
        setState({color: '#ff0000'});
        colorBtn.style.color = drawState.value.color;
    }

    qs(toolbar, '[name=marker]').addEventListener('click', e => {
        setState({marker: e.target.checked});
    });
};

if (tdoc.dev) {
    let build;
    api.events.sub({add: [new api.Watch({name: 'build'}, async data => {
        if (!data) return;
        if (!build) {
            build = data;
            console.info(`[t-doc] Build: ${build}`);
        } else if (data !== build) {
            location.reload();
        }
    })]});
}
