// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {elmt, on, qs} from './core.js';
import {Executor} from './exec.js';

class HtmlExecutor extends Executor {
    static runner = 'html';
    static highlight = 'html';

    static async init() {}

    addControls(controls) {
        if (this.when === 'click' || (this.editable && this.when !== 'never')) {
            this.runCtrl = controls.appendChild(this.runControl());
        }
        super.addControls(controls);
    }

    async run(run_id) {
        const output = elmt`\
<div class="tdoc-exec-output tdoc-sectioned">\
<div class="tdoc-navbar">\
<button class="fa-arrow-left tdoc-back" title="Back"></button>\
<button class="fa-arrow-right tdoc-forward" title="Forward"></button>\
<button class="fa-rotate-right tdoc-reload" title="Reload"></button>\
<div class="tdoc-stretch"></div>\
<button class="fa-expand tdoc-maximize" title="Maximize"></button>\
<button class="fa-compress tdoc-restore" title="Restore"></button>\
<button class="fa-xmark tdoc-close" title="Remove"></button>\
</div>\
<iframe credentialless\
 allow="accelerometer; ambient-light-sensor; autoplay; bluetooth; camera;\
 clipboard-write; encrypted-media; fullscreen; gamepad; geolocation; gyroscope;\
 hid; idle-detection; local-fonts; magnetometer; microphone; midi;\
 picture-in-picture; screen-wake-lock;\
 serial; usb; web-share"\
 referrerpolicy="no-referrer">\
</iframe>\
</div>`;
        const iframe = qs(output, 'iframe');
        this.setOutputStyle(iframe);
        const blocks = [];
        for (const {code} of this.codeBlocks()) blocks.push(code);
        iframe.srcdoc = blocks.join('');
        on(qs(output, '.tdoc-back')).click(() => { history.back(); });
        on(qs(output, '.tdoc-forward')).click(() => { history.forward(); });
        on(qs(output, '.tdoc-reload')).click(() => {
            try {  // Try to reload if non-cross-origin
                iframe.contentWindow.history.go();
            } catch (e) {}
        });
        on(qs(output, '.tdoc-maximize')).click(() => {
            document.documentElement.classList.add('tdoc-fullscreen');
            output.classList.add('tdoc-fullscreen');
        });
        on(qs(output, '.tdoc-restore')).click(() => {
            document.documentElement.classList.remove('tdoc-fullscreen');
            output.classList.remove('tdoc-fullscreen');
        });
        on(qs(output, '.tdoc-close')).click(() => { output.remove(); });
        this.replaceOutputs(output);
    }

    async stop(run_id) {}
}

Executor.apply(HtmlExecutor);
