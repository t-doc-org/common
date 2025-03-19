// Copyright 2025 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {enc, on, sleep} from './core.js';

// A claim on a serial port.
class Claim {
    constructor(serial, onRead, onRelease) {
        this.serial = serial;
        this.onRead = onRead;
        this.onRelease = onRelease;
    }

    release(reason) {
        return this.serial.unclaim(this, reason);
    }

    async send(data) {
        if (this.serial.claimed === this) await this.serial.send(data);
    }

    async setSignals(options) {
        if (this.serial.claimed === this) await this.serial.setSignals(options);
    }
}

const emptyData = new Uint8Array();

// A serial port that can be used by multiple clients.
class Serial {
    constructor(port) {
        this.port = port;
    }

    // Return true iff the port matches the given filter.
    matches(filter) {
        const i = this.port.getInfo();
        const matches = f => !f ||
            ((!f.usbVendorId || (i.usbVendorId === f.usbVendorId)) &&
             (!f.usbProductId || (i.usbProductId === f.usbProductId)) &&
             (!f.bluetoothServiceClassId ||
               (i.bluetoothServiceClassId === f.bluetoothServiceClassId)));
        if (filter instanceof Array) {
            if (filter.length === 0) return true;
            for (const f of filter) {
                if (matches(f)) return true;
            }
            return false;
        }
        return matches(filter);
    }

    // Claim the port. This snatches it away from the previous claimant.
    async claim(options, onRead, onRelease) {
        await this.unclaim();
        const claim = new Claim(this, onRead, onRelease);
        await this.open(options);
        this.claimed = claim;
        return claim;
    }

    // Release the port.
    unclaim(claim, reason) {
        if (!this.claimed || (claim && this.claimed !== claim)) return;
        this.claimed.onRelease(reason);
        delete this.claimed;
        return this.close();
    }

    // Open the port and start streaming received data.
    async open(options) {
        await this.port.open(options);
        this.opened = true;
        this.streamer = this.stream();
    }

    // Close the port.
    async close() {
        this.opened = false;
        if (this.reader) await this.reader.cancel();
        if (this.streamer) await this.streamer;
    }

    // Stream received data.
    async stream() {
        let reason = "The port was closed";
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
                      // Avoid blocking the UI if data is received continuously.
                      await sleep(undefined);
                    }
                } finally {
                    this.reader.releaseLock();
                    delete this.reader;
                }
            }
        } catch (e) {
            reason = e.toString();
        } finally {
            if (this.claimed) {
                this.claimed.onRelease(reason);
                delete this.claimed;
            }
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

    // Send data to the port.
    async send(data) {
        if (!this.opened) return;
        if (!this.writer && this.port.writable) {
            this.writer = this.port.writable.getWriter();
        }
        await this.writer.write(data);
    }

    // Set control signals on the port.
    async setSignals(options) {
        if (!this.opened) return;
        await this.port.setSignals(options);
    }
}

// Get a list of known serial ports matching the given filter.
export function getSerials(filter) {
    const matching = [];
    for (const s of serials.values()) {
        if (s.matches(filter)) matching.push(s);
    }
    return matching;
}

// Request that the user select a serial port.
export async function requestSerial(options) {
    if (!navigator.serial) {
        throw new Error("WebSerial is not supported on this browser");
    }
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

// Register or unregister handlers for port connection and disconnection.
export function onSerial(key, hs) {
    if (hs) {
        handlers.set(key, hs);
    } else {
        handlers.delete(key);
    }
}

const serials = new Map();
const handlers = new Map();

if (navigator.serial) {
    // Get notified on connection and disconnection.
    on(navigator.serial).connect(e => {
        let s = serials.get(e.target);
        if (!s) {
            s = new Serial(e.target);
            serials.set(e.target, s);
        }
        for (const h of handlers.values()) {
            if (h.onConnect) h.onConnect(s);
        }
    }).disconnect(async e => {
        const s = serials.get(e.target);
        if (!s) return;
        await s.unclaim(undefined, "The port was disconnected");
        for (const h of handlers.values()) {
            if (h.onDisconnect) h.onDisconnect(s);
        }
        serials.delete(e.target);
    });

    // Create Serial instances for all connected ports.
    for (const port of await navigator.serial.getPorts()) {
        serials.set(port, new Serial(port));
    }
}
