// Copyright 2025 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {enc} from './core.js';

class Claim {
    constructor(serial, onRead, onRelease) {
        this.serial = serial;
        this.onRead = onRead;
        this.onRelease = onRelease;
    }

    async release() {
        if (this.serial.claimed !== this) return;
        this.onRelease();
        delete this.serial.claimed;
        await this.serial.disconnect();
    }

    async send(data) {
        if (this.serial.claimed === this) await this.serial.send(data);
    }
}

const emptyData = new Uint8Array();

class Serial {
    constructor(port) {
        this.connected = false;
        this.port = port;
    }

    async claim(options, onRead, onRelease) {
        if (this.claimed) {
            this.claimed.onRelease();
            delete this.claimed;
        }
        await this.disconnect();
        const claim = new Claim(this, onRead, onRelease);
        await this.connect(options);
        this.claimed = claim;
        return claim;
    }

    async connect(options) {
        await this.port.open(options);
        this.connected = true;
        this.streamer = this.stream();
    }

    async disconnect() {
        this.connected = false;
        if (this.reader) await this.reader.cancel();
        if (this.streamer) await this.streamer;
    }

    async stream() {
        console.log("Starting");
        try {
            while (this.connected && this.port.readable) {
                this.reader = this.port.readable.getReader();
                try {
                    for (;;) {
                      const {value, done} = await this.reader.read();
                      if (this.claimed && (value || done)) {
                          this.claimed.onRead(value ?? emptyData, done);
                      }
                      if (done) break;
                    }
                } finally {
                    this.reader.releaseLock();
                    delete this.reader;
                }
            }
        } catch (e) {
            console.error(e);
        } finally {
            console.log("Done");
            this.connected = false;
            if (this.writer) {
                await this.writer.close();
                this.writer.releaseLock();
                delete this.writer;
            }
            await this.port.close();
            delete this.streamer;
        }
    }

    async send(data) {
        if (!this.connected) return;
        if (!this.writer && this.port.writable) {
            this.writer = this.port.writable.getWriter();
        }
        await this.writer.write(data);
    }
}

const serials = {};
for (const port of await navigator.serial.getPorts()) {
    serials[port] = new Serial(port);
}

navigator.serial.addEventListener('connect', e => {
    if (!(e.target in serials)) serials[e.target] = new Serial(e.target);
});

navigator.serial.addEventListener('disconnect', async (e) => {
    const s = serials[e.target];
    if (s) {
        await s.disconnect();
        delete serials[e.target];
    }
});

function matchesFilter(i, f) {
    return (!f.usbVendorId || (i.usbVendorId === f.usbVendorId)) &&
           (!f.usbProductId || (i.usbProductId === f.usbProductId)) &&
           (!f.bluetoothServiceClassId ||
               (i.bluetoothServiceClassId === f.bluetoothServiceClassId));
}

function matchesFilters(info, filters) {
    for (const f of filters) {
        if (matchesFilter(info, f)) return true;
    }
    return false;
}

export function getSerials(filters) {
    const matching = [];
    for (const s of Object.values(serials)) {
        if (matchesFilters(s.port.getInfo(), filters)) matching.push(s);
    }
    return matching;
}

export async function requestSerial(options) {
    const port = await navigator.serial.requestPort(options);
    const s = serials[port];
    if (s) return s;
    return serials[port] = new Serial(port);
}
