// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import * as api from './api.js';
import {
    addTooltip, domLoaded, elmt, enable, findDyn, htmlData, on, page, qs, qsa,
    rgb2hex, StoredJson,
} from './core.js';

// Handle auto-reload on source change.
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

// Prevent doctools.js from capturing editor key events, in case keyboard
// shortcuts are enabled.
domLoaded.then(() => {
    if (typeof BLACKLISTED_KEY_CONTROL_ELEMENTS !== 'undefined') {
        BLACKLISTED_KEY_CONTROL_ELEMENTS.add('DIV');
    }
});

// Handle login / logout.
domLoaded.then(() => {
    const dd = qs(document, '.dropdown-user');
    const menu = qs(dd, '.dropdown-menu');
    const user = qs(menu, 'li > a.btn-user');
    user.classList.add('disabled');
    const login = qs(menu, 'li:has(.btn-login)');
    const logout = qs(menu, 'li:has(.btn-logout)');
    api.user.onChange(async () => {
        const name = await api.user.name();
        dd.classList.toggle('signed-in', name !== undefined);
        login.classList.toggle('hidden', name !== undefined);
        logout.classList.toggle('hidden', name === undefined);
        qs(user, '.btn__text-container')
            .replaceChildren(name !== undefined ? name : "Not signed in");
    });
});
let loginModal;
tdoc.login = async() => {
    if (!loginModal) {
        const el = document.body.appendChild(elmt`
<div class="modal fade" id="tdoc-login" tabindex="-1" aria-hidden="true"\
 aria-labelledby="tdoc-login-title">\
<div class="modal-dialog"><div class="modal-content">\
<div class="modal-header">\
<h1 class="modal-title fs-5" id="tdoc-login-title">Sign in</h1>\
<button type="button" class="btn-close" data-bs-dismiss="modal"\
 aria-label="Close"></button>\
</div><div class="modal-body">\
<form><div class="mb-3">\
<label for="tdoc-login-token" class="col-form-label">Token:</label>\
<input type="password" class="form-control" id="tdoc-login-token"\
 autocomplete="current-password">\
</div></form>\
</div><div class="modal-footer">\
<div class="message hidden">Sign in failed.</div>\
<button type="button" class="btn btn-primary" disabled>Sign in</button>\
</div></div></div>\
`);
        const form = qs(el, 'form');
        const input = qs(form, 'input#tdoc-login-token');
        const msg = qs(el, '.message');
        const btn = qs(el, '.btn-primary');
        loginModal = bootstrap.Modal.getOrCreateInstance(el);
        on(el)['shown.bs.modal'](() => input.focus());
        on(el)['hide.bs.modal'](() => document.activeElement.blur());
        on(el)['hidden.bs.modal'](() => {
            input.value = '';
            msg.classList.add('hidden');
            btn.disabled = true;
        });
        on(input).input(() => enable(input.value, btn));
        on(btn).click(() => form.requestSubmit());
        on(form).submit(async e => {
            e.preventDefault();
            if (await api.user.login(input.value)) {
                loginModal.hide();
            } else {
                msg.classList.remove('hidden');
                input.focus();
            }
        });
    }
    loginModal.show();
};
tdoc.logout = async () => await api.user.logout();

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
const drawState = StoredJson.create('tdoc:drawState', {});
drawState.get().eraser = false;
tdoc.draw = async () => {
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

    const {createDrauu} = await import(`${tdoc.versions.drauu}/index.mjs`);
    drawingSvg = qs(document, '.bd-content').appendChild(elmt`\
<svg id="tdoc-drawing" xmlns="http://www.w3.org/2000/svg"\
 xmlns:xlink="http://www.w3.org/1999/xlink"></svg>`);
    drawing = createDrauu({el: drawingSvg});
    setState({});
    const ds = drawState.get();
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
${ds.eraser ? ' checked="checked"' : ''}>\
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
${ds.marker ? ' checked="checked"' : ''}>\
</div>`);

    for (const el of qsa(toolbar, '[data-bs-toggle=tooltip]')) {
        addTooltip(el, {placement: el.classList.contains('dropdown-item') ?
                                   'right' : 'bottom'});
    }

    const toolBtn = qs(toolbar, '.tdoc-tool button');
    for (const el of qsa(toolbar, '.tdoc-tool .dropdown-item')) {
        const tool = el.dataset.tool, icon = el.classList[1];
        if (ds.tool === tool) toolBtn.classList.add(icon);
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
    if (!(ds.size && +sizeSlider.min <= ds.size
            && ds.size <= +sizeSlider.max)) {
        setState({size: 3});
    }
    sizeSlider.value = ds.size;
    sizeSlider.addEventListener('input', e => {
        setState({size: +e.target.value});
    });

    const colorBtn = qs(toolbar, '.tdoc-color button');
    for (const el of qsa(toolbar, '.tdoc-color .dropdown-item')) {
        const color = rgb2hex(el.style.color);
        if (ds.color === color) colorBtn.style.color = color;
        el.addEventListener('click', () => {
            colorBtn.style.color = color;
            setState({color});
        });
    }
    if (!colorBtn.style.color) {
        setState({color: '#ff0000'});
        colorBtn.style.color = ds.color;
    }

    qs(toolbar, '[name=marker]').addEventListener('click', e => {
        setState({marker: e.target.checked});
    });
};

// Handle Mermaid diagrams.
if (tdoc.dyn?.mermaid) {
    (async () => {
        const [{default: mermaid}, {default: elk}] = await Promise.all([
            import(`${tdoc.versions.mermaid}/mermaid.esm.min.mjs`),
            import(`\
${tdoc.versions['mermaid-layout-elk']}/mermaid-layout-elk.esm.min.mjs`),
        ]);
        mermaid.registerLayoutLoaders(elk);
        await domLoaded;

        const config = tdoc.dyn.mermaid;
        const lightTheme = config.theme ?? 'default';
        const darkTheme = config.darkTheme ?? 'dark';

        const nodes = findDyn('mermaid');
        for (const n of nodes) n.tdocCode = n.innerHTML;

        async function render() {
            mermaid.initialize({
                ...config,
                startOnLoad: false,
                theme: document.documentElement.dataset.theme === 'dark' ?
                       darkTheme : lightTheme,
            });
            for (const node of nodes) {
                node.innerHTML = node.tdocCode;
                delete node.dataset.processed;
            }
            await mermaid.run({nodes});
        }

        await render();
        document.addEventListener('theme-change', render);
    })();
}
