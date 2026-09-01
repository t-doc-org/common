// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import * as api from './api.js';
import * as core from './core.js';
const {elmt, htmle, on, qs, qsa} = core;

// Handle build status and auto-reload on source change.
if (tdoc.local) {
    let build, statusBtn;
    function updateTooltip() {
        if (![bootstrap, statusBtn].every(v => v)) return;
        const bs = core.htmlData.tdocBuildStatus ?? '';
        bootstrap.Tooltip.getInstance(statusBtn)
            ?.setContent?.({'.tooltip-inner': `Build status: ${bs}`});
    }
    core.domLoaded.then(() => {
        statusBtn = qs(document, '.btn-build-status');
        on(statusBtn)['show.bs.tooltip'](updateTooltip);
    });

    let buildStatus, modal, pre;

    function renderWarnings(el) {
        // TODO: Colorize entries
        const entries = [];
        for (const w of buildStatus.warnings) {
            entries.push(elmt`<div>${w}</div>`);
        }
        el.replaceChildren(...entries);
    }

    function showWarnings() {
        const el = elmt`\
<div class="tdoc-build-errors modal fade" tabindex="-1" aria-hidden="true"\
 aria-labelledby="tdoc-modal-title">\
<div class="modal-dialog modal-xl modal-dialog-scrollable">\
<div class="modal-content">\
<div class="modal-header">\
<h1 class="modal-title fs-5" id="tdoc-modal-title">Build errors</h1>\
<button type="button" class="btn-close" data-bs-dismiss="modal"\
 aria-label="Close"></button>\
</div><div class="modal-body vstack gap-3">\
<div class="no-warnings">Please check the terminal output.</div>\
<pre class="warnings m-0 border-1 p-2"></pre>\
</div><div class="modal-footer flex-nowrap">\
<div class="flex-fill message"></div>\
<button type="button" class="btn btn-primary" data-bs-dismiss="modal">Close\
</button>\
</div></div></div>`;
        pre = qs(el, 'pre');
        renderWarnings(pre);
        modal = core.showModal(el);
        on(el)['hide.bs.modal'](() => { modal = pre = undefined; });
    }

    tdoc.buildStatus = () => {
        if (buildStatus.status === 'failure') showWarnings();
    };

    api.events.sub({add: [
        new api.Watch({name: 'build'}, data => {
            if (!data) return;
            if (!build) {
                build = data;
                console.info(`[t-doc] Build: ${build}`);
            } else if (data !== build) {
                location.reload();
            }
        }),
        new api.Watch({name: 'build-status'}, data => {
            buildStatus = data;
            core.htmlData.tdocBuildStatus = buildStatus.status ?? '';
            updateTooltip();
            if (buildStatus.status === 'failure') {
                if (modal) {
                    renderWarnings(pre);
                } else if (buildStatus.warnings.length > 0) {
                    showWarnings();
                }
            } else if (buildStatus.status === 'success') {
                if (modal) modal.hide();
            }
        }),
    ]});  // Background
}

// Show repository status.
if (tdoc.local) {
    core.domLoaded.then(() => {
        const search = qs(document,
                      '.sidebar-primary-item:has(> .search-button-field)');
        const body = qs(search.parentNode.insertBefore(elmt`\
<div class="sidebar-primary-item"><table class="tdoc-repo-status"><thead>\
<tr><th title="These repositories need action.">Repository status:</th>\
<th title="Remote changes">C</th><th title="Unknown files">U</th></tr></thead>\
<tbody></tbody></table></div>`, search), 'tbody');
        api.events.sub({add: [new api.Watch({name: 'repo_status'}, data => {
            const repos = Object.entries(data);
            repos.sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0);
            const rows = [];
            for (const [repo, {incoming, unknown}] of repos) {
                const it = incoming ? `\
${incoming} remote changes are available. Please pull, update and merge as soon\
 as possible.` : "";
                const ut = unknown ? `\
${unknown} unknown files found. Do you need to add them?` : "";
                rows.push(elmt`\
<tr><td>${repo}</td><td title="${it}">${incoming ?? ''}</td>\
<td title="${ut}">${unknown ?? ''}</td></tr>`);
            }
            body.replaceChildren(...rows);
        })]});  // Background
    });
}

