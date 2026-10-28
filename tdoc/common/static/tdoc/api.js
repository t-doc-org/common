// Copyright 2025 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import * as core from './core.js';
const {elmt, html, on, qs, qsa} = core;

const backend = new core.Stored('tdoc:api:backend', undefined, sessionStorage);
core.onHashParams(['api'], api => {
    backend.set(api);
    location.reload();
});

const [url, bes, domain] = (() => {
    if (tdoc.local) return ['/_api', '', ''];
    const loc = new URL(location), api=tdoc.api, domain = tdoc.domain;
    const b = backend.get();
    const suffix = b ? '-' + b : '';
    return [`${loc.protocol}//${api}${suffix}.${domain}`, suffix, domain];
})();

const _hasToken = `\
__Secure-tdoc-token${tdoc.local ? '' : '-' + new URL(url).hostname}=`;

function hasToken() {
    return document.cookie.split(';').some(c => c.trim().startsWith(_hasToken));
}

function removeToken() {
    const domainAttr = domain ? `domain=${domain}; ` : '';
    document.cookie = `\
${_hasToken}=; ${domainAttr}max-age=0; path=/; samesite=Strict; secure`;
}

async function httpCall(path, opts) {
    return await core.fetchJson(`${url}${path}`, {
        credentials: 'include',
        ...opts,
        headers: {
            'X-Csrf': '0',
            ...core.bearerAuthorization(opts?.token),
            ...opts?.headers,
        },
    });
}

class Rpc {
    constructor(conn, path, req) {
        this.conn = conn;
        this.rid = conn.rid;
        conn.rid = core.nextInt(conn.rid);
        this.req = req;
        req.$A = req.$Z = 1;
        req.$I = this.rid;
        req.$P = path;
        ({promise: this.resp, resolve: this.resolve, reject: this.reject} =
            Promise.withResolvers());
    }

    start() {
        this.conn.start(this);
        this.initiate();
    }

    initiate() {
        if (this.conn.send(this.req)) delete this.req;
    }

    onMessage(resp) {
        if (!this.conn.finish(this)) return;
        delete resp.$Z;
        const code = resp.$E;
        if (code == null) {
            this.resolve(resp);
        } else {
            this.reject(new Error(resp.$M ?? "Request failed",
                                  {cause: {code}}));
        }
    }

    abort(err) {
        if (!this.conn.finish(this)) return;
        this.reject(new Error(err));
        this.conn.send({$I: this.rid, $E: 408});  // REQUEST_TIMEOUT
    }
}

class Connection {
    static linger = 10000;

    constructor(chan, notBefore) {
        this.chan = chan;
        this.rpcs = new Map();
        this.rid = 0;
        this.connect(notBefore);  // BG
    }

    get connected() {
        return this.ws != null && this.ws.readyState === WebSocket.OPEN;
    }

    send(req) {
        if (!this.connected) return false;
        this.ws.send(JSON.stringify(req));
        return true;
    }

    start(rpc) {
        if (this.rpcs.size === 0) this.stopLinger();
        this.rpcs.set(rpc.rid, rpc);
    }

    finish(rpc) {
        if (!this.rpcs.delete(rpc.rid)) return false;
        if (this.rpcs.size === 0) this.startLinger();
        return true;
    }

    startLinger() {
        if (this.closing) return;
        this.linger = setTimeout(() => {
            delete this.linger;
            this.closing = true;
            this.chan.closed(this);
            if (this.ws != null) this.ws.close();
        }, this.constructor.linger);
    }

    stopLinger() {
        if (this.linger == null) return;
        clearTimeout(this.linger);
        delete this.linger;
    }

    closed(err = false) {
        this.closing = true;
        this.chan.closed(this, err);
        this.stopLinger();
    }

    async connect(notBefore) {
        if (notBefore != null) {  // Handle backoff
            const delay = notBefore - performance.now();
            if (delay > 0) await core.sleep(delay);
        }
        this.connectTime = performance.now();
        const ws = new WebSocket(`${url}/ws`);
        ws.binaryType = 'arraybuffer';
        on(ws).open(e => {
            this.ws = ws;
            for (const rpc of this.rpcs.values()) rpc.initiate();
        });
        on(ws).message(e => this.onMessage(e));
        on(ws).error(e => {
            this.closed(true);
        });
        on(ws).close(e => {
            this.closed();
            for (const rpc of this.rpcs.values()) rpc.abort("Disconnected");
        });
        if (this.rpcs.size === 0) this.startLinger();
    }

    onMessage(e) {
        const data = JSON.parse(e.data);
        const rid = data.$I;
        if (rid == null) return;
        const rpc = this.rpcs.get(rid);
        if (rpc == null) return;
        delete data.$I;
        rpc.onMessage(data);
    }
}

class Channel {
    static backoff = {min: 1000, max: 10000};
    static noBackoffConnDuration = 30000;

    async call(path, req) {
        const rpc = new Rpc(this.conn, path, req);
        try {
            rpc.start();
            return await rpc.resp;
        } finally {
            rpc.abort("Canceled");
        }
    }

