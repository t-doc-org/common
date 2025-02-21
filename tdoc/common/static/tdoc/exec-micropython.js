// Copyright 2025 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {element, enc, text} from './core.js';
import {Executor} from './exec.js';
import {MicroPython} from './micropython.js';
import {getSerials, onSerial, requestSerial} from './serial.js';

const form_feed = '\x0c';

class MicroPythonExecutor extends Executor {
    static runner = 'micropython';
    static highlight = 'python';

    static async init() {}

    constructor(node) {
        super(node);
        this.decoders = new Map();
        this.mp = new MicroPython((...args) => this.writeConsole(...args),
                                  (...args) => this.onRelease(...args));
    }

    addControls(controls) {
        if (this.when !== 'never') {
            this.runCtrl = controls.appendChild(this.runControl());
            controls.appendChild(this.toolsControl());
            this.input = this.inputControl(data => this.mp.send(data + '\r\n'));
        }
        super.addControls(controls);
    }

    toolsControl() {
        const ctrl = element(`
<div class="dropstart">\
<button class="tdoc fa-screwdriver-wrench" title="Tools"\
 data-bs-toggle="dropdown" data-bs-offset="-7,4"></button>\
<ul class="dropdown-menu"></ul>\
</div>`);
        const ul = ctrl.querySelector('ul');
        ul.appendChild(this.menuItem('plug', 'Connect', '',
                                     () => this.connect()));
        ul.appendChild(this.menuItem(
            'power-off', 'Hard reset', ' if-connected disabled',
            () => this.reset()));
        ul.appendChild(this.menuItem(
            'file-arrow-up', 'Write to <code>main.py</code>',
            ' if-connected disabled', () => this.writeMain()));
        ul.appendChild(this.menuItem(
            'trash', 'Remove <code>main.py</code>', ' if-connected disabled',
            () => this.removeMain()));
        return ctrl;
    }

    menuItem(icon, text, cls, onClick) {
        const it = element(`\
<li><a class="dropdown-item${cls}">\
<span class="btn__icon-container tdoc fa-${icon}"></span>\
<span class="btn__text-container">${text}</span>\
</a></li>`);
        it.querySelector('a').addEventListener('click', onClick);
        return it;
    }

    inputControl(onSend) {
        const div = this.render(
            '\uffff_1', `<div class="tdoc-input"></div>`);
        const input = div.appendChild(element(`\
<input class="input" autocapitalize="off" autocomplete="off"\
 autocorrect="off" spellcheck="false">`));
        const btn = div.appendChild(element(`\
<button class="tdoc-send" title="Send input (Enter)">Send</button>`));
        btn.addEventListener('click', () => {
            const value = input.value;
            input.value = '';
            onSend(value);
        });
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.altKey && !e.ctrlKey && !e.metaKey) {
                e.preventDefault();
                btn.click();
            }
        });
        div.appendChild(this.stopControl());
        return div;
    }

    onReady() {
        this.enableInput(false);
        this.setSerial();
        onSerial(this, {
            onConnect: s => { if (!this.mp.serial) this.setSerial(s); },
            onDisconnect: s => { if (this.mp.serial === s) this.setSerial(); }
        });
        const serials = getSerials();
        if (serials.length === 1) this.setSerial(serials[0]);
    }

    enableInput(enable) {
        enable = enable ?? this.mp.claim;
        for (const el of this.input.querySelectorAll('input, button')) {
            el.disabled = !enable;
        }
    }

    setSerial(serial) {
        this.mp.setSerial(serial);
        this.runCtrl.disabled = !serial;
        for (const el of this.node.querySelectorAll(
                '.tdoc-exec-controls .dropdown-item.if-connected')) {
            el.classList.toggle('disabled', !serial);
        }
    }

    async connect() {
        this.setSerial();
        this.clearConsole();
        try {
            this.setSerial(await requestSerial());
            await this.mp.claimSerial(false);
            this.enableInput();
        } catch (e) {
            if (e.name !== 'NotFoundError') {
                this.writeConsole('err', `${e.toString()}\n`);
            }
        }
    }

    onRelease(reason) {
        this.enableInput(false);
        if (reason) this.writeConsole('err', `${reason}\n`);
    }

    async rawRepl(fn) {
        this.clearConsole();
        this.enableInput(false);
        try {
            await this.mp.rawRepl(fn);
        } catch (e) {
            this.writeConsole('err', `${e.toString()}\n`);
        } finally {
            this.enableInput();
        }
    }

    getCode() {
        const blocks = [];
        for (const {code} of this.codeBlocks()) blocks.push(code);
        return blocks.join('');
    }

    async doRun() {
        await this.rawRepl(async () => {
            await this.mp.softReboot();
            await this.mp.exec(this.getCode(), true);
        });
    }

    async doStop() {
        await this.mp.interrupt();
    }

    async reset() {
        await this.rawRepl(async () => {
            await this.mp.exec(`import machine; machine.reset()`, true);
        });
    }

    async writeMain() {
        await this.rawRepl(async () => {
            await this.mp.writeFile('main.py', enc.encode(this.getCode()));
        });
        this.writeConsole('', `Program written to main.py\n`);
    }

    async removeMain() {
        await this.rawRepl(async () => {
            await this.mp.removeFile('main.py');
        });
        this.writeConsole('', `File main.py removed\n`);
    }

    clearConsole() {
        if (!this.out) return;
        this.out.parentNode.remove();
        delete this.out;
        this.decoders.clear();
    }

    writeConsole(stream, data, done) {
        // Convert to string if necessary.
        if (typeof data !== 'string') {
            let dec = this.decoders.get(stream);
            if (!dec) {
                dec = new TextDecoder();
                this.decoders.set(stream, dec);
            }
            data = dec.decode(data, {stream: !done});
        }

        // Handle form feed characters by clearing the output.
        const i = data.lastIndexOf(form_feed);
        if (i >= 0) {
            data = data.slice(i + 1);
            if (this.out) {
                if (data.length > 0) {
                    this.out.replaceChildren();
                } else {
                    this.out.parentNode.remove();
                    delete this.out;
                }
            }
        }

        // Create the output node if necessary.
        if (data.length === 0) return;
        if (!this.out) {
            const div = this.render(
                '\uffff_0', `<div class="highlight"><pre></pre></div>`);
            div.appendChild(element(`\
<button class="fa-xmark tdoc-remove" title="Remove"></button>`))
                .addEventListener('click', () => {
                    div.remove();
                    delete this.out;
                });
            this.out = div.querySelector('pre');
            this.setOutputStyle(this.out);
        }

        // Append the text and scroll if at the bottom.
        let node = text(data);
        if (stream) {
            const el = element(`<span class="${stream}"></span>`);
            el.appendChild(node);
            node = el;
        }
        const atBottom = Math.abs(this.out.scrollHeight - this.out.scrollTop
                                  - this.out.clientHeight) <= 1;
        this.out.appendChild(node);
        if (atBottom) {
            this.out.scrollTo(this.out.scrollLeft, this.out.scrollHeight);
        }
    }

    render(name, html) {
        const new_el = element(html);
        new_el.tdocName = name;
        if (!this.output) {
            this.output = element(
                `<div class="tdoc-exec-output tdoc-sectioned"></div>`);
            this.appendOutputs([this.output]);
        }
        for (const el of this.output.children) {
            if (el.tdocName > name) {
                el.before(new_el);
                return new_el;
            }
            if (el.tdocName === name) {
                el.replaceWith(new_el);
                return new_el;
            }
        }
        this.output.appendChild(new_el);
        return new_el;
    }
}

Executor.apply(MicroPythonExecutor);
