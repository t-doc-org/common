// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {elmt, on, qs} from './core.js';
import {Executor} from './exec.js';

class HtmlExecutor extends Executor {
    static runner = 'html';
    static highlight = 'html';

    constructor(node) {
        super(node);
        this.output = this.sectionedOutput();
        // TODO: Hook the console proxy up to the iframe
        // this.console = new Console(this.output.consoleOut('990'));
    }

    addControls(controls) {
        if (this.when === 'click' || (this.editable && this.when !== 'never')) {
            this.runCtrl = controls.appendChild(this.runControl());
        }
        super.addControls(controls);
    }

    async run(run_id) {
        const navbar = elmt`\
<div class="tdoc-navbar">\
<button class="fa-arrow-left tdoc-back" title="Back"></button>\
<button class="fa-arrow-right tdoc-forward" title="Forward"></button>\
<button class="fa-rotate-right tdoc-reload" title="Reload"></button>\
<div class="tdoc-stretch"></div>\
<button class="fa-expand tdoc-maximize" title="Maximize"></button>\
<button class="fa-compress tdoc-restore" title="Restore"></button>\
<button class="fa-xmark tdoc-close" title="Remove"></button>\
</div>`;
        on(qs(navbar, '.tdoc-back')).click(() => { history.back(); });
        on(qs(navbar, '.tdoc-forward')).click(() => { history.forward(); });
        on(qs(navbar, '.tdoc-reload')).click(() => {
            try {  // Try to reload if non-cross-origin
                iframe.contentWindow.history.go();
            } catch (e) {}
        });
        on(qs(navbar, '.tdoc-maximize')).click(() => {
            document.documentElement.classList.add('tdoc-fullscreen');
            this.output.output.classList.add('tdoc-fullscreen');
        });
        on(qs(navbar, '.tdoc-restore')).click(() => {
            document.documentElement.classList.remove('tdoc-fullscreen');
            this.output.output.classList.remove('tdoc-fullscreen');
        });
        on(qs(navbar, '.tdoc-close')).click(() => { this.output.remove(); });
        this.output.render('000', navbar);

        const iframe = elmt`\
<iframe credentialless\
 allow="accelerometer; ambient-light-sensor; autoplay; bluetooth; camera;\
 clipboard-write; encrypted-media; fullscreen; gamepad; geolocation; gyroscope;\
 hid; idle-detection; local-fonts; magnetometer; microphone; midi;\
 picture-in-picture; screen-wake-lock; serial; usb; web-share"\
 referrerpolicy="no-referrer">\
</iframe>`;
        this.setOutputStyle(iframe);
        this.output.render('001', iframe)

        const blocks = [];
        for (const {code} of this.codeBlocks()) blocks.push(code);
        iframe.srcdoc = blocks.join('');
    }

    async stop(run_id) {}
}

class Console {
    constructor(out) {
        this.out = out;
        this.counts = {};
    }

    _log({stream, prefix, args}) {
        this.out.write(
            stream ?? '', `\
${prefix ?? ''}${(args ?? []).map(v => v.toString()).join(" ")}\n`);
    }

    assert(cond, ...args) {
        console.assert(cond, ...args);
        if (!cond) {
            if (args.length === 0) args = ['console.assert'];
            this._log({stream: 'err', args});
        }
    }

    clear() {
        console.clear();
        this.out.write('', '\x0c');
    }

    count(label) {
        console.count(label);
        label ??= 'default';
        const v = this.counts[label] = (this.counts[label] ?? 0) + 1;
        this._log({args: [`${label}: ${v}`]});
    }

    countReset(label) {
        console.countReset(label);
        delete this.counts[label ?? 'default'];
    }

    debug(...args) { console.debug(...args); }
    dir(...args) { console.dir(...args); }
    dirxml(...args) { console.dirxml(...args); }
    error(...args) { console.error(...args); }
    group(...args) { console.group(...args); }
    groupCollapsed(...args) { console.groupCollapsed(...args); }
    groupEnd(...args) { console.groupEnd(...args); }
    info(...args) { console.info(...args); }

    log(...args) {
        console.log(...args);
        this._log({args});
    }

    table(...args) { console.table(...args); }
    time(...args) { console.time(...args); }
    timeEnd(...args) { console.timeEnd(...args); }
    timeLog(...args) { console.timeLog(...args); }
    trace(...args) { console.trace(...args); }
    warn(...args) { console.warn(...args); }
}

Executor.apply(HtmlExecutor);  // Background
