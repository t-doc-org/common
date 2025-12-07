// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {elmt, on, qs} from './core.js';
import {Executor} from './exec.js';

const parser = new DOMParser();

// Dispatch messages from iframes.
const sources = new Map();
on(window).message(e => {
    const exec = sources.get(e.source);
    if (!exec) return;
    exec.onMessage(e);
});

class HtmlExecutor extends Executor {
    static runner = 'html';
    static highlight = 'html';

    constructor(node) {
        super(node);
        this.output = this.sectionedOutput();
        this.out = this.output.consoleOut('990');
    }

    addControls(controls) {
        if (this.when === 'click' || (this.editable && this.when !== 'never')) {
            this.runCtrl = controls.appendChild(this.runControl());
        }
        super.addControls(controls);
    }

    async run(run_id) {
        this.out.clear();
        const navbar = elmt`\
<div class="tdoc-navbar">\
<button class="fa-arrow-left tdoc-back" title="Back"></button>\
<button class="fa-arrow-right tdoc-forward" title="Forward"></button>\
<div class="tdoc-title"></div>\
<button class="fa-expand tdoc-maximize" title="Maximize"></button>\
<button class="fa-compress tdoc-restore" title="Restore"></button>\
<button class="fa-xmark tdoc-close" title="Remove"></button>\
</div>`;
        on(qs(navbar, '.tdoc-back')).click(() => { history.back(); });
        on(qs(navbar, '.tdoc-forward')).click(() => { history.forward(); });
        on(qs(navbar, '.tdoc-maximize')).click(() => {
            document.documentElement.classList.add('tdoc-fullscreen');
            this.output.output.classList.add('tdoc-fullscreen');
        });
        on(qs(navbar, '.tdoc-restore')).click(() => {
            document.documentElement.classList.remove('tdoc-fullscreen');
            this.output.output.classList.remove('tdoc-fullscreen');
        });
        on(qs(navbar, '.tdoc-close')).click(() => { this.output.remove(); });
        this.title = qs(navbar, '.tdoc-title');
        this.output.render('000', navbar);

        // Create the iframe.
        if (this.iframe) sources.delete(this.iframe.contentWindow);
        delete this.iframe;
        const iframe = elmt`\
<iframe credentialless\
 allow="accelerometer; ambient-light-sensor; autoplay; bluetooth; camera;\
 clipboard-write; encrypted-media; fullscreen; gamepad; geolocation; gyroscope;\
 hid; idle-detection; local-fonts; magnetometer; microphone; midi;\
 picture-in-picture; screen-wake-lock; serial; usb; web-share"\
 sandbox="allow-downloads allow-forms allow-modals allow-popups\
 allow-popups-to-escape-sandbox allow-presentation allow-scripts"\
 referrerpolicy="no-referrer">\
</iframe>`;
        this.setOutputStyle(iframe);
        this.output.render('001', iframe);
        this.iframe = iframe;
        sources.set(iframe.contentWindow, this);

        // Parse the HTML code, and inject the cross-origin communication code.
        const blocks = [];
        for (const {code} of this.codeBlocks()) blocks.push(code);
        const doc = parser.parseFromString(blocks.join(''), 'text/html');
        const inject = import.meta.resolve('./exec-html-iframe.js');
        doc.head.insertBefore(elmt`<script src="${inject}"></script>`,
                              doc.head.firstElementChild);
        iframe.srcdoc = doc.documentElement.outerHTML;
    }

    async stop(run_id) {}

    onMessage(e) {
        const data = e.data;
        if (data.unload !== undefined) {
            this.title.textContent = '';
            this.out.clear();
        }
        if (data.title !== undefined) this.title.textContent = data.title;
        if (data.consoleClear !== undefined) this.out.clear();
        const log = data.consoleLog;
        if (log !== undefined) {
            const eol = log.msg.endsWith('\n') ? '' : '\n';
            this.out.write(log.stream ?? '', `${log.msg}${eol}`);
        }
    }
}

Executor.apply(HtmlExecutor);  // Background
