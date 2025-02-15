// Copyright 2025 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {element, enc, text} from './core.js';
import {Executor} from './exec.js';
import {getSerials, requestSerial} from './serial.js';

const form_feed = 0x0c;
const requestOpts = {
    filters: [
        // Raspberry Pi Pico
        {usbVendorId: 0x2e8a, usbProductId: 0x0005},
    ],
}

class MicroPythonExecutor extends Executor {
    static runner = 'micropython';
    static highlight = 'python';

    static async init() {}

    constructor(node) {
        super(node);
        this.decoders = {};
    }

    addControls(controls) {
        if (this.when !== 'never') {
            this.runCtrl = controls.appendChild(this.runControl());
            this.stopCtrl = controls.appendChild(this.stopControl());
            this.rebootCtrl = controls.appendChild(this.rebootControl());
            this.connectCtrl = controls.appendChild(this.connectControl());
        }
        super.addControls(controls);
    }

    rebootControl() {
        const ctrl = element(`\
<button class="fa-power-off tdoc-reboot" title="Reboot target"></button>`);
        ctrl.addEventListener('click', () => this.reboot());
        return ctrl;
    }

    connectControl() {
        const ctrl = element(`\
<button class="fa-plug tdoc-connect" title="Connect"></button>`);
        ctrl.addEventListener('click', () => this.connect());
        return ctrl;
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
        return div;
    }

    onReady() {
        this.connected = false;
        this.input = this.inputControl(async (data) => {
            await this.claimSerial();
            await this.send(data + '\x0a\x0d');
        });
        this.setSerial();
        const serials = getSerials(requestOpts.filters);
        if (serials.length === 1) this.setSerial(serials[0]);
        // TODO: Register for connection events
    }

    setSerial(serial) {
        this.serial = serial;
        this.runCtrl.disabled = !serial;
        this.stopCtrl.disabled = !serial;
        this.rebootCtrl.disabled = !serial;
        this.input.querySelector('input').disabled = !serial;
        this.input.querySelector('button').disabled = !serial;
    }

    async claimSerial() {
        if (this.claim) return;
        this.claim = await this.serial.claim(
            {baudRate: 115200}, (...args) => this.onRead(...args),
            (...args) => this.onRelease(...args));
    }

    async connect() {
        if (this.claim) {
            await this.claim.release();
            delete this.claim;
        }
        this.setSerial();
        try {
            this.setSerial(await requestSerial(requestOpts));
            // TODO: Register for disconnection
        } catch (e) {}
    }

    async send(data) {
        if (this.claim) await this.claim.send(enc.encode(data));
    }

    onRead(data, done) {
        this.writeConsole(1, data, done);
    }

    onRelease() {
        delete this.claim;
    }

    async doRun() {
        await this.claimSerial();
        const blocks = [];
        for (const {code} of this.codeBlocks()) blocks.push(code);
        const code = blocks.join('');
        await this.send('\r\x03');
        await this.send('\r\x01');
        await this.send('\x04');
        await this.send(code);
        await this.send('\x04');
    }

    async doStop() {
        await this.claimSerial();
        await this.interruptTarget();
    }

    async reboot() {
        this.clearConsole();
        await this.claimSerial();
        await this.rebootTarget();
    }

    async interruptTarget() {
        await this.send('\r\x03');
        await this.send('\r\x02');
    }

    async rebootTarget() {
        await this.send('\r\x03');
        await this.send('\r\x02');
        await this.send('\x04');
    }

    clearConsole() {
        if (this.out) this.out.replaceChildren();
    }

    writeConsole(stream, data, done) {
        let dec = this.decoders[stream];
        if (!dec) dec = this.decoders[stream] = new TextDecoder();
        const i = data.lastIndexOf(form_feed);
        if (i >= 0) {
            data = data.subarray(i + 1);
            if (this.out) {
                if (data.length > 0) {
                    this.out.replaceChildren();
                } else {
                    this.out.parentNode.remove();
                    delete this.out;
                }
            }
        }
        if (data.length === 0) return;
        if (!this.out) {
            const div = this.render(
                '\uffff_0', `<div class="highlight"><pre></pre></div>`);
            if (this.runCtrl && !this.node.classList.contains('hidden')) {
                div.appendChild(element(`\
<button class="fa-xmark tdoc-remove hidden" title="Remove"></button>`))
                    .addEventListener('click', () => { div.remove(); });
            }
            this.out = div.querySelector('pre');
            this.setOutputStyle(this.out);
        }
        let node = text(dec.decode(data, {stream: !done}));
        if (stream === 2) {
            const el = element(`<span class="err"></span>`);
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
