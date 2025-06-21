// Copyright 2025 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {dec, enc, FifoBuffer, sleep, timeout, toRadix} from './core.js';

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
        parts.push(c === `'` ? `\\'` :
                   c === `\\` ? `\\\\` :
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
        parts.push(v === 0x27 ? `\\'` :
                   v === 0x5c ? `\\\\` :
                   v >= 0x20 && v <= 0x7e ? String.fromCharCode(v) :
                   `\\x${toRadix(v, 16, 2)}`);

    }
    parts.push(`'`);
    return parts.join('');
}

function hexDigit(v) {
    v -= 0x30;  // '0'
    if (v < 0) throw new RangeError("Invalid hex digit");
    if (v < 10) return v;
    v -= 0x11;  // 'A' - '0'
    if (v < 6) return 10 + v;
    v -= 0x20;  // 'a' - 'A'
    if (v < 6) return 10 + v;
    throw new RangeError("Invalid hex digit");
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

class RemoteError extends Error {
    toString() { return this.message; }
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
        ({promise: this.pAbort, reject: this.abort} = Promise.withResolvers());
        this.claim = await this.serial.claim(
            this.options.open, (...args) => this.onRead(...args),
            (...args) => this.onRelease(...args));
        if (this.options.signals) this.claim.setSignals(this.options.signals);
    }

    onRelease(reason) {
        delete this.claim;
        if (this.abort) this.abort();
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
        const avail = this.avail;
        ({promise: this.pAvail, resolve: this.avail} = Promise.withResolvers());
        if (avail) avail();
    }

    stopCapture(prompt) {
        if (!this.capturing) return;
        const cap = this.cap;
        delete this.cap;
        delete this.pAvail, this.avail;
        if (cap.length > 0) this.onRead(cap.read(cap.length));
    }

    onRead(data, done) {
        if (!this.capturing) return this._onRead('', data, done);
        if (data.length === 0) return;
        this.cap.write(data);
        this.notifyCapture();
    }

    async rawRepl(fn, banner = false) {
        try {
            await this.claimSerial();
            this.useRawPaste = true;
            this.startCapture();
            await this.interrupt();
            await this.enterRawRepl();
            await this.expect('raw REPL; CTRL-B to exit\r\n>');
            await fn();
        } finally {
            await this.exitRawRepl();
            const prompt = enc.encode('\r\n>>> ');
            const onRead = banner ? (...args) => this._onRead('', ...args)
                                  : undefined;
            await this.expect(prompt, {onRead});
            this.stopCapture();
            this.onRead(prompt);
        }
    }

    async softReboot() {
        await this.eot();
        await this.expect('soft reboot\r\n');
        await this.expect('raw REPL; CTRL-B to exit\r\n>');
    }

    async exec(code) {
        if (typeof code === 'string') code = enc.encode(code);
        if (!this.useRawPaste || !await this.sendRawPaste(code)) {
            this.useRawPaste = false;
            await this.sendChunked(code);
        }
    }

    async execWait({ms = null, record = false, onOut, onErr} = {}) {
        const out = await this.expect('\x04', {ms, record, onRead: onOut});
        const err = await this.expect('\x04', {record, onRead: onErr});
        await this.expect('>');
        return {out, err};
    }

    async sendRawPaste(data) {
        await this.startRawPaste();
        switch (dec.decode(await this.recv(2))) {
        case 'R\x00': return false;  // Raw paste not supported
        case 'R\x01': break;  // Raw paste supported
        default:  // Device doesn't know about raw paste
            await this.expect('w REPL; CTRL-B to exit\r\n>')
            return false;
        }
        const resp = await this.recv(2);
        const winSize = resp.at(0) | (resp.at(1) << 8);
        let win = winSize;
        for (let i = 0; i < data.length;) {
            while (win === 0 || this.cap.length > 0) {
                const resp = (await this.recv(1)).at(0);
                if (resp === 0x01) {
                    win += winSize;
                } else if (resp === 0x04) {
                    await this.eot();
                    throw new Error("Code upload was aborted");
                } else {
                    throw new Error(`\
Unexpected response to code upload: 0x${toRadix(resp, 16, 2)}`);
                }
            }
            const len = Math.min(win, data.length - i);
            await this.send(data.subarray(i, i + len));
            win -= len;
            i += len;
        }
        await this.eot();
        await this.expect('\x04');
        return true;
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
        await this.eot();
        const resp = dec.decode(await this.recv(2));
        if (resp !== 'OK') throw new Error(`Code upload failed: ${resp}`);
    }

    async run(code, ms = 1000) {
        await this.exec(code);
        const {out, err} = await this.execWait({ms, record: true});
        if (err.length > 0) throw new RemoteError(dec.decode(err));
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
    d = f.read(64)
    if not d: break
    print(''.join('{:02x}'.format(b) for b in d), end='')
`, 60000));
        } catch (e) {
            if (e instanceof RangeError) {
                throw new Error(`Failed to read file: ${e.message}`);
            } else if (e instanceof RemoteError
                       && e.message.includes('ENOENT')) {
                throw new Error(`File not found: ${path}`);
            }
            throw e;
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
            await this.run(`w(${pyBytes(data.subarray(0, chunkSize))})`);
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
    startRawPaste() { return this.send('\x05A\x01'); }

    async recv(count, ms = 1000) {
        const cancel = timeout(ms);
        while (this.cap.length < count) {
            await Promise.race([this.pAvail, cancel, this.pAbort]);
        }
        cancel.catch(e => undefined);  // Prevent logging
        return this.cap.read(count);
    }

    async expect(want, {ms = 1000, record = false, onRead} = {}) {
        if (typeof want === 'string') want = enc.encode(want);
        const cancel = timeout(ms);
        let pos = 0;
        for (;;) {
            const i = this.cap.findData(want, pos);
            if (i >= 0) {
                if (onRead) onRead(this.cap.peek(pos, i));
                const data = record ? this.cap.read(i) : this.cap.drop(i);
                this.cap.drop(want.length);
                cancel.catch(e => undefined);  // Prevent logging
                return data;
            }
            const oldPos = pos;
            pos = this.cap.length - want.length + 1;
            if (pos < 0) pos = 0;
            if (onRead && pos > oldPos) onRead(this.cap.peek(oldPos, pos));
            if (!record) {
                this.cap.drop(pos);
                pos = 0;
            }
            await Promise.race([this.pAvail, cancel, this.pAbort]);
        }
    }
}
