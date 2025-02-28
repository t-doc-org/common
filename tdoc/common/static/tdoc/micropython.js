// Copyright 2025 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {dec, enc, FifoBuffer, sleep, timeout, toRadix} from './core.js';

// TODO: Add support for raw paste mode
// <https://github.com/micropython/micropython/blob/master/tools/pyboard.py>

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

function hexDigit(v) {
    v -= 0x30;  // '0'
    if (v < 0) throw new Error("Invalid hex digit");
    if (v < 10) return v;
    v -= 0x11;  // 'A' - '0'
    if (v < 6) return 10 + v;
    v -= 0x20;  // 'a' - 'A'
    if (v < 6) return 10 + v;
    throw new Error("Invalid hex digit");
}

function fromHex(data) {
    const len = data.length / 2;
    for (let i = 0; i < len; ++i) {
        const h = data.at(2 * i), l = data.at(2 * i + 1);
        data.set([hexDigit(data.at(2 * i)) << 4
                  | hexDigit(data.at(2 * i + 1))], i);
    }
    return data.subarray(0, len);
}

export class MicroPython {
    constructor(onRead, onRelease) {
        this._onRead = onRead;
        this._onRelease = onRelease;
    }

    setSerial(serial) {
        if (this.claim) this.claim.release();
        this.serial = serial;
        this.options = findOptions(serial);
    }

    async claimSerial(force = true) {
        if (this.claim || !this.serial) return;
        if (!force && this.serial.claimed) return;
        this.claim = await this.serial.claim(
            this.options.open, (...args) => this.onRead(...args),
            (...args) => this.onRelease(...args));
        if (this.options.signals) this.claim.setSignals(this.options.signals);
    }

    onRelease(reason) {
        delete this.claim;
        this._onRelease(reason);
    }

    async send(data) {
        if (typeof data === 'string') data = enc.encode(data);
        if (this.claim) await this.claim.send(data);
    }

    get capturing() { return !!this.cap; }

    startCapture() {
        if (this.capturing) return;
        this.cap = new FifoBuffer();
        this.notifyCapture();
    }

    notifyCapture() {
        const notify = this.capNotify;
        const {promise, resolve} = Promise.withResolvers();
        this.capAvailable = promise;
        this.capNotify = resolve;
        if (notify) notify();
    }

    stopCapture(prompt) {
        if (!this.capturing) return;
        const cap = this.cap;
        delete this.cap;
        delete this.capAvailable, this.capNotify;
        this.stream = '';
        if (cap.length > 0) this._onRead(this.stream, cap.read(cap.length));
    }

    onRead(data, done) {
        if (this.capturing) {
            if (data.length === 0) return;
            this.cap.write(data);
            this.notifyCapture();
            return;
        }
        while (this.streaming) {
            const i = data.indexOf(0x04);
            if (i < 0) break;
            this._onRead(this.stream, data.subarray(0, i), true);
            data = data.subarray(i + 1);
            if (this.stream === '') {
                this.stream = 'err';
            } else if (this.stream === 'err') {
                this.streaming = false;
                this.stream = '';
                this.exitRawRepl();
                break;
            }
        }
        this._onRead(this.stream, data, done);
    }

    async rawRepl(fn) {
        try {
            await this.claimSerial();
            this.startCapture();
            this.streaming = false;
            await this.interrupt();
            await this.enterRawRepl();
            await this.expect('raw REPL; CTRL-B to exit\r\n>');
            await fn();
        } finally {
            if (!this.streaming) {
                this.stream = '';
                await this.exitRawRepl();
                await this.expect('\r\n>>> ');
            }
            this.stopCapture();
        }
    }

    async softReboot() {
        await this.eot();
        await this.expect('soft reboot\r\n');
        await this.expect('raw REPL; CTRL-B to exit\r\n>');
    }

    async exec(code, streaming) {
        if (typeof code === 'string') code = enc.encode(code);
        await this.sendChunked(code);
        await this.eot();
        const resp = dec.decode(await this.recv(2));
        if (resp !== 'OK') throw new Error(`Failed to execute code: ${resp}`);
        if (streaming) this.streaming = true;
    }

    async sendChunked(data) {
        let i = 0;
        while (i < data.length) {
            let end = i + 256;
            if (end > data.length) end = data.length;
            await this.send(data.subarray(i, end));
            i = end;
            await sleep(10);
        }
    }

    async run(code) {
        await this.exec(code);
        const out = await this.expect('\x04');
        const err = await this.expect('\x04>');
        if (err.length > 0) throw new Error(dec.decode(err));
        return out;
    }

    async readFile(path, data) {
        // Prepend os.sep if it exists. This handles platforms with
        // non-hierarchical filesystems (e.g. BBC micro:bit) gracefully.
        try {
            return fromHex(await this.run(`\
import os
with open(getattr(os, 'sep', '') + ${pyStr(path)}, 'rb') as f:
  while True:
    d = f.read(1)
    if not d: break
    print('{:02x}'.format(d[0]), end='')
`));
        } catch (e) {
            if (!e.message.includes('ENOENT')) throw e;
            throw new Error(`File not found: ${path}`);
        }
    }

    async writeFile(path, data) {
        await this.run(`\
import os
f = open(getattr(os, 'sep', '') + ${pyStr(path)}, 'wb')
w = f.write
`);
        const chunkSize = 256;
        while (data.length > 0) {
            const s = pyBytes(data.subarray(0, chunkSize));
            await this.run(`w(${s})`);
            data = data.subarray(chunkSize);
        }
        await this.run(`f.close()`);
    }

    async removeFile(path, data) {
        await this.run(`\
import os
try: os.remove(getattr(os, 'sep', '') + ${pyStr(path)})
except OSError as e:
  import errno
  if e.errno != errno.ENOENT: raise
`);
    }

    enterRawRepl() { return this.send('\r\x01'); }
    exitRawRepl() { return this.send('\r\x02'); }
    interrupt() { return this.send('\r\x03'); }
    eot() { return this.send('\x04'); }

    async recv(count, ms = 1000) {
        const cancel = timeout(ms);
        while (this.cap.length < count) {
            await Promise.race([this.capAvailable, cancel]);
        }
        cancel.catch(e => undefined);  // Prevent logging
        return this.cap.read(count);
    }

    async expect(want, ms = 1000) {
        if (typeof want === 'string') want = enc.encode(want);
        const cancel = timeout(ms);
        let pos = 0;
        for (;;) {
            const i = this.cap.indexOf(want, pos);
            if (i >= 0) {
                const data = this.cap.read(i);
                this.cap.drop(want.length);
                cancel.catch(e => undefined);  // Prevent logging
                return data;
            }
            pos = this.cap.length - want.length + 1;
            if (pos < 0) pos = 0;
            await Promise.race([this.capAvailable, cancel]);
        }
    }
}
