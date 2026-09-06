// Copyright 2026 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import * as api from './api.js';
import * as core from './core.js';
const {elmt, html, on, qs} = core;

if (!tdoc.local) {
    console.warn("[t-doc] Imported local.js but not serving locally");
}

// Handle build status and auto-reload on source change.
let build, statusBtn;

function updateBuildStatusTooltip() {
    if (![bootstrap, statusBtn].every(v => v)) return;
    const bs = core.htmlData.tdocBuildStatus ?? '';
    bootstrap.Tooltip.getInstance(statusBtn)
        ?.setContent?.({'.tooltip-inner': `Build status: ${bs}`});
}

core.domLoaded.then(() => {
    statusBtn = qs(document, '.btn-build-status');
    on(statusBtn)['show.bs.tooltip'](updateBuildStatusTooltip);
});

let buildStatus = {}, modal, modalEl;

function showBuildStatusModal() {
    const el = elmt`\
<div class="tdoc-build-status modal fade" tabindex="-1"
 aria-hidden="true" aria-labelledby="tdoc-modal-title">\
<div class="modal-dialog modal-xl modal-dialog-scrollable">\
<div class="modal-content">\
<div class="modal-header">\
<h1 class="modal-title fs-5" id="tdoc-modal-title">Build messages</h1>\
<button type="button" class="btn-close" data-bs-dismiss="modal"\
 aria-label="Close"></button>\
</div><div class="modal-body vstack gap-2">\
</div><div class="modal-footer flex-nowrap">\
<div class="flex-fill message"></div>\
<button type="button" class="btn btn-primary" data-bs-dismiss="modal">Close\
</button>\
</div></div></div>`;
    renderBuildMessages(el)
    modal = core.showModal(el);
    modalEl = el;
    on(el)['hide.bs.modal'](() => { modal = modalEl = undefined; });
}

function renderBuildMessages(el) {
    const els = html``;
    for (const msg of buildStatus.messages) {
        const div = els.appendChild(elmt`<div class="${msg.level}"></div>`);
        div.appendChild(core.htmlFragment(msg.html))
    }
    qs(el, '.modal-body').replaceChildren(els);
}

tdoc.buildStatus = () => {
    if ((buildStatus.messages ?? []).length > 0) showBuildStatusModal();
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
        const {status, messages} = buildStatus = data;
        core.htmlData.tdocBuildStatus = status ?? '';
        updateBuildStatusTooltip();
        if (messages === undefined) return;
        if (messages.length === 0) {
            if (modal) modal.hide();
        } else if (modal) {
            renderBuildMessages(modalEl);
        } else if (status === 'error') {
            showBuildStatusModal();
        }
    }),
]});  // Background

// Show repository status.
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
