// Copyright 2025 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {backoff, bearerAuthorization, dec, fetchJson, FifoBuffer, pageUrl, sleep} from './core.js';

export const url = (() => {
    if (tdoc.dev) return '/*api';
    if (tdoc.api_url) return tdoc.api_url;
    const loc = new URL(location);
    if (loc.host === 't-doc.org' || loc.host.endsWith('.t-doc.org')) {
        return `${loc.protocol}//api.t-doc.org`;
    }
    return null;
})();

export function log(session, data, options) {
    return fetchJson(`${url}/log`, {
        headers: bearerAuthorization(options?.token),
        body: {
            'time': Date.now(),
            'location': location.origin + location.pathname,
            'session': session, 'data': data,
        },
    });
}

export function solutions(show) {
    return fetchJson(`${url}/solutions`, {
        body: {page: pageUrl, show},
    });
}

export class Watch {
    static lastId = 0;

    constructor(req, onEvent, onFailed) {
        this.req = req;
        this.onEvent = onEvent;
        this.onFailed = onFailed ?? (() => {
            console.error(`Watch failure: ${JSON.stringify(this.req)}`);
        });
        this.id = ++this.constructor.lastId;
    }
}

class EventsApi {
    constructor() {
        this.watches = new Map();
    }

    async sub({add, remove}) {
        remove ??= [];
        add ??= [];
        for (const w of remove) this.watches.delete(w.id);
        for (const w of add) this.watches.set(w.id, w);
        if (!this.running) {
            if (this.watches.size === 0) return;
            this.run();  // In the background
            return;
        }
        const sid = await this.sid;
        if (sid === undefined) return;  // Current connection failed
        const req = {sid};
        if (remove.length > 0) {
            req.remove = [];
            for (const w of remove) req.remove.push(w.id);
        }
        if (add.length > 0) {
            req.add = [];
            for (const w of add) req.add.push({wid: w.id, req: w.req});
        }
        try {
            const resp = await fetchJson(`${url}/event/sub`, {body: req});
            this.reportFailed(resp.failed);
        } catch (e) {}
    }

    async run() {
        this.running = true;
        try {
            let retries = 0;
            for (;;) {
                let start = performance.now(), resolve;
                try {
                    const req = {};
                    if (this.watches.size > 0) {
                        req.add = [];
                        for (const w of this.watches.values()) {
                            req.add.push({wid: w.id, req: w.req});
                        }
                    }
                    ({promise: this.sid, resolve} = Promise.withResolvers());
                    await this.stream(req, resolve);
                } catch (e) {
                } finally {
                    resolve();
                    delete this.sid;
                }
                if (performance.now() - start > 30000) retries = 0;
                await sleep(backoff(1000, 10000, retries++));
            }
        } finally {
            this.running = false;
        }
    }

    async stream(req, connected) {
        const abort = new AbortController();
        try {
            const resp = await fetch(`${url}/event/watch`, {
                method: 'POST', cache: 'no-cache', referrer: '',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(req),
                signal: abort.signal,
            });
            if (resp.status !== 200) return;
            const reader = resp.body.getReader();
            try {
                const buffer = new FifoBuffer();
                for (;;) {
                  const {value, done} = await reader.read();
                  if (value) {
                      let start = buffer.length;
                      buffer.write(value);
                      for (;;) {
                          const pos = buffer.findValue(10, start);
                          if (pos < 0) break;
                          const msg = dec.decode(buffer.read(pos + 1));
                          start = 0;
                          if (connected) {
                            const data = JSON.parse(msg);
                            this.sid = data.sid;
                            connected(data.sid);
                            connected = undefined;
                            this.reportFailed(data.failed);
                          } else if (msg.length > 1) {
                              await this.onEvent(msg);
                          }
                      }
                  }
                  if (done) break;
                }
            } finally {
                reader.releaseLock();
            }
        } finally {
            abort.abort();
        }
    }

    async onEvent(msg) {
        const data = JSON.parse(msg);
        const watch = this.watches.get(data.wid);
        if (watch === undefined) return;
        try {
            await watch.onEvent(data.data);
        } catch (e) {
            console.error(e);
        }
    }

    reportFailed(failed) {
        for (const wid of failed ?? []) {
            const w = this.watches.get(wid);
            if (w !== undefined && w.onFailed) w.onFailed();
        }
    }
}

export const events = new EventsApi();
