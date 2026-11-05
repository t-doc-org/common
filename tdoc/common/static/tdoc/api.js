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

class Code {
    static #all = new Map();

    static of(v) {
        if (v instanceof Code) return v;
        const code = this.#all.get(v);
        return code != null ? code : UNKNOWN;
    }

    constructor(name, value) {
        this.name = name;
        this.value = value;
        this.constructor.#all.set(name, this);
        this.constructor.#all.set(value, this);
    }

    toString() { return this.name; }
}

export const OK = new Code('OK', 0);
export const CANCELLED = new Code('CANCELLED', 1);
export const UNKNOWN = new Code('UNKNOWN', 2);
export const INVALID_ARGUMENT = new Code('INVALID_ARGUMENT', 3);
export const DEADLINE_EXCEEDED = new Code('DEADLINE_EXCEEDED', 4);
export const NOT_FOUND = new Code('NOT_FOUND', 5);
export const ALREADY_EXISTS = new Code('ALREADY_EXISTS', 6);
export const PERMISSION_DENIED = new Code('PERMISSION_DENIED', 7);
export const RESOURCE_EXHAUSTED = new Code('RESOURCE_EXHAUSTED', 8);
export const FAILED_PRECONDITION = new Code('FAILED_PRECONDITION', 9);
export const ABORTED = new Code('ABORTED', 10);
export const OUT_OF_RANGE = new Code('OUT_OF_RANGE', 11);
export const UNIMPLEMENTED = new Code('UNIMPLEMENTED', 12);
export const INTERNAL = new Code('INTERNAL', 13);
export const UNAVAILABLE = new Code('UNAVAILABLE', 14);
export const DATA_LOSS = new Code('DATA_LOSS', 15);
export const UNAUTHENTICATED = new Code('UNAUTHENTICATED', 16);

export class RpcError extends Error {
    constructor(code, msg) {
        code = Code.of(code);
        super(msg ? `${code}: ${msg}` : `${code}`, {cause: {code}});
        this.code = code;
        this.msg = msg;
    }
}

class Rpc {
    constructor(conn, path, timeout) {
        this.conn = conn;
        this.rid = conn.rid;
        this.path = path;
        this.deadline = timeout == null ? null : performance.now() + timeout;
        this.q = [];
        this.qPoke = new core.CondVar();
        this.cancelled = new Promise((res, rej) => { this._cancel = rej; });
        this.cancelled.catch(e => undefined);  // Prevent logging
    }

    async start() {
        this.conn.start(this);
        if (this.deadline != null) {
            this.timer = setTimeout(() => this.abort(DEADLINE_EXCEEDED),
                                    this.deadline - performance.now());
        }
        await Promise.race([this.conn.connected, this.cancelled]);
    }

    finish() {
        if (this.timer != null) clearTimeout(this.timer);
        this.conn.finish(this);
    }

    cancel(code, msg) {
        if (this.aborted) return false;
        this.receiveClosed = this.sendClosed = this.aborted = true;
        this.closeQueue([code, msg]);
        this._cancel(new RpcError(code, msg));
        return true;
    }

    received(resp) {
        const code = resp.$E;
        if (code != null) {
            this.cancel(Code.of(code), resp.$M);
            return;
        }
        if (this.receiveClosed) return;
        const last = resp.$Z;
        if (last == null) {
            this.enqueue(resp);
            return;
        }
        this.receiveClosed = true;
        if (last !== 0) {
            delete resp.$Z;
            this.enqueue(resp);
        }
        this.closeQueue();
    }

    enqueue(resp) {
        if (this.qClosed) return;
        this.q.push(resp);
        this.qPoke.notify();
    }

    closeQueue(err) {
        if (this.qClosed) return;
        this.qClosed = err ?? true;
        if (err != null) delete this.q;
        this.qPoke.notify();
    }

    get resps() {
        let resps = this._resps;
        if (resps == null) resps = this._resps = this.iterResps();
        return resps;
    }

