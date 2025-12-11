// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {elmt, escape, on, onMessage, qs} from './core.js';
import {Executor} from './exec.js';

const parser = new DOMParser();

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
        const title = qs(navbar, '.tdoc-title');
        this.output.render('000', navbar);

        // Create the iframe. Ideally, it would be cross-origin and use
        // allow-same-origin, but it's surprisingly difficult to do so:
        //
        //  - data: URLs make the iframe cross-origin, but they disable some
        //    functionality (e.g. storage APIs) and may have size limitations.
        //  - It doesn't seem to be possible to create cross-origin blob URLs.
        //  - The only possibility seems to be to serve the HTML code from a
        //    sandbox origin, e.g. via the API. This would require storing it
        //    at least temporarily, and wouldn't work with the local server,
        //    since the API is same-origin in this case.
        //  - Maybe some day we'll have allow-unique-origin for this very use
        //    case <https://github.com/whatwg/html/issues/9623>.
        //
        // So for now we err on the safe side and don't allow-same-origin.
        //
        // Some links on the topic:
        //  - https://security.googleblog.com/2023/04/securely-hosting-user-data-in-modern.html
        const iframe = elmt`\
<iframe\
 allow="accelerometer; ambient-light-sensor; autoplay; bluetooth; camera;\
 encrypted-media; fullscreen; gamepad; geolocation; gyroscope; hid;\
 idle-detection; local-fonts; magnetometer; microphone; midi;\
 picture-in-picture; screen-wake-lock; serial; usb; xr-spatial-tracking"\
 sandbox="allow-downloads allow-forms allow-modals allow-pointer-lock\
 allow-popups allow-popups-to-escape-sandbox allow-presentation\
 allow-scripts"\
 referrerpolicy="no-referrer">\
</iframe>`;
        this.setOutputStyle(iframe);
        this.output.render('001', iframe);
        onMessage(iframe.contentWindow, e => {
            const data = e.data;
            if (data.unload !== undefined) {
                title.textContent = '';
                this.out.clear();
            }
            if (data.title !== undefined) title.textContent = data.title;
            if (data.consoleClear !== undefined) this.out.clear();
            const log = data.consoleLog;
            if (log !== undefined) {
                const eol = log.msg.endsWith('\n') ? '' : '\n';
                this.out.write(log.stream ?? '', `${log.msg}${eol}`);
            }
        });

        // Inject the cross-origin communication code at the beginning of the
        // HTML code. It would be more correct to parse the HTML to a document,
        // then add the <script> tag at the beginning of the <head>, and
        // re-serialize the document, but this wouldn't preserve line numbers.
        // In practice, browsers are smart enough to move the <script> tag to
        // the beginning of the <head> anyway, so this works.
        const inject = import.meta.resolve('./exec-html-iframe.js');
        const blocks = [`<script src="${escape(inject)}"></script>`];
        for (const {code} of this.codeBlocks()) blocks.push(code);
        iframe.srcdoc = blocks.join('');
    }

    async stop(run_id) {}
}

Executor.apply(HtmlExecutor);  // Background
