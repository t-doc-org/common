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
        await this.serial.unclaim(this);
    }

    async send(data) {
        if (this.serial.claimed === this) await this.serial.send(data);
    }
}

const emptyData = new Uint8Array();

class Serial {
    constructor(port) {
        this.port = port;
    }

    async claim(options, onRead, onRelease) {
        await this.unclaim();
        const claim = new Claim(this, onRead, onRelease);
        await this.open(options);
        this.claimed = claim;
        return claim;
    }

    async unclaim(claim) {
        if (!this.claimed || (claim && this.claimed !== claim)) return;
        this.claimed.onRelease();
        delete this.claimed;
        await this.close();
    }

    async open(options) {
        await this.port.open(options);
        this.opened = true;
        this.streamer = this.stream();
    }

    async close() {
        this.opened = false;
        if (this.reader) await this.reader.cancel();
        if (this.streamer) await this.streamer;
    }

    async stream() {
        try {
            while (this.opened && this.port.readable) {
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
            // TODO: Report, maybe through onRelease
            console.error(e);
        } finally {
            this.opened = false;
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
        if (!this.opened) return;
        if (!this.writer && this.port.writable) {
            this.writer = this.port.writable.getWriter();
        }
        await this.writer.write(data);
    }
}

function matchesFilter(i, f) {
    return (!f.usbVendorId || (i.usbVendorId === f.usbVendorId)) &&
           (!f.usbProductId || (i.usbProductId === f.usbProductId)) &&
           (!f.bluetoothServiceClassId ||
               (i.bluetoothServiceClassId === f.bluetoothServiceClassId));
}

function matchesFilters(info, filters) {
    if (!filters || filters.length === 0) return true;
    for (const f of filters) {
        if (matchesFilter(info, f)) return true;
    }
    return false;
}

export function getSerials(filters) {
    const matching = [];
    for (const s of serials.values()) {
        if (matchesFilters(s.port.getInfo(), filters)) matching.push(s);
    }
    return matching;
}

export async function requestSerial(options) {
    const port = await navigator.serial.requestPort(options);
    let s = serials.get(port);
    if (!s) {
        s = new Serial(port);
        serials.set(port, s);
        if (s.port.connected) {
            for (const h of handlers.values()) {
                if (h.onConnect) h.onConnect(s);
            }
        }
    }
    return s;
}

export function onSerial(key, hs) {
    if (hs) {
        handlers.set(key, hs);
    } else {
        handlers.delete(key);
    }
}

const serials = new Map();
const handlers = new Map();
for (const port of await navigator.serial.getPorts()) {
    serials.set(port, new Serial(port));
}

navigator.serial.addEventListener('connect', e => {
    let s = serials.get(e.target);
    if (!s) {
        s = new Serial(e.target);
        serials.set(e.target, s);
    }
    for (const h of handlers.values()) {
        if (h.onConnect) h.onConnect(s);
    }
});

navigator.serial.addEventListener('disconnect', async e => {
    const s = serials.get(e.target);
    if (!s) return;
    await s.unclaim();
    for (const h of handlers.values()) {
        if (h.onDisconnect) h.onDisconnect(s);
    }
    serials.delete(e.target);
});