    async *iterResps() {
        const cond = () => this.q == null || this.q.length > 0 || this.qClosed;
        for (;;) {
            await this.qPoke.wait(cond);
            const q = this.q, closed = this.qClosed;
            if (q == null) throw new RpcError(...closed);
            this.q = [];
            for (const resp of q) {
                yield resp;
                if (this.q == null) throw new RpcError(...this.qClosed);
            }
            if (closed) break;
        }
    }

    send(req, final = false) {
        if (this.sendClosed) throw new Error("Send on closed stream");
        req.$I = this.rid;
        if (!this.initiated) {
            req.$A = 1;
            req.$P = this.path;
            if (this.deadline != null) {
                const timeout = this.deadline - performance.now();
                if (timeout <= 0) throw new RpcError(DEADLINE_EXCEEDED);
                req.$T = Math.ceil(timeout);
            }
        }
        if (final) req.$Z = 1;
        if (!this.conn.send(req)) {
            this.sendClosed = true;
            throw new Error("Disconnected");
        }
        if (!this.initiated) this.initiated = true;
        if (final) this.sendClosed = true;
    }

    closeSend() {
        if (this.sendClosed) return;
        this.sendClosed = true;
        if (!this.conn.send({$I: this.rid, $Z: 0})) {
            throw new Error("Disconnected");
        }
    }

    abort(code, msg) {
        if (!this.cancel(code, msg)) return;
        if (!this.initiated) return;
        this.conn.send({$I: this.rid, $E: CANCELLED.value});
    }
}

class Connection {
    #rid = 0;
    rpcs = new Map();

    constructor(chan, notBefore, lingerDelay) {
        this.chan = chan;
        this.lingerDelay = lingerDelay;
        this.connect(notBefore);  // BG
    }

    get rid() {
        const rid = this.#rid;
        this.#rid = core.nextInt(rid);
        return rid;
    }

    get isConnected() {
        return this.ws != null && this.ws.readyState === WebSocket.OPEN;
    }

    send(req) {
        if (!this.isConnected) return false;
        this.ws.send(JSON.stringify(req));
        return true;
    }

    start(rpc) {
        if (this.rpcs.size === 0) this.stopLinger();
        this.rpcs.set(rpc.rid, rpc);
    }

    finish(rpc) {
        if (!this.rpcs.delete(rpc.rid)) return;
        if (this.rpcs.size === 0) this.startLinger();
    }

    startLinger() {
        if (this.closing) return;
        this.linger = setTimeout(() => {
            delete this.linger;
            this.closing = true;
            this.chan.closed(this);
            if (this.ws != null) this.ws.close();
        }, this.lingerDelay);
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
        let resolve, reject;
        ({promise: this.connected, resolve, reject} = Promise.withResolvers());
        if (notBefore != null) {  // Handle backoff
            const delay = notBefore - performance.now();
            if (delay > 0) await core.sleep(delay);
        }
        this.connectTime = performance.now();
        const ws = new WebSocket(`${url}/ws`);
        ws.binaryType = 'arraybuffer';
        on(ws).open(e => {
            this.ws = ws;
            resolve();
        });
        on(ws).message(e => this.onMessage(e));
        on(ws).error(e => {
            this.closed(true);
            reject(new Error("Connection failed"));
        });
        on(ws).close(e => {
            this.closed();
            for (const rpc of this.rpcs.values()) {
                rpc.abort(UNAVAILABLE, "Disconnected");
            }
        });
        if (this.rpcs.size === 0) this.startLinger();
    }

    onMessage(e) {
        const resp = JSON.parse(e.data);
        const rid = resp.$I;
        if (rid == null) return;
        const rpc = this.rpcs.get(rid);
        if (rpc == null) return;
        delete resp.$I;
        rpc.received(resp);
    }
}

class Channel {
    connLingerDelay = 10000;
    backoff = {min: 1000, max: 10000};
    noBackoffConnDuration = 30000;

    async stream({path, timeout}, fn) {
        const rpc = new Rpc(this.conn, path, timeout);
        try {
            await rpc.start();
            const res = await fn(rpc);
            rpc.closeSend();
            return res;
        } catch (e) {
            rpc.abort(INTERNAL, "Exception");
            throw e;
        } finally {
            rpc.finish();
        }
    }