    get conn() {
        let conn = this._conn;
        if (!conn) {
            conn = this._conn = new Connection(this, this.notBefore);
        }
        return conn;
    }

    closed(conn, err = false) {
        if (conn !== this._conn) return;
        delete this._conn;
        if (!err || performance.now() >
                    conn.connectTime + this.constructor.noBackoffConnDuration) {
            delete this.retries;
            delete this.notBefore;
        } else {
            if (this.retries == null) this.retries = 0;
            this.notBefore = performance.now()
                             + core.backoff(this.constructor.backoff,
                                            this.retries++);
        }
    }
}

const chan = new Channel();
const httpOnlyPaths = {
    '/events/sub': true,
};

export async function call(path, req = {}) {
    if (core.debug('ws') && !httpOnlyPaths[path]) {
        return await chan.call(path, req)
    }
    return await httpCall(path, {req});
}

if (core.debug('health')) {
    (async () => {
        for (let i = 0; i < 4; ++i) {
            console.log(await call('/health'));
            await core.sleep(200);
        }
    })();  // BG
}

class Auth extends EventTarget {
    constructor() {
        super();
        this.user = new core.StoredJson(`tdoc:api${bes}:user-info`);
        this.state = new core.StoredJson('tdoc:api:state', {}, sessionStorage);
        this.ready = this.init();
    }

    async init() {
        // All UI actions below are scheduled in the background.
        const state = this.state.get();
        const cnonce = state?.cnonce, settings = state?.modal === 'settings';
        this.state.update(v => { delete v.cnonce; delete v.modal; });

        // Handle the login flow.
        let [token, auth, error] =
            core.page.handleHashParams('token', 'auth', 'auth_error');
        let loginFlow = false;
        if (token && !hasToken()) {  // Initial login flow via token= URL
            loginFlow = true;
            try { await this.token(token); } catch (e) {}
            if (!hasToken()) error = "Token verification failure";
        } else if ((auth && auth === cnonce) || error) {  // Redirect login flow
            loginFlow = true;
            if (!hasToken() && !error) error = "Authentication failure";
        }

        // Get or refresh user information.
        if (hasToken()) {  // Logged in
            const done = (async () => {
                let user = this.user.get();
                try {
                    user = await call(`/user`);
                } catch (e) {
                    if (!user) user = {name: "(Unknown user)"};
                }
                this.set(user);
            })();  // BG
            // Wait for fresh info only if no cached info is available.
            if (!this.user.get()) await done;
        } else {  // Not logged in
            this.set(undefined);
        }

        // Display the result of the login flow.
        if (loginFlow) {
            let msg, kind;
            if (!error) {
                msg = settings ? "The login has been added successfully." :
                      `You have logged in successfully as "${this.name}".`;
                kind = 'success';
            } else {
                msg = settings ?
                      html`<b>The login could not be added:</b> ${error}` :
                      html`<b>Logging in has failed:</b> ${error}`;
                kind = 'danger';
            }
            if (settings) {
                this.showSettingsModal(msg, kind);
            } else {
                core.showAlert(msg, {kind});
            }
        }

        // Update the username shown in the user menu.
        core.domLoaded.then(() => {
            const el = qs(document, '.dropdown-user .dropdown-item.btn-user');
            el.classList.add('disabled');
            this.onChange(() => {
                qs(el, '.btn__text-container').replaceChildren(
                    this.name ?? "Not logged in");
            });
        });
    }

