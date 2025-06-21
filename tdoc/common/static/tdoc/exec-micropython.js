// Copyright 2025 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {dec, elmt, enc, html, on, qs, qsa, text} from './core.js';
import {Executor} from './exec.js';
import {MicroPython} from './micropython.js';
import {getSerials, onSerial, requestSerial} from './serial.js';

class MicroPythonExecutor extends Executor {
    static runner = 'micropython';
    static highlight = 'python';

    constructor(node) {
        super(node);
        this.output = this.sectionedOutput();
        this.console = this.output.consoleOut('990');
        this.mp = new MicroPython((...args) => this.console.write(...args),
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
        const ctrl = elmt`
<div class="dropstart">\
<button class="tdoc fa-screwdriver-wrench" title="Tools"\
 data-bs-toggle="dropdown" data-bs-offset="-7,4"></button>\
<ul class="dropdown-menu"></ul>\
</div>`;
        const ul = qs(ctrl, 'ul');
        ul.appendChild(this.menuItem('plug', 'Connect', '',
                                     () => this.connect()));
        ul.appendChild(this.menuItem(
            'power-off', 'Hard reset', ' if-connected disabled',
            () => this.reset()));
        ul.appendChild(this.menuItem(
            'file-arrow-down', html`Read <code>main.py</code>`,
            ' if-connected disabled', () => this.readMain()));
        ul.appendChild(this.menuItem(
            'file-arrow-up', html`Write to <code>main.py</code>`,
            ' if-connected disabled', () => this.writeMain()));
        ul.appendChild(this.menuItem(
            'trash', html`Remove <code>main.py</code>`,
            ' if-connected disabled', () => this.removeMain()));
        return ctrl;
    }

    menuItem(icon, label, cls, onClick) {
        const li = elmt`\
<li><a class="dropdown-item${cls}">\
<span class="btn__icon-container tdoc fa-${icon}"></span>\
<span class="btn__text-container"></span>\
</a></li>`;
        if (typeof label === 'string') label = text(label);
        qs(li, '.btn__text-container').appendChild(label);
        on(qs(li, 'a')).click(onClick);
        return li;
    }

    inputControl(onSend) {
        const {div} = this.output.lineInput('991', null, input => {
            if (this.inhibitInput) return;
            const value = input.value;
            input.value = '';
            onSend(value);
        });
        const stop = div.appendChild(this.stopControl());
        stop.setAttribute('title', `${stop.getAttribute('title')} (Ctrl+C)`);
        const input = qs(div, 'input');
        on(input).keydown(e => {
            if (e.ctrlKey && e.key === 'c' && !e.altKey && !e.metaKey
                    && input.selectionStart === input.selectionEnd) {
                e.preventDefault();
                stop.click();
            }
        });
        return div;
    }

    onReady() {
        if (this.when === 'never') return;
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
        for (const el of qsa(this.input, 'input, button')) {
            el.disabled = !enable;
        }
    }

    setSerial(serial) {
        this.mp.setSerial(serial);
        this.runCtrl.disabled = !serial;
        for (const el of qsa(this.node,
                '.tdoc-exec-controls .dropdown-item.if-connected')) {
            el.classList.toggle('disabled', !serial);
        }
    }

    async connect() {
        this.setSerial();
        this.console.clear();
        try {
            this.setSerial(await requestSerial());
            await this.mp.claimSerial(false);
            this.enableInput();
        } catch (e) {
            if (e.name !== 'NotFoundError') {
                this.console.write('err', `${e.toString()}\n`);
            }
        }
    }

    onRelease(reason) {
        this.enableInput(false);
        if (reason) this.console.write('err', `${reason}\n`);
    }

    async rawRepl(fn, prompt) {
        this.console.clear();
        this.inhibitInput = true;
        try {
            await this.mp.rawRepl(async () => {
                this.enableInput();
                await fn();
            }, prompt);
        } catch (e) {
            if (e) this.console.write('err', `${e.toString().trimEnd()}\n`);
        } finally {
            this.inhibitInput = false;
        }
    }

    getCode() {
        const blocks = [];
        for (const {code} of this.codeBlocks()) blocks.push(code);
        return blocks;
    }

    async run() {
        await this.rawRepl(async () => {
            await this.mp.softReboot();
            const blocks = this.getCode();
            for (const [i, code] of blocks.entries()) {
                await this.mp.exec(code);
                this.inhibitInput = false;
                let err = false;
                await this.mp.execWait({
                    onOut: (...args) =>  this.console.write('', ...args),
                    onErr: (data, done) => {
                        this.console.write('err', data, done);
                        err ||= data.length > 0;
                    },
                });
                if (err) break;
                this.inhibitInput = true;
            }
        }, true);
    }

    async stop() {
        await this.mp.interrupt();
    }

    async doStop() {
        if (!this.running) await this.mp.interrupt();
        await super.doStop();
    }

    async reset() {
        await this.rawRepl(async () => {
            await this.mp.exec(`import machine; machine.reset()`, true);
        });
    }

    async readMain() {
        await this.rawRepl(async () => {
            const data = await this.mp.readFile('main.py');
            this.setEditorText(dec.decode(data));
            this.console.write('', `Program read from main.py\n`);
        });
    }

    async writeMain() {
        await this.rawRepl(async () => {
            await this.mp.writeFile('main.py',
                                    enc.encode(this.getCode().join('\n')));
            this.console.write('', `Program written to main.py\n`);
        });
    }

    async removeMain() {
        await this.rawRepl(async () => {
            await this.mp.removeFile('main.py');
            this.console.write('', `File main.py removed\n`);
        });
    }
}

Executor.apply(MicroPythonExecutor);  // Background