    async call(opts, req) {
        return await this.stream(opts, async rpc => {
            rpc.send(req, true);
            let res;
            for await (const resp of rpc.resps) {
                if (res != null) throw new Error("Received multiple responses");
                res = resp;
            }
            return res;
        });
    }

    get conn() {
        let conn = this._conn;
        if (!conn) {
            conn = this._conn = new Connection(this, this.notBefore,
                                               this.connLingerDelay);
        }
        return conn;
    }

    closed(conn, err = false) {
        if (conn !== this._conn) return;
        delete this._conn;
        if (!err || performance.now() >
                    conn.connectTime + this.noBackoffConnDuration) {
            delete this.retries;
            delete this.notBefore;
        } else {
            if (this.retries == null) this.retries = 0;
            this.notBefore = performance.now()
                             + core.backoff(this.backoff, this.retries++);
        }
    }
}

const chan = new Channel();
const httpOnlyPaths = {
    '/events/sub': true,
};

export async function call(path, req = {}) {
    if (core.debug('ws') && !httpOnlyPaths[path]) {
        return await chan.call({path, timeout: 15000}, req)
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
if (core.debug('stream')) {
    (async () => {
        try {
            await core.sleep(2000);
            await chan.stream({path: '/stream'}, async rpc => {
                const receiver = (async () => {
                    for await (const resp of rpc.resps) {
                        console.log(resp);
                    }
                })();
                receiver.catch(e => undefined);  // Prevent logging
                for (let i = 0; i < 4; ++i) {
                    if (i === 2) {
                        rpc.send({i, err: NOT_FOUND.value, msg: "Some failure"});
                        // rpc.send({i, cancel: "Some message"});
                        // throw new RpcError(INVALID_ARGUMENT, "Some exception");
                    } else {
                        rpc.send({i});
                    }
                    await Promise.race([core.sleep(200), rpc.cancelled]);
                }
                rpc.closeSend();
                await receiver;
            });
            console.log(`Stream terminated successfully`);
        } catch (e) {
            console.log(`Stream failed: ${e}`);
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

class EventsApi2 {
    watches = new Map();

    async sub({add, remove}) {
        remove ??= [];
        add ??= [];
        for (const w of remove) this.watches.delete(w.id);
        for (const w of add) this.watches.set(w.id, w);
        if (!this.running) {
            if (this.watches.size === 0) return;
            this.run();  // BG
            return;
        }
        const rpc = this.rpc;
        if (rpc == null) return;  // No active RPC
        const req = {};
        if (remove.length > 0) {
            req.remove = [];
            for (const w of remove) req.remove.push(w.id);
        }
        if (add.length > 0) {
            req.add = [];
            for (const w of add) req.add.push({wid: w.id, req: w.req});
        }
        try { rpc.send(req); } catch (e) {}
    }

    async run() {
        this.running = true;
        try {
            for (let retries = 0;;) {
                const start = performance.now();
                try {
                    await this.watch();
                } catch (e) {
                } finally {
                    delete this.rpc;
                }
                if (performance.now() - start > 30000) {
                    retries = 0;
                } else {
                    await core.sleep(core.backoff({min: 1000, max: 10000},
                                                  retries++));
                }
            }
        } finally {
            this.running = false;
        }
    }

    async watch() {
        await chan.stream({path: '/events/watch'}, async rpc => {
            const req = {};
            if (this.watches.size > 0) {
                const add = req.add = [];
                for (const w of this.watches.values()) {
                    add.push({wid: w.id, req: w.req});
                }
            }
            rpc.send(req);
            this.rpc = rpc;
            for await (const resp of rpc.resps) {
                if (resp.data != null) {
                    await this.onEvent(resp);
                } else if (resp.failed != null) {
                    this.reportFailed(resp.failed)
                }
            }
        });
    }

    async onEvent(resp) {
        const watch = this.watches.get(resp.wid);
        if (watch === undefined) return;
        try {
            await watch.onEvent(resp.data);
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

export const events = core.debug('ws') ? new EventsApi2() : new EventsApi();