// Prevent doctools.js from capturing editor key events, in case keyboard
// shortcuts are enabled.
core.domLoaded.then(() => {
    if (typeof BLACKLISTED_KEY_CONTROL_ELEMENTS !== 'undefined') {
        BLACKLISTED_KEY_CONTROL_ELEMENTS.add('DIV');
    }
});

// Handle admonition expansion. The button is needed to enable keyboard focus.
core.domLoaded.then(() => {
    for (const el of qsa(document, '.admonition.dropdown')) {
        const toggle = all => {
            const v = !el.classList.contains('expand');
            for (const dd of all ? qsa(document, '.admonition.dropdown')
                                 : [el]) {
                dd.classList.toggle('expand', v);
            }
        };
        const title = qs(el, '.admonition-title')
        on(title).click(e => {
            toggle(e.ctrlKey && !e.altKey && !e.metaKey && !e.shiftKey);
        });
        // Enable keyboard navigation.
        on(title.appendChild(elmt`<button></button>`)).click(e => {
            toggle(e.shiftKey && !e.altKey && !e.ctrlKey && !e.metaKey);
            e.stopPropagation();
        });
    }
});

// Handle the "toggle solutions" button.
let toggleSolutionsBtn;

function updateSolutionsTooltip() {
    if (![bootstrap, toggleSolutionsBtn].every(v => v)) return;
    const title = (core.htmlData.tdocSolutionsState ?? 'hide') === 'hide' ?
                  "Show solutions" : "Hide solutions";
    bootstrap.Tooltip.getInstance(toggleSolutionsBtn)
        ?.setContent?.({'.tooltip-inner': title});
}

tdoc.toggleSolutions = () => {
    const show = (core.htmlData.tdocSolutionsState ?? 'hide') === 'hide' ?
                 'show' : 'hide';
    if (core.htmlData.tdocSolutions === 'dynamic') {
        if (core.htmlData.tdocSolutionsCtrl !== undefined) api.solutions(show);
    } else {
        core.htmlData.tdocSolutionsState = show;
        updateSolutionsTooltip();
    }
};

core.domLoaded.then(() => {
    toggleSolutionsBtn = qs(document, '.btn-toggle-solutions');
    if (toggleSolutionsBtn) {
        on(toggleSolutionsBtn)['show.bs.tooltip'](updateSolutionsTooltip);
        if (core.htmlData.tdocSolutions === 'dynamic') {
            api.events.sub({add: [new api.Watch(
                {name: 'solutions', page: core.page.path},
                data => {
                    core.htmlData.tdocSolutionsState = data.show ?? 'hide';
                    updateSolutionsTooltip();
                })]});  // Background
            api.auth.onChange(() => {
                if (api.auth.hasPerm('solutions:write')) {
                    core.htmlData.tdocSolutionsCtrl = '';
                } else {
                    delete core.htmlData.tdocSolutionsCtrl;
                }
            });
        }
    }
});

// Handle the "draw" button.
let drawing, drawingSvg;
const drawState = new core.StoredJson('tdoc:drawState', {});
drawState.get().eraser = false;
tdoc.draw = async () => {
    if (core.htmlData.tdocDraw !== undefined) {
        drawing.unmount();
        delete core.htmlData.tdocDraw;
        return;
    }
    core.htmlData.tdocDraw = '';
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
    await core.domLoaded;
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
        core.addTooltip(el, {placement: el.classList.contains('dropdown-item') ?
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
        const color = core.rgb2hex(el.style.color);
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
        mermaid.initialize({...tdoc.dyn.mermaid, startOnLoad: false});
        const mu = new core.Mutex();  // Mermaid rendering is non-reentrant
        core.dyn.render.mermaid = async el => {
            try {
                await mu.locked(() => mermaid.run({nodes: [el]}));
            } catch (e) {
                el.replaceChildren(
                    core.HtmlError.of('str' in e ? e.str : e).html);
                throw htmle`\
<code>{mermaid}</code>: A diagram failed to render.`;
            }
        };
    })();
}

// Handle graphviz diagrams.
core.domLoaded.then(() => {
    // Replace <object> elements with their SVG content, so that they can be
    // styled.
    for (const el of qsa(document, 'object.graphviz')) {
        const embed = () => {
            el.parentNode.classList.add(...el.classList);
            el.replaceWith(el.getSVGDocument().documentElement);
        };
        if (el.getSVGDocument()) {
            embed();
        } else {
            on(el).load(embed);
        }
    }
});
