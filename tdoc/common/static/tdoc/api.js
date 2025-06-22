// Copyright 2025 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {
    backoff, bearerAuthorization, dec, fetchJson, FifoBuffer, on, page, sleep,
    Stored, StoredJson,
} from './core.js';

function handleApiBackend() {
    const params = page.hashParams;
    if (!params) return;
    const api = params.get('api');
    if (api === null) return;
    backend.value = api;
    params.delete('api');
    page.hashParams = params;
    location.reload();
}

const backend = new Stored('tdoc:api:backend', undefined, sessionStorage);
handleApiBackend();
on(window).hashchange(() => handleApiBackend());

export const url = (() => {
    if (tdoc.dev) return '/*api';
    if (tdoc.api_url) return tdoc.api_url;
    const loc = new URL(location);
    if (loc.host === 't-doc.org' || loc.host.endsWith('.t-doc.org')) {
        const suffix = backend.value ? '-' + backend.value : '';
        return `${loc.protocol}//api${suffix}.t-doc.org`;
    }
    return null;
})();

class User extends EventTarget {
    static stored = new StoredJson('tdoc:api:user');

    constructor() {
        super();
        this.ready = new Promise(res => { this.resolve = res; });
        this.handleLogin();
        if (!this.initialized) this.login(this.constructor.stored.value?.token);
    }

    async token() {
        if (this.ready) await this.ready;
        return this.data?.token;
    }

    async member_of(group) {
        if (this.ready) await this.ready;
        const groups = this.data?.groups ?? [];
        return groups.includes(group) || groups.includes('*');
    }

    async onChange(fn) {
        await fn();
        this.addEventListener('change', fn);
    }

    set(data) {
        this.data = data;
        if (this.resolve) {
            this.resolve();
            delete this.ready, this.resolve;
        }
        this.dispatchEvent(new CustomEvent('change'));
    }

    async login(token) {
        this.initialized = true;
        if (!token) return this.logout();
        try {
            const data = await fetchJson(`${url}/user`, {
                headers: bearerAuthorization(token),
            });
            data.token = token;
            this.constructor.stored.value = data;
            this.set(data);
        } catch (e) {
            if (this.resolve) this.set(this.constructor.stored.value);
        }
    }

    logout() {
        this.initialized = true;
        this.constructor.stored.value = undefined;
        this.set(undefined);
    }

    handleLogin() {
        const params = page.hashParams
        if (!params) return;
        if (params.get('logout') !== null) {
            params.delete('logout');
            page.hashParams = params;
            this.logout();
        }
        const token = params.get('login');
        if (token) {
            params.delete('login');
            page.hashParams = params;
            this.login(token);  // Background
        }
    }
}

export const user = new User();
on(window).hashchange(() => user.handleLogin());

export function log(session, data, options) {
    return fetchJson(`${url}/log`, {
        headers: bearerAuthorization(options?.token),
        body: {
            'time': Date.now(),
            'location': page.origin + page.path,
            'session': session, 'data': data,
        },
    });
}

export async function poll(req) {
    return await fetchJson(`${url}/poll`, {
        headers: bearerAuthorization(await user.token()),
        body: req,
    });
}

export async function solutions(show) {
    return await fetchJson(`${url}/solutions`, {
        headers: bearerAuthorization(await user.token()),
        body: {page: page.path, show},
    });
}

export async function terminate(rc = 0) {
    return await fetchJson(`${url}/terminate`, {body: {rc}});
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
            const resp = await fetchJson(`${url}/events/sub`, {
                headers: bearerAuthorization(await user.token()),
                body: req,
            });
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
        this.token = await user.token();
        this.abort = new AbortController();
        try {
            const resp = await fetch(`${url}/events/watch`, {
                method: 'POST', cache: 'no-cache', referrer: '',
                headers: {
                    'Content-Type': 'application/json',
                    ...bearerAuthorization(this.token),
                },
                body: JSON.stringify(req),
                signal: this.abort.signal,
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
            this.abort.abort();
            delete this.abort;
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

    restartOnTokenChange(token) {
        if (this.abort && token !== this.token) this.abort.abort();
    }
}

export const events = new EventsApi();
user.onChange(async () => events.restartOnTokenChange(await user.token()));
