// Copyright 2025 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {element, enc, sleep, text, timeout, toRadix} from './core.js';
import {Executor} from './exec.js';
import {getSerials, onSerial, requestSerial} from './serial.js';

// TODO: Add support for raw paste mode
// <https://github.com/micropython/micropython/blob/master/tools/pyboard.py>

const form_feed = '\x0c';

const options = [{
//     // Raspberry Pi / MicroPython
//     match: {usbVendorId: 0x2e8a, usbProductId: 0x0005},
//     open: {baudRate: 1000000},
// }, {
//     // ARM Ltd / ARM mbed (BBC micro:bit)
//     match: {usbVendorId: 0x0d28, usbProductId: 0x0204},
//     open: {baudRate: 115200},
// }, {
    open: {baudRate: 115200},
}];

function findOptions(serial) {
    if (!serial) return;
    for (const opt of options) {
        if (serial.matches(opt.match)) return opt;
    }
}

function pyStr(s) {
    const parts = [`'`];
    for (const c of s) {
        const cp = c.codePointAt(0);
        parts.push(c == `'` ? `\\'` :
                   c == `\\` ? `\\\\` :
                   cp >= 0x20 && cp <= 0x7e ? c :
                   cp <= 0xff ? `\\x${toRadix(cp, 16, 2)}` :
                   cp <= 0xffff ? `\\u${toRadix(cp, 16, 4)}` :
                   `\\U${toRadix(cp, 16, 8)}`);

    }
    parts.push(`'`);
    return parts.join('');
}

function pyBytes(data) {
    const parts = [`b'`];
    for (const v of data) {
        parts.push(v == 0x27 ? `\\'` :
                   v == 0x5c ? `\\\\` :
                   v >= 0x20 && v <= 0x7e ? String.fromCharCode(v) :
                   `\\x${toRadix(v, 16, 2)}`);

    }
    parts.push(`'`);
    return parts.join('');
}

class MicroPythonExecutor extends Executor {
    static runner = 'micropython';
    static highlight = 'python';

    static async init() {}

    constructor(node) {
        super(node);
        this.decoders = new Map();
    }

    addControls(controls) {
        if (this.when !== 'never') {
            this.runCtrl = controls.appendChild(this.runControl());
            controls.appendChild(this.toolsControl());
            this.input = this.inputControl(data => this.send(data + '\r\n'));
        }
        super.addControls(controls);
    }

