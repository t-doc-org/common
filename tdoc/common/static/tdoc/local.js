// Copyright 2026 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import * as api from './api.js';
import * as core from './core.js';
const {elmt, on, qs} = core;

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

let buildStatus, modal, pre;
const logPrefix = /^(?:(.+?)(?::(\d+))?: )?(WARNING|ERROR|CRITICAL): /;

function renderBuildErrors(el) {
    const entries = [];
    for (let w of buildStatus.errors) {
        const div = elmt`<div></div>`;
        let m = w.match(logPrefix);
        if (m) {
            const [m0, m1, m2, m3] = m;
            if (m1) {
                div.appendChild(elmt`<span class="loc-p">${m1}</span>`);
                div.appendChild(core.text(":"));
                if (m2) {
                    div.appendChild(elmt`<span class="loc-l">${m2}</span>`);
                    div.appendChild(core.text(":"));
                }
                div.appendChild(core.text(" "));
            }
            if (m3) {
                div.appendChild(elmt`<span class="lvl-${m3[0]}">${m3}</span>`);
                div.appendChild(core.text(": "));
            }
            w = w.substring(m0.length);
        }
        if (w !== "") div.appendChild(core.text(w));
        entries.push(div);
    }
    el.replaceChildren(...entries);
}

function showBuildErrors() {
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
<div class="no-errors">Please check the terminal output.</div>\
<pre class="errors m-0 border-1 p-2"></pre>\
</div><div class="modal-footer flex-nowrap">\
<div class="flex-fill message"></div>\
<button type="button" class="btn btn-primary" data-bs-dismiss="modal">Close\
</button>\
</div></div></div>`;
    pre = qs(el, 'pre');
    renderBuildErrors(pre);
    modal = core.showModal(el);
    on(el)['hide.bs.modal'](() => { modal = pre = undefined; });
}

tdoc.buildStatus = () => {
    if (buildStatus.status === 'failure') showBuildErrors();
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
        updateBuildStatusTooltip();
        if (buildStatus.status === 'failure') {
            if (modal) {
                renderBuildErrors(pre);
            } else {
                showBuildErrors();
            }
        } else if (buildStatus.status === 'success') {
            if (modal) modal.hide();
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
