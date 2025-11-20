// Copyright 2025 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {
    AsyncStoredJson, backoff, bearerAuthorization, dec, domLoaded, elmt, enable,
    fetchJson, FifoBuffer, handleHashParams, htmlData, on, page, qs, sleep,
    Stored,
} from './core.js';

function handleApiBackend() {
    const params = page.hashParams;
    if (!params) return;
    const api = params.get('api');
    if (api === null) return;
    backend.set(api);
    params.delete('api');
    page.hashParams = params;
    location.reload();
}

const backend = Stored.create('tdoc:api:backend', undefined, sessionStorage);
handleApiBackend();
on(window).hashchange(() => handleApiBackend());

export const url = (() => {
    if (tdoc.dev) return '/_api';
    if (tdoc.api_url) return tdoc.api_url;
    const loc = new URL(location);
    if (loc.host === 't-doc.org' || loc.host.endsWith('.t-doc.org')) {
        const b = backend.get();
        const suffix = b ? '-' + b : '';
        return `${loc.protocol}//api${suffix}.t-doc.org`;
    }
    return null;
})();

class Auth extends EventTarget {
    static async create() {
        return new this(await AsyncStoredJson.create('tdoc:api:user'));
    }

    constructor(stored) {
        super();
        this.stored = stored;
        ({promise: this.pReady, resolve: this.ready} = Promise.withResolvers());
        this.handleHashParams();
        if (!this.initialized) {
            this.setToken(this.stored.get()?.token);  // Background
        }
    }

    async name() {
        if (this.pReady) await this.pReady;
        return this.data?.name;
    }

    async token() {
        if (this.pReady) await this.pReady;
        return this.data?.token;
    }

    async member_of(group) {
        if (this.pReady) await this.pReady;
        const groups = this.data?.groups ?? [];
        return groups.includes(group) || groups.includes('*');
    }

    async onChange(fn) {
        await fn();
        this.addEventListener('change', fn);
    }

    set(data) {
        this.data = data;
        if (data) {
            htmlData.tdocLoggedIn = '';
        } else {
            delete htmlData.tdocLoggedIn;
        }
        if (this.ready) {
            this.ready();
            delete this.pReady, this.ready;
        }
        this.dispatchEvent(new CustomEvent('change'));
    }

    async fetchJson(url, opts) {
        return await fetchJson(url, {
            ...opts,
            headers: {
                ...bearerAuthorization(opts?.token ?? await this.token()),
                ...opts?.headers ?? {},
            },
        });
    }

    async info() {
        return await this.fetchJson(`${url}/auth/info`);
    }

    async login({provider, user}) {
        const data = await this.fetchJson(`${url}/auth/login`, {
            body: {provider, user, href: location.href},
        });
        if (data.token) {
            if (!await this.setToken(data.token)) {
                throw Error("Failed to set token.");
            }
            return;
        }
        if (data.redirect) location.assign(data.redirect);
    }

    async logout() {
        const token = await this.token();
        await this.setToken(undefined);
        await this.fetchJson(`${url}/auth/logout`, {token});
    }

    async setToken(token) {
        this.initialized = true;
        if (!token) {
            await this.stored.set(undefined);
            this.set(undefined);
            return true;
        }
        try {
            const data = await this.fetchJson(`${url}/user`, {token});
            data.token = token;
            await this.stored.set(data);
            this.set(data);
        } catch (e) {
            await this.stored.set(undefined);
            this.set(undefined);
            return false;
        }
        return true;
    }

    handleHashParams() {
        handleHashParams(['token', 'error'], (token, error) => {
            // TODO: Prevent CSRF via client-side nonce in sessionStorage.
            if (token) {
                this.setToken(token);  // Background
            }
            if (error) {
                // TODO: Display notification or modal dialog
                alert(error);
            }
        });
    }
}

export const auth = await Auth.create();
on(window).hashchange(() => auth.handleHashParams());

// Handle login / logout.
domLoaded.then(() => {
    const el = qs(document, '.dropdown-user .dropdown-item.btn-user');
    el.classList.add('disabled');
    auth.onChange(async () => {
        const name = await auth.name();
        qs(el, '.btn__text-container')
            .replaceChildren(name !== undefined ? name : "Not logged in");
    });
});