    toolsControl() {
        const ctrl = element(`
<div class="dropstart">\
<button class="fa-screwdriver-wrench tdoc-tools" title="Tools"\
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
<span class="btn__icon-container tdoc-icon fa-${icon}"></span>\
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
            onConnect: s => { if (!this.serial) this.setSerial(s); },
            onDisconnect: s => { if (this.serial === s) this.setSerial(); }
        });
        const serials = getSerials();
        if (serials.length === 1) this.setSerial(serials[0]);
    }

    enableInput(enable) {
        if (!this.input) return;
        for (const el of this.input.querySelectorAll('input, button')) {
            el.disabled = !enable;
        }
    }

    setSerial(serial) {
        this.serial = serial;
        this.options = findOptions(serial);
        this.runCtrl.disabled = !serial;
        for (const el of this.node.querySelectorAll(
                '.tdoc-exec-controls .dropdown-item.if-connected')) {
            el.classList.toggle('disabled', !serial);
        }
    }

    async connect() {
        if (this.claim) await this.claim.release();
        this.setSerial();
        this.clearConsole();
        try {
            this.setSerial(await requestSerial());
        } catch (e) {
            if (e.name !== 'NotFoundError') {
                this.writeConsole('err', `${e.toString()}\n`);
            }
        }
    }

    async claimSerial() {
        if (this.claim) return;
        this.claim = await this.serial.claim(
            this.options.open, (...args) => this.onRead(...args),
            (...args) => this.onRelease(...args));
        if (this.options.signals) this.claim.setSignals(this.options.signals);
    }

    onRelease(reason) {
        delete this.claim;
        this.enableInput(false);
        if (reason) this.writeConsole('err', `${reason}\n`);
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
        this.stream = '';
        this.writeConsole(this.stream, this.controlData);
        delete this.controlDecoder, this.controlData;
        delete this.controlPromise, this.controlNotify;
        this.enableInput(!!this.claim);
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
        while (this.executing) {
            const i = data.indexOf(0x04);
            if (i < 0) break;
            this.writeConsole(this.stream, data.subarray(0, i), true);
            data = data.subarray(i + 1);
            if (this.stream === '') {
                this.stream = 'err';
            } else if (this.stream === 'err') {
                this.executing = false;
                this.stream = '';
                this.exitRawRepl();
                break;
            }
        }
        this.writeConsole(this.stream, data, done);
    }

    getCode() {
        const blocks = [];
        for (const {code} of this.codeBlocks()) blocks.push(code);
        return blocks.join('');
    }

    async doRun() {
        this.inRawRepl(true, async () => {
            this.clearConsole();
            const code = this.getCode();
            await this.exec(code);
            this.executing = true;
        });
    }

    async doStop() {
        await this.interrupt();
    }

    async reset() {
        this.inRawRepl(false, async () => {
            this.clearConsole();
            await this.exec(`import machine; machine.reset()`);
        });
    }

    async writeMain() {
        this.inRawRepl(false, async () => {
            this.clearConsole();
            await this.writeFile('main.py', enc.encode(this.getCode()));
            await this.expect('>');
            this.writeConsole('', `Program written to main.py\n`);
        });
    }

    async removeMain() {
        this.inRawRepl(false, async () => {
            this.clearConsole();
            await this.removeFile('main.py');
            await this.expect('>');
            this.writeConsole('', `File main.py removed\n`);
        });
    }

    async writeFile(path, data) {
        // Prepend os.sep if it exists. This handles platforms with
        // non-hierarchical filesystems (e.g. BBC micro:bit) gracefully.
        await this.execWait(`\
import os
f = open(getattr(os, 'sep', '') + ${pyStr(path)}, 'wb')
w = f.write
`);
        const chunkSize = 256;
        while (data.length > 0) {
            const s = pyBytes(data.subarray(0, chunkSize));
            await this.execWait(`w(${s})`);
            data = data.subarray(chunkSize);
        }
        await this.execWait(`f.close()`);
    }

    async removeFile(path, data) {
        await this.execWait(`\
import os
try: os.remove(getattr(os, 'sep', '') + ${pyStr(path)})
except OSError as e:
  import errno
  if e.errno != errno.ENOENT: raise
`);
    }

    async execWait(code, ms = 1000) {
        await this.exec(code);
        const {out, err} = await this.waitOutput(ms);
        if (err) throw new Error(err);
        return out;
    }

    async exec(code) {
        await this.expect('>');
        while (code) {
            const data = code.slice(0, 256);
            await this.send(data);
            code = code.slice(256);
            await sleep(10);
        }
        await this.eot();
        const resp = await this.recv(2);
        if (resp !== 'OK') throw new Error(`Failed to execute code: ${resp}`);
    }

    async waitOutput(ms) {
        const out = await this.expect('\x04', ms);
        const err = await this.expect('\x04', ms);
        return {out, err}
    }

    async inRawRepl(reset, fn) {
        try {
            await this.claimSerial();
            this.enterControl();
            await this.interrupt();
            await this.enterRawRepl();
            if (reset) {
                await this.expect('raw REPL; CTRL-B to exit\r\n>');
                await this.eot();
                await this.expect('soft reboot\r\n');
            }
            await this.expect('raw REPL; CTRL-B to exit\r\n');
            await fn();
        } catch (e) {
            this.writeConsole('err', `${e.toString()}\n`);
        } finally {
            this.exitControl();
        }
    }

    enterRawRepl() { return this.send('\r\x01'); }
    exitRawRepl() { return this.send('\r\x02'); }
    interrupt() { return this.send('\r\x03'); }
    eot() { return this.send('\x04'); }

    async recv(count, ms = 1000) {
        const cancel = timeout(ms);
        while (this.controlData.length < count) {
            await Promise.race([this.controlPromise, cancel]);
        }
        cancel.catch(e => undefined);  // Prevent logging
        const data = this.controlData.slice(0, 2);
        this.controlData = this.controlData.slice(2);
        return data;
    }

    async expect(want, ms = 1000) {
        const cancel = timeout(ms);
        let pos = 0;
        for (;;) {
            const i = this.controlData.indexOf(want, pos);
            if (i >= 0) {
                const data = this.controlData.slice(0, i);
                this.controlData = this.controlData.slice(i + want.length);
                cancel.catch(e => undefined);  // Prevent logging
                return data;
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
