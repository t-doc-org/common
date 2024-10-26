// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {Executor, element} from './tdoc-exec.js';

class HtmlExecutor extends Executor {
    static lang = 'html';

    static async init() {}

    addControls(controls) {
        if (this.when === 'click' || (this.editable && this.when !== 'never')) {
            this.runCtrl = controls.appendChild(this.runControl());
        }
        super.addControls(controls);
    }

    async run(run_id) {
        const blocks = [];
        for (const [code, node] of this.codeBlocks()) blocks.push(code);
        const output = element(`\
<div class="tdoc-exec-output tdoc-sectioned">\
<div class="tdoc-navbar">\
<button class="fa-arrow-left tdoc-back" title="Back">\
<button class="fa-arrow-right tdoc-forward" title="Forward">\
<button class="fa-rotate-right tdoc-reload" title="Reload">\
</div>\
<iframe></iframe></div>`);
        this.iframe = output.querySelector('iframe');
        this.iframe.srcdoc = blocks.join('');
        output.querySelector('.tdoc-back')
            .addEventListener('click', () => {
                this.iframe.contentWindow.history.back();
            });
        output.querySelector('.tdoc-forward')
            .addEventListener('click', () => {
                this.iframe.contentWindow.history.forward();
            });
        output.querySelector('.tdoc-reload')
            .addEventListener('click', () => {
                this.iframe.contentWindow.history.go();
            });
        this.replaceOutputs([output]);
    }

    async stop(run_id) {}
}

Executor.apply(HtmlExecutor);
