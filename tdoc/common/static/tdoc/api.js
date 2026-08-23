// Copyright 2025 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {
    AsyncStoredJson, backoff, bearerAuthorization, dec, domLoaded, elmt, enable,
    fetchJson, FifoBuffer, htmlData, localIso, on, onHashParams, page, qs,
    qsa, randomId, showAlert, showModal, sleep, Stored, StoredJson,
    toModalMessage,
} from './core.js';

const backend = new Stored('tdoc:api:backend', undefined, sessionStorage);
onHashParams(['api'], api => {
    backend.set(api);
    location.reload();
});

const [url, bes] = (() => {
    if (tdoc.local) return ['/_api', ''];
    if (tdoc.api_url) return [tdoc.api_url, ''];
    const loc = new URL(location);
    if (loc.host === 't-doc.org' || loc.host.endsWith('.t-doc.org')) {
        const b = backend.get();
        const suffix = b ? '-' + b : '';
        return [`${loc.protocol}//api${suffix}.t-doc.org`, suffix];
    }
    return ['/missing_api_url', ''];
})();

export async function call(path, opts) {
    return await fetchJson(`${url}${path}`, {
        credentials: 'include',
        ...opts,
        headers: {
            'X-Csrf': '0',
            ...bearerAuthorization(opts?.token),
            ...opts?.headers,
        },
    });
}

class Auth extends EventTarget {
    constructor() {
        super();
        this.user = new StoredJson(`tdoc:api${bes}:user-info`);
        this.domain = new AsyncStoredJson(`tdoc:domain:api${bes}:auth`, {});
        this.state = new StoredJson('tdoc:api:state', {}, sessionStorage);
        this.ready = this.init();
    }

    async init() {
        const hasUser = this.user.get();
        const state = this.state.get(), cnonce = state?.cnonce;
        this.state.update(v => { delete v.cnonce; });
        const [token, auth, error] = page.handleHashParams('token', 'auth',
                                                           'auth_error');
        if (token && !hasUser) {  // Initial login via token= URL
            await this.postLogin(state, token);
        } else if (auth && auth === cnonce) {  // Normal login flow
            const done = this.postLogin(state);
            if (!hasUser) await done;
        } else {
            // TODO: Get rid of domain storage, it's slow; use a cookie instead
            const domain = await this.domain.get();
            const done = this.updateUser({force: domain.loggedIn ?? false});
            if (!hasUser) await done;
        }
        if (error) this.postLoginError(state, error);  // Background

        // Update the username shown in the user menu.
        domLoaded.then(async () => {
            await domLoaded;
            const el = qs(document, '.dropdown-user .dropdown-item.btn-user');
            el.classList.add('disabled');
            this.onChange(() => {
                qs(el, '.btn__text-container').replaceChildren(
                    this.name ?? "Not logged in");
            });
        });
    }

    async postLogin(state, token) {
        const updated = await this.updateUser({token});
        (async () => {
            if (updated) {
                if (state?.modal === 'settings') {
                    await this.showSettingsModal(
                        "The login has been added successfully.");
                } else {
                    await showAlert(
                        `You have logged in successfully as "${this.name}".`);
                }
            } else {
                if (state?.modal === 'settings') {
                    await this.showSettingsModal(
                        "The login could not be added.", {kind: 'danger'});
                } else {
                    await showAlert("Logging in has failed.", {kind: 'danger'});
                }
            }
        })();  // Background
    }

    async postLoginError(state, error) {
        if (state?.modal === 'settings') {
            await this.showSettingsModal(error, {kind: 'danger'});
        } else {
            await showAlert(error, {kind: 'danger'});
        }
    }