    set(user) {
        this.user.set(user);
        if (user) {
            core.htmlData.tdocUserPerms = (user.perms ?? []).join(' ');
            core.htmlData.tdocUserTags = (user.tags ?? []).join(' ');
        } else {
            delete core.htmlData.tdocUserPerms;
            delete core.htmlData.tdocUserTags;
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

    async token(token) {
        return await httpCall('/auth/token', {token});
    }

    async info() {
        return await call('/auth/info');
    }

    async update(req) {
        return await call('/auth/update', req);
    }

    async login(issuer) {
        const cnonce = await core.randomId(33);
        const resp = await call('/auth/login',
                                {issuer, href: location.href, cnonce});
        this.state.update(v => { v.cnonce = cnonce; });
        return resp.redirect;
    }

    async logout() {
        try { await httpCall('/auth/logout'); } catch (e) {}
        removeToken();
        this.user.set(undefined);
    }

    async showLoginModal() {
        let info, message, kind;
        try {
            info = await this.info();
        } catch (e) {
            info = {issuers: []};
            message = html`<b>Failed to get login info:</b> ${e.message}`;
            kind = 'danger';
        }
        const el = elmt`\
<div class="modal fade" tabindex="-1" aria-hidden="true"\
 aria-labelledby="tdoc-modal-title">\
<div class="modal-dialog"><div class="modal-content">\
<div class="modal-header">\
<h1 class="modal-title fs-5" id="tdoc-modal-title">Log in</h1>\
<button type="button" class="btn-close" data-bs-dismiss="modal"\
 aria-label="Close"></button>\
</div><div class="modal-body vstack gap-3">\
<form class="hstack gap-2 login hidden">\
<label for="tdoc-login-user" class="col-form-label">User:</label>\
<input type="text" class="form-control" id="tdoc-login-user" value="admin">\
<button type="submit" class="btn btn-primary text-nowrap login" disabled>\
Log in</button>\
</form>\
<div class="hstack flex-wrap gap-2 text-nowrap issuers"></div>\
</div><div class="modal-footer flex-nowrap">\
<div class="flex-fill text-${kind ?? 'success'} message">${message ?? ""}</div>\
<button type="button" class="btn btn-primary" data-bs-dismiss="modal">Close\
</button>\
</div></div></div>`;
        const loginForm = qs(el, 'form.login');
        loginForm.classList.toggle('hidden', !tdoc.local);
        const input = qs(loginForm, 'input#tdoc-login-user');
        const loginBtn = qs(loginForm, 'button.login');
        core.enable(input.value, loginBtn);
        this.addIssuerButtons(el, "Log in with", info.issuers);

        const modal = core.showModal(el);
        on(input).input(() => core.enable(input.value, loginBtn));
        on(loginForm).submit(async e => {
            e.preventDefault();
            if (!input.value) return;
            await core.toModalMessage(el, async () => {
                const redirect = await this.login(`local:${input.value}`);
                modal.hide();
                location.assign(redirect);
            });
        });
    }

    async showSettingsModal(message, kind = 'success') {
        let info, rauth;
        try {
            [info, rauth] = await Promise.all([
                this.info(),
                call(`/repo`, {info: true}),
            ]);
        } catch (e) {
            info = {issuers: [], logins: []};
            rauth = {enabled: false};
            if (message == null || (kind === 'success' || kind === 'warning')) {
                message = html`<b>Failed to get user info:</b> ${e.message}`;
                kind = 'danger';
            }
        }
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
 style="position: absolute; top: 0.5rem; right: 0.5rem;">Reset</button>\
</div></div></div>\
</div><div class="modal-footer flex-nowrap">\
<button type="button" class="btn btn-danger text-nowrap logout">\
<i class="tfa fa-right-from-bracket"></i> Log out\
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
            const updated = core.localIso(new Date(login.updated * 1e3));
            const row = logins.appendChild(elmt`\
<tr><td class="px-2">${login.name}</td><td class="px-2 text-nowrap">\
${login.issuer}</td><td class="px-2 text-nowrap">${updated}</td>\
<td><button type="button" class="btn btn-outline-danger">Remove</button></td>\
</tr>`);
            const btn = qs(row, 'button');
            if (info.logins.length < 2) core.enable(false, btn);
            on(btn).click(async () => {
                if (!confirm(`\
Are you sure you want to remove the login ${login.name}?`)) {
                    return;
                }
                await core.toModalMessage(el, async () => {
                    await this.update({
                        remove: {iss: login.iss, sub: login.sub},
                    });
                    row.remove();
                    const btns = qsa(logins, 'button');
                    if (btns.length < 2) core.enable(false, ...btns);
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

        const modal = core.showModal(el);
        this.state.update(v => { v.modal = 'settings'; });
        on(el)['hide.bs.modal'](() => {
            this.state.update(v => { delete v.modal; });
        });
        on(qs(repo, '.reset')).click(async e => {
            if (rauth.prefix !== null && !confirm(`\
Are you sure you want to reset the repository access password?

You will need to set the new password in your Mercurial configuration.`)) {
                return;
            }
            await core.toModalMessage(el, async () => {
                const resp = await call(`/repo`, {reset: true});
                user.textContent = resp.user;
                pass.textContent = resp.password;
                rauth.prefix = '';
                return `\
The password has been reset. Copy it now, as it won't be shown again.`;
            });
        });
        on(qs(el, '.logout')).click(async () => {
            await core.toModalMessage(el, async () => {
                await this.logout();
                modal.hide();
                await core.showAlert("You have logged out successfully.",
                                     {kind: 'warning', load: true});
                location.reload();
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
                await core.toModalMessage(modal, async () => {
                    location.assign(await this.login(issuer));
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
    return await call(`/editor`, req);
}

export async function poll(req) {
    return await call(`/poll`, req);
}

export async function solutions(show) {
    return await call(`/solutions`, {page: core.page.path, show});
}

export async function terminate(rc = 0) {
    return await httpCall(`/terminate`, {req: {rc}});
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
            const resp = await call(`/events/sub`, req);
            this.reportFailed(resp.failed);
        } catch (e) {}
    }

    async run() {
        this.running = true;
        try {
            for (let retries = 0;;) {
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
                await core.sleep(core.backoff({min: 1000, max: 10000},
                                              retries++));
            }
        } finally {
            this.running = false;
        }
    }

    async stream(req, connected) {
        this.abort = new AbortController();
        try {
            const resp = await fetch(`${url}/events/watch`, {
                method: 'POST', referrer: '',
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
                const buffer = new core.FifoBuffer();
                for (;;) {
                  const {value, done} = await reader.read();
                  if (value) {
                      let start = buffer.length;
                      buffer.write(value);
                      for (;;) {
                          const pos = buffer.findValue(10, start);
                          if (pos < 0) break;
                          const msg = core.dec.decode(buffer.read(pos + 1));
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