function showModal(el) {
    const modal = new bootstrap.Modal(el);
    on(el)['hide.bs.modal'](() => document.activeElement.blur());
    on(el)['hidden.bs.modal'](() => {
        modal.dispose();
        el.remove();
    });
    modal.show();
    return modal;
}

async function catchToMessage(modal, fn) {
    try {
        await fn();
    } catch (e) {
        const msg = qs(modal._element, '.message');
        msg.textContent = e.message;
        msg.classList.remove('hidden');
    }
}

function addProviderButtons(modal, prefix, providers) {
    const btns = qs(modal, '.providers');
    if (providers.length === 0) btns.classList.add('d-none');
    for (const {provider, label} of providers) {
        const btn = btns.appendChild(elmt`\
<div class="col-auto">\
<button type="button" class="btn btn-outline-primary">${prefix} ${label}\
</button>\
</div>\
`);
        on(btn).click(async () => {
            await catchToMessage(modal, async () => {
                await auth.login({provider});
            });
        });
    }
}

tdoc.login = async () => {
    const info = await auth.info();
    const el = elmt`\
<div class="modal fade" tabindex="-1" aria-hidden="true"\
 aria-labelledby="tdoc-login-title">\
<div class="modal-dialog"><div class="modal-content">\
<div class="modal-header">\
<h1 class="modal-title fs-5" id="tdoc-login-title">Log in</h1>\
<button type="button" class="btn-close" data-bs-dismiss="modal"\
 aria-label="Close"></button>\
</div><div class="modal-body vstack gap-3">\
<form class="hstack gap-2 text-nowrap login hidden">
<label for="tdoc-login-user" class="col-form-label">User:</label>\
<input type="text" class="form-control" id="tdoc-login-user" value="admin">\
<button type="submit" class="btn btn-primary login" disabled>Log in</button>\
</form>\
<div class="hstack gap-2 text-nowrap providers"></div>\
</div><div class="modal-footer">\
<div class="flex-fill text-danger message"></div>\
<button type="button" class="btn btn-primary" data-bs-dismiss="modal">Close\
</button>\
</div></div></div>\
`;
    const loginForm = qs(el, 'form.login');
    loginForm.classList.toggle('hidden', !tdoc.dev);
    const input = qs(loginForm, 'input#tdoc-login-user');
    const loginBtn = qs(loginForm, 'button.login');
    enable(input.value, loginBtn);
    addProviderButtons(el, "Log in with", info.providers);

    const modal = showModal(el);
    on(input).input(() => enable(input.value, loginBtn));
    on(loginForm).submit(async e => {
        e.preventDefault();
        if (!input.value) return;
        await catchToMessage(modal, async () => {
            await auth.login({user: input.value});
            modal.hide();
        });
    });
};

tdoc.settings = async () => {
    const info = await auth.info();
    console.log(info);
    const el = elmt`\
<div class="modal fade" tabindex="-1" aria-hidden="true"\
 aria-labelledby="tdoc-settings-title">\
<div class="modal-dialog"><div class="modal-content">\
<div class="modal-header">\
<h1 class="modal-title fs-5" id="tdoc-settings-title">Settings</h1>\
<button type="button" class="btn-close" data-bs-dismiss="modal"\
 aria-label="Close"></button>\
</div><div class="modal-body vstack gap-3">\
<div class="hstack gap-2 text-nowrap providers"></div>\
</div><div class="modal-footer">\
<button type="button" class="btn btn-danger logout">Log out</button>\
<div class="flex-fill text-danger message"></div>\
<button type="button" class="btn btn-primary" data-bs-dismiss="modal">Close\
</button>\
</div></div></div>\
`;
    addProviderButtons(el, "Add login with", info.providers);

    const modal = showModal(el);
    on(qs(el, '.logout')).click(async () => {
        await catchToMessage(modal, async () => {
            await auth.logout();
            modal.hide();
        });
    });
};

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
    return await auth.fetchJson(`${url}/poll`, {body: req});
}

export async function solutions(show) {
    return await auth.fetchJson(`${url}/solutions`, {
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
            const resp = await auth.fetchJson(`${url}/events/sub`, {body: req});
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
        this.token = await auth.token();
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
auth.onChange(async () => events.restartOnTokenChange(await auth.token()));