    async updateUser({token, force = true} = {}) {
        let user = this.user.get(), res = true, loggedOut = false;
        if (force || user !== undefined) {
            try {
                user = await call(`/user`, {token});
            } catch (e) {
                res = false;
                if (e.cause?.status === 401) {  // UNAUTHORIZED
                    loggedOut = user !== undefined;
                    user = undefined;
                }
            }
        }
        this.set(user);
        this.domain.update(v => { v.loggedIn = user !== undefined; });  // BG
        if (loggedOut) {
            await showAlert("You have been logged out.",
                            {kind: 'warning', load: true});
            location.reload();
        }
        return res;
    }

    set(user) {
        this.user.set(user);
        if (user) {
            htmlData.tdocUserPerms = (user.perms ?? []).join(' ');
            htmlData.tdocUserTags = (user.tags ?? []).join(' ');
        } else {
            delete htmlData.tdocUserPerms;
            delete htmlData.tdocUserTags;
        }
        this.dispatchEvent(new CustomEvent('change'));
    }

    onChange(fn) {
        fn();
        this.addEventListener('change', fn);
    }

    get name() { return this.user.get()?.name; }
    get tags() { return this.user.get()?.tags ?? []; }

    hasPerm(perm) {
        const user = this.user.get();
        const perms = user?.perms ?? [];
        return perms.includes(perm) || perms.includes('*');
    }

    async info() {
        return await call(`/auth/info`);
    }

    async update(req) {
        return await call(`/auth/update`, {req});
    }

    async login(issuer) {
        const req = {
            issuer, href: location.href,
            cnonce: await randomId(33),
        };
        const resp = await call(`/auth/login`, {req});
        this.state.update(v => { v.cnonce = req.cnonce; });
        location.assign(resp.redirect);
    }

