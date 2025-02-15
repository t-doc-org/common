// Copyright 2025 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {element, enc, sleep, text, timeout} from './core.js';
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
            this.connectCtrl = controls.appendChild(this.connectControl());
        }
        super.addControls(controls);
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
        this.stream = 1;
        this.input = this.inputControl(async (data) => {
            await this.claimSerial();
            await this.send(data + '\r\n');
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
        this.input.querySelector('input').disabled = !serial;
        this.input.querySelector('button').disabled = !serial;
    }

    async claimSerial() {
        if (this.claim) return;
        this.claim = await this.serial.claim(
            {baudRate: 115200}, (...args) => this.onRead(...args),
            (...args) => this.onRelease(...args));
        // TODO: Disable input
    }

    get isControl() { return !!this.controlDecoder; }

    enterControl() {
        if (this.isControl) return;
        this.controlDecoder = new TextDecoder();
        this.controlData = '';
        this.notifyControl();
    }

    notifyControl() {
        const notify = this.controlNotify;
        const {promise, resolve} = Promise.withResolvers();
        this.controlPromise = promise;
        this.controlNotify = resolve;
        if (notify) notify();
    }

    exitControl() {
        if (!this.isControl) return;
        this.stream = 1;
        this.writeConsole(this.stream, enc.encode(this.controlData), false);
        delete this.controlDecoder, this.controlData;
        delete this.controlPromise, this.controlNotify;
        // TODO: Enable input
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
            this.clearConsole();
        } catch (e) {
            // TODO: Display error
        }
    }

    async send(data) {
        if (this.claim) await this.claim.send(enc.encode(data));
    }

    onRead(data, done) {
        if (this.isControl) {
            const s = this.controlDecoder.decode(data, {stream: !done});
            if (!s) return;
            this.controlData += s;
            this.notifyControl();
            return;
        }
        while (this.running) {
            const i = data.indexOf(0x04);
            if (i < 0) break;
            this.writeConsole(this.stream, data.subarray(0, i), true);
            data = data.subarray(i + 1);
            ++this.stream;
            if (this.stream > 2) {
                this.running = false;
                this.stream = 1;
                this.exitRawRepl();
                break;
            }
        }
        this.writeConsole(this.stream, data, done);
    }

    onRelease() {
        delete this.claim;
    }

    async doRun() {
        const blocks = [];
        for (const {code} of this.codeBlocks()) blocks.push(code);
        const code = blocks.join('');
        this.clearConsole();
        await this.claimSerial();
        await this.exec(code);
    }

    async doStop() {
        await this.claimSerial();
        await this.interrupt();
    }

    async exec(code) {
        this.enterControl();
        await this.rawRepl(true);
        await this.expect('>');
        while (code) {
            const data = code.slice(0, 256);
            await this.send(data);
            code = code.slice(256);
            await sleep(10);
        }
        await this.eot();
        const resp = await this.recv(2, 1000);
        if (resp !== 'OK') throw new Error(`Failed to execute: ${resp}`);
        this.running = true;
        this.exitControl();
    }

    async rawRepl(reset = false) {
        await this.interrupt();
        await this.enterRawRepl();
        if (reset) {
            await this.expect('raw REPL; CTRL-B to exit\r\n>', 1000);
            await this.eot();
            await this.expect('soft reboot\r\n', 1000);
        }
        await this.expect('raw REPL; CTRL-B to exit\r\n', 1000);
    }

    enterRawRepl() { return this.send('\r\x01'); }
    exitRawRepl() { return this.send('\r\x02'); }
    interrupt() { return this.send('\r\x03'); }
    eot() { return this.send('\x04'); }

    async recv(count, ms) {
        const cancel = timeout(ms);
        while (this.controlData.length < count) {
            await Promise.race([this.controlPromise, cancel]);
        }
        const data = this.controlData.slice(0, 2);
        this.controlData = this.controlData.slice(2);
        return data;
    }

    async expect(want, ms) {
        const cancel = timeout(ms);
        let pos = 0;
        for (;;) {
            const i = this.controlData.indexOf(want, pos);
            if (i >= 0) {
                this.controlData = this.controlData.slice(i + want.length);
                return;
            }
            pos = this.controlData.length - want.length + 1;
            if (pos < 0) pos = 0;
            await Promise.race([this.controlPromise, cancel]);
        }
    }

    clearConsole() {
        if (!this.out) return;
        this.out.parentNode.remove();
        delete this.out;
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
