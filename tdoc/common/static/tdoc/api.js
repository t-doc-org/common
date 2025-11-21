// Copyright 2025 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {
    AsyncStoredJson, backoff, bearerAuthorization, dec, domLoaded, elmt, enable,
    fetchJson, FifoBuffer, handleHashParams, htmlData, on, page, qs, qsa,
    showModal, sleep, Stored, StoredJson, toBase64, toModalMessage,
} from './core.js';
import {random} from './crypto.js';

function handleApiBackend() {
    handleHashParams(['api'], api => {
        backend.set(api);
        location.reload();
    });
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

export async function call(path, opts) {
    return await fetchJson(`${url}${path}`, opts);
}

class Auth extends EventTarget {
    static async create() {
        return new this(await AsyncStoredJson.create('tdoc:api:user'));
    }

    constructor(stored) {
        super();
        this.state = StoredJson.create('tdoc:api:state', undefined,
                                       sessionStorage);
        this.stored = stored;
        ({promise: this.ready, resolve: this.rReady} = Promise.withResolvers());
        this.handleHashParams();
        if (!this.initialized) {
            this.setToken(this.stored.get()?.token);  // Background
        }
    }

    async name() {
        if (this.ready) await this.ready;
        return this.data?.name;
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
        if (data) {
            htmlData.tdocLoggedIn = '';
        } else {
            delete htmlData.tdocLoggedIn;
        }
        if (this.rReady) {
            this.rReady();
            delete this.ready, this.rReady;
        }
        this.dispatchEvent(new CustomEvent('change'));
    }

    async call(path, opts) {
        return await call(path, {
            ...opts,
            headers: {
                ...bearerAuthorization(opts?.token ?? await this.token()),
                ...opts?.headers,
            },
        });
    }

    async info() {
        return await this.call(`/auth/info`);
    }

    async update(req) {
        return await this.call(`/auth/update`, {req});
    }

    async login({issuer, user}) {
        const cnonce = await toBase64(random(32));
        this.state.set({cnonce});
        const resp = await this.call(`/auth/login`, {
            req: {issuer, user, cnonce, href: location.href},
        });
        if (resp.token) {
            if (!await this.setToken(resp.token)) {
                throw Error("Failed to set token");
            }
            return;
        }
        if (resp.redirect) location.assign(resp.redirect);
    }

    async logout() {
        const token = await this.token();
        await this.setToken(undefined);
        await this.call(`/auth/logout`, {token});
    }

    async setToken(token) {
        this.initialized = true;
        if (!token) {
            await this.stored.set(undefined);
            this.set(undefined);
            return true;
        }
        try {
            const data = await this.call(`/user`, {token});
            data.token = token;
            await this.stored.set(data);
            this.set(data);
        } catch (e) {
            if (e.cause.status === 401) {  // UNAUTHORIZED
                await this.stored.set(undefined);
                this.set(undefined);
            }
            return false;
        }
        return true;
    }

    handleHashParams() {
        handleHashParams(['token', 'cnonce'], async (token, cnonce) => {
            if (!token) return;
            const hasToken = !!this.stored.get()?.token;
            if (!hasToken || (cnonce && cnonce === this.state.get()?.cnonce)) {
                this.state.set(undefined);
                await this.setToken(token);
                if (hasToken) await this.showSettingsModal();
            }
        });
        handleHashParams(['error'], error => {
            // TODO: Display notification or modal dialog
            alert(error);
        });
    }

    onDomLoaded() {
        // Update the username shown in the user menu.
        const el = qs(document, '.dropdown-user .dropdown-item.btn-user');
        el.classList.add('disabled');
        this.onChange(async () => {
            const name = await auth.name();
            qs(el, '.btn__text-container')
                .replaceChildren(name !== undefined ? name : "Not logged in");
        });
    }

    async showLoginModal() {
        const info = await this.info();
        const el = elmt`\
<div class="modal fade" tabindex="-1" aria-hidden="true"\
 aria-labelledby="tdoc-modal-title">\
<div class="modal-dialog"><div class="modal-content">\
<div class="modal-header">\
<h1 class="modal-title fs-5" id="tdoc-modal-title">Log in</h1>\
<button type="button" class="btn-close" data-bs-dismiss="modal"\
 aria-label="Close"></button>\
</div><div class="modal-body vstack gap-3">\
<form class="hstack gap-2 text-nowrap login hidden">
<label for="tdoc-login-user" class="col-form-label">User:</label>\
<input type="text" class="form-control" id="tdoc-login-user" value="admin">\
<button type="submit" class="btn btn-primary login" disabled>Log in</button>\
</form>\
<div class="hstack gap-2 text-nowrap issuers"></div>\
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
        this.addIssuerButtons(el, "Log in with", info.issuers);

        const modal = showModal(el);
        on(input).input(() => enable(input.value, loginBtn));
        on(loginForm).submit(async e => {
            e.preventDefault();
            if (!input.value) return;
            await toModalMessage(el, async () => {
                await this.login({user: input.value});
                modal.hide();
            });
        });
    }

    async showSettingsModal() {
        const info = await this.info();
        const el = elmt`\
<div class="modal fade" tabindex="-1" aria-hidden="true"\
 aria-labelledby="tdoc-modal-title">\
<div class="modal-dialog modal-lg"><div class="modal-content">\
<div class="modal-header">\
<h1 class="modal-title fs-5" id="tdoc-modal-title">Settings</h1>\
<button type="button" class="btn-close" data-bs-dismiss="modal"\
 aria-label="Close"></button>\
</div><div class="modal-body vstack gap-3">\
<table class="table table-sm mb-0 text-nowrap logins"><thead>\
<tr class="px-2"><th class="w-100 px-2">Login</th><th class="px-2">Issuer</th>\
<th class="px-2">Last used</th><th class="px-2"></th></tr>\
</thead><tbody class="align-middle"></tbody></table>\
<div class="hstack gap-2 text-nowrap issuers"></div>\
</div><div class="modal-footer">\
<button type="button" class="btn btn-danger logout">Log out</button>\
<div class="flex-fill text-danger message"></div>\
<button type="button" class="btn btn-primary" data-bs-dismiss="modal">Close\
</button>\
</div></div></div>\
`;
        const logins = qs(el, 'table.logins > tbody');
        if (info.logins.length === 0) {
            logins.appendChild(elmt`\
<tr><td class="px-2" colspan="4">No logins</td></tr>`);
        }
        for (const login of info.logins) {
            const row = logins.appendChild(elmt`\
<tr><td class="px-2">${login.email}</td><td class="px-2">${login.issuer}</td>\
<td class="px-2">${login.updated}</td>\
<td><button type="button" class="btn btn-outline-danger">Remove</button></td>\
</tr>`);
            const btn = qs(row, 'button');
            if (info.logins.length < 2) enable(false, btn);
            on(btn).click(async () => {
                await toModalMessage(el, async () => {
                    await this.update({
                        remove: {iss: login.iss, sub: login.sub},
                    });
                    row.remove();
                    const btns = qsa(logins, 'button');
                    if (btns.length < 2) enable(false, ...btns);
                    return "Login removed";
                });
            });
        }
        this.addIssuerButtons(el, "Add login with", info.issuers);

        const modal = showModal(el);
        on(qs(el, '.logout')).click(async () => {
            await toModalMessage(el, async () => {
                await this.logout();
                modal.hide();
            });
        });
    }

    addIssuerButtons(modal, prefix, issuers) {
        const btns = qs(modal, '.issuers');
        if (issuers.length === 0) btns.classList.add('d-none');
        for (const {issuer, label} of issuers) {
            const btn = btns.appendChild(elmt`\
<div class="col-auto">\
<button type="button" class="btn btn-outline-primary">${prefix} ${label}\
</button>\
</div>\
`);
            on(btn).click(async () => {
                await toModalMessage(modal, async () => {
                    await auth.login({issuer});
                });
            });
        }
    }
}

export const auth = await Auth.create();
on(window).hashchange(() => auth.handleHashParams());
domLoaded.then(() => auth.onDomLoaded());
tdoc.login = async () => await auth.showLoginModal();
tdoc.settings = async () => await auth.showSettingsModal();

export function log(session, data, options) {
    return call(`/log`, {
        headers: bearerAuthorization(options?.token),
        req: {
            'time': Date.now(),
            'location': page.origin + page.path,
            'session': session, 'data': data,
        },
    });
}

export async function poll(req) {
    return await auth.call(`/poll`, {req});
}

export async function solutions(show) {
    return await auth.call(`/solutions`, {req: {page: page.path, show}});
}

export async function terminate(rc = 0) {
    return await call(`/terminate`, {req: {rc}});
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
            const resp = await auth.call(`/events/sub`, {req: req});
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