    async logout() {
        await call(`/auth/logout`);
        this.user.set(undefined);
        await this.domain.update(v => { v.loggedIn = false; });
        await showAlert("You have logged out successfully.",
                        {kind: 'warning', load: true});
        location.reload();
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
<form class="hstack gap-2 login hidden">
<label for="tdoc-login-user" class="col-form-label">User:</label>\
<input type="text" class="form-control" id="tdoc-login-user" value="admin">\
<button type="submit" class="btn btn-primary text-nowrap login" disabled>\
Log in</button>\
</form>\
<div class="hstack flex-wrap gap-2 text-nowrap issuers"></div>\
</div><div class="modal-footer flex-nowrap">\
<div class="flex-fill message"></div>\
<button type="button" class="btn btn-primary" data-bs-dismiss="modal">Close\
</button>\
</div></div></div>`;
        const loginForm = qs(el, 'form.login');
        loginForm.classList.toggle('hidden', !tdoc.local);
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
                await this.login(`local:${input.value}`);
                modal.hide();
            });
        });
    }

    async showSettingsModal(message, kind = 'success') {
        const [info, rauth] = await Promise.all([
            this.info(),
            call(`/repo`, {req: {info: true}}),
        ]);
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
<div class="hstack flex-wrap gap-2 text-nowrap issuers"></div>\
<div class="accordion repo hidden"><div class="accordion-item">\
<h2 class="accordion-header m-0">\
<button type="button" class="accordion-button collapsed p-2 fw-bold"\
 data-bs-toggle="collapse" data-bs-target="#tdoc-repo"\
 aria-controls="tdoc-repo">Repository access</button>\
</h2>\
<div class="accordion-collapse collapse rounded-0 overflow-hidden"\
 style="position: relative;" id="tdoc-repo">\
<pre class="hgrc m-0 border-0 p-2">\
[auth]
t-doc.prefix = ${tdoc.repos}
t-doc.username = <span class="user user-select-all"></span>
t-doc.password = <span class="pass user-select-all"></span>
</pre>\
<button type="button" class="reset btn btn-danger"\
 style="position: absolute; top: 0.5rem; right: 0.5rem;">Reset</button>
</div></div></div>\
</div><div class="modal-footer flex-nowrap">\
<button type="button" class="btn btn-danger text-nowrap logout">Log out\
</button>\
<div class="flex-fill text-${kind} message">${message ?? ""}</div>\
<button type="button" class="btn btn-primary" data-bs-dismiss="modal">Close\
</button>\
</div></div></div>`;
        const logins = qs(el, 'table.logins > tbody');
        if (info.logins.length === 0) {
            logins.appendChild(elmt`\
<tr><td class="px-2" colspan="4">No logins</td></tr>`);
        }
        for (const login of info.logins) {
            const updated = localIso(new Date(login.updated * 1e3));
            const row = logins.appendChild(elmt`\
<tr><td class="px-2">${login.name}</td><td class="px-2 text-nowrap">\
${login.issuer}</td><td class="px-2 text-nowrap">${updated}</td>\
<td><button type="button" class="btn btn-outline-danger">Remove</button></td>\
</tr>`);
            const btn = qs(row, 'button');
            if (info.logins.length < 2) enable(false, btn);
            on(btn).click(async () => {
                if (!confirm(`\
Are you sure you want to remove the login ${login.name}?`)) {
                    return;
                }
                await toModalMessage(el, async () => {
                    await this.update({
                        remove: {iss: login.iss, sub: login.sub},
                    });
                    row.remove();
                    const btns = qsa(logins, 'button');
                    if (btns.length < 2) enable(false, ...btns);
                    return `\
The login ${login.name} has been removed successfully.`;
                });
            });
        }
        this.addIssuerButtons(el, "Add login with", info.issuers);
        const repo = qs(el, '.repo');
        const hgrc = qs(repo, '.hgrc');
        const user = qs(hgrc, '.user');
        const pass = qs(hgrc, '.pass');
        if (rauth.enabled) {
            user.textContent = rauth.user;
            pass.textContent =
                rauth.prefix !== null ?
                rauth.prefix + '*'.repeat(48 - rauth.prefix.length)
                : "[no password set]";
            pass.classList.toggle('fst-italic', rauth.prefix === null);
            repo.classList.remove('hidden');
        }

        const modal = showModal(el);
        this.state.update(v => { v.modal = 'settings'; });
        on(el)['hidden.bs.modal'](() => {
            this.state.update(v => { delete v.modal; });
        });
        on(qs(repo, '.reset')).click(async e => {
            if (rauth.prefix !== null && !confirm(`\
Are you sure you want to reset the repository access password?

You will need to set the new password in your Mercurial configuration.`)) {
                return;
            }
            await toModalMessage(el, async () => {
                const resp = await call(`/repo`, {req: {reset: true}});
                user.textContent = resp.user;
                pass.textContent = resp.password;
                rauth.prefix = '';
                return `\
The password has been reset. Copy it now, as it won't be shown again.`;
            });
        });
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
<button type="button" class="btn btn-outline-primary text-nowrap">\
${prefix} ${label}</button>\
</div>`);
            on(btn).click(async () => {
                await toModalMessage(modal, async () => {
                    await this.login(issuer);
                });
            });
        }
    }
}

export const auth = new Auth();
await auth.ready;
console.info(`[t-doc] API backend: ${url}, user: ${auth.name ?? '<none>'}`);

tdoc.login = () => auth.showLoginModal();
tdoc.settings = () => auth.showSettingsModal();

export async function editor(req) {
    return await call(`/editor`, {req});
}

export async function poll(req) {
    return await call(`/poll`, {req});
}

export async function solutions(show) {
    return await call(`/solutions`, {req: {page: page.path, show}});
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
            // TODO: Delay startup so initial watches get aggregated
            this.run();  // Background
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
            const resp = await call(`/events/sub`, {req});
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
        this.abort = new AbortController();
        try {
            const resp = await fetch(`${url}/events/watch`, {
                method: 'POST', cache: 'no-store', referrer: '',
                credentials: 'include',
                headers: {
                    'Cache-Control': 'no-store',
                    'Content-Type': 'application/json',
                    'X-Csrf': '0',
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
}

export const events = new EventsApi();
