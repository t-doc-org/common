// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

// UTF-8 text encoder and decoder.
export const enc = new TextEncoder();
export const dec = new TextDecoder();

// The dataset of the <html> tag.
export const htmlData = document.documentElement.dataset;

// Information about the page.
export const page = {
    origin: tdoc.local ? '' : location.origin,
    path: location.pathname
          + (location.pathname.endsWith('/') ? 'index.html' : ''),

    get hashParams() {
        if (!location.hash.startsWith('#?')) return;
        return new URLSearchParams(location.hash.slice(1));
    },

    set hashParams(params) {
        let hash = params.toString();
        if (hash) hash = `#?${hash}`;
        if (hash === location.hash) return;
        history.replaceState(
            null, '',
            location.origin + location.pathname + location.search + hash);
    }
};

function handleHashParams(names, fn) {
    const params = page.hashParams
    if (!params) return;
    let found = false;
    const vs = names.map(name => {
        const v = params.get(name);
        if (v !== null) {
            found = true;
            params.delete(name);
        }
        return v;
    });
    if (found) {
        page.hashParams = params;
        return fn(...vs);
    }
}

// Register a handler for the hash parameters with the given names. Calls the
// handler immediately if any of the hash parameters are currently present, and
// returns the result of the handler. Also call the handler if the page hash
// changes and any of the parameters are present.
export function onHashParams(names, fn) {
    const res = handleHashParams(names, fn);
    on(window).hashchange(() => handleHashParams(names, fn));
    return res;
}

// Resolves when the DOM content has loaded and deferred scripts have executed.
export const domLoaded = new Promise(resolve => {
    if (document.readyState !== 'loading') {
        resolve();
    } else {
        document.addEventListener('DOMContentLoaded', resolve);
    }
});

// Return true iff the argument is an object and not an array.
export function isObject(v) {
    return v !== null && typeof v === 'object' && !Array.isArray(v);
}

// Return true iff the argument is a plain Object.
export function isPlainObject(v) {
    if (typeof v !== 'object') return false;
    const p = Object.getPrototypeOf(v);
    return p === null || p.isPrototypeOf(Object);
}

// Escape text for inclusion in HTML.
export function escape(text) {
    return text.replace(/[&<>"']/g, m => `&#${m.charCodeAt(0)};`);
}

// Create a text node.
export function text(value) {
    return document.createTextNode(value);
}

// Perform string interpolation of an HTML snippet.
function interpolateHtml(html, values) {
    if (html.length === 1 && (values[0] === undefined || values[0] === '')) {
        return html[0];
    }
    const parts = [];
    for (const [i, s] of html.entries()) {
        parts.push(s);
        const v = values[i];
        if (v === undefined || v === '') {
            continue;
        } else if (v === null) {
            parts.push('null');
        } else if (v instanceof Element) {
            parts.push(v.outerHTML);
        } else if (v instanceof DocumentFragment) {
            const el = document.createElement('template');
            el.content.append(v);
            parts.push(el.innerHTML);
        } else {
            parts.push(escape(v.toString()));
        }
    }
    return parts.join('');
}

// Create an DocumentFragment node.
export function html(tmpl, ...values) {
    const el = document.createElement('template');
    el.innerHTML = interpolateHtml(tmpl, values);
    return el.content;
}

// Create an Element node.
export function elmt(tmpl, ...values) {
    return html(tmpl, ...values).firstElementChild;
}

// An Error with an HTML-formatted message.
export class HtmlError extends Error {
    static of(err) {
        if (err instanceof HtmlError) return err;
        if (err instanceof Error) {
            return htmle`<strong>${err.name}:</strong> ${err.message}`;
        }
        return htmle`<strong>Error:</strong> ${err}`;
    }

    constructor(html, options) {
        super(html.textContent, options);
        this.html = html;
    }

    as(kind) {
        this.kind = kind;
        return this;
    }
}

// Create an HtmlError containing, well, HTML.
export function htmle(tmpl, ...values) {
    return new HtmlError(html(tmpl, ...values));
}

// Display alerts for unhandled exceptions in promises.
addEventListener('unhandledrejection', e => { showAlert(e.reason); });

// Query a single matching element below an element.
export function qs(el, selector) {
    return el?.querySelector?.(selector);
}

const emptyNodeList = document.createElement('template').querySelectorAll('p');

// Query all matching elements below an element.
export function qsa(el, selector) {
    if (el === undefined || el === null) return emptyNodeList;
    return el.querySelectorAll(selector);
}

// A mutex for asynchronous code.
export class Mutex {
    async acquire() {
        while (this.p !== undefined) await this.p;
        ({promise: this.p, resolve: this.r} = Promise.withResolvers());
    }

    release() {
        const resolve = this.r;
        delete this.p, this.r;
        resolve();
    }

    async locked(fn) {
        await this.acquire();
        try {
            return await fn();
        } finally {
            this.release();
        }
    }
}

// Pending accesses to asyncGet attributes.
const pendingAsyncGet = new Set();

function pendingAsyncGetFor(ns) {
    const pending = {};
    for (const [n, c, a] of pendingAsyncGet.keys()) {
        if (n !== ns) continue;
        let as = pending[c];
        if (as === undefined) as = pending[c] = [];
        as.push(a);
    }
    return pending;
}

// Return a proxy that makes all attribute accesses asynchronous, where the
// attribute must first be set before accesses complete.
export function asyncGet(obj, {
    ns, container, callables = false, alert = true,
} = {}) {
    const resolves = {};
    return new Proxy(obj, {
        get(obj, prop, recv) {
            if (prop === 'then') return;  // Make the proxy non-thenable
            const v = obj[prop];
            if (v !== undefined) return v;
            if (typeof prop === 'symbol') return;
            const {promise, resolve} = Promise.withResolvers();
            const value = callables ? asyncCall(promise) : promise;
            obj[prop] = value;
            resolves[prop] = resolve;
            if (ns !== undefined) {
                const fqn = [ns, container, prop];
                pendingAsyncGet.add(fqn);
                promise.then(() => { pendingAsyncGet.delete(fqn); });
            }
            return value;
        },

        set(obj, prop, value, recv) {
            try {
                if (prop === 'then') {
                    throw htmle`Invalid property name: <code>${prop}</code>`;
                }
                const resolve = resolves[prop];
                if (resolve !== undefined) {
                    delete resolves[prop];
                    resolve(value);
                } else if (obj[prop] !== undefined) {
                    throw ns === undefined ?
                        htmle`Duplicate definition: <code>${prop}</code>` :
                        htmle`\
<code>{${ns}}</code> Duplicate <code>${container}</code> definition: \
<code>${prop}</code>`;
                } else {
                    obj[prop] = value;
                }
            } catch (e) {
                if (!alert) throw e;
                console.error(e);
                showAlert(e);
            }
            return true;
        },
    });
}

// Return a function that awaits the given promise, then calls the function to
// which it resolves.
function asyncCall(pfn) {
    return function(...args) {
        return pfn.then(fn => fn.apply(this, args));
    };
}

function splitContainerName(name) {
    if (name === undefined) return [];
    const parts = name.split('.');
    return [parts[0], parts.slice(1).join('.')];
}

// Merge attribute sets, with later sets overriding earlier ones.
export async function mergeAttrs(mergeTo, attrs, ...as) {
    const res = {};
    const mergeToRes = async (...as) => {
        for (let a of as) {
            if (a instanceof Promise) a = await a;
            if (attrs !== undefined && typeof a === 'string') {
                a = await attrs[a];
            }
            if (a === undefined) continue;
            if (Array.isArray(a)) {
                await mergeToRes(...a);
            } else {
                mergeTo(res, a);
            }
        }
    };
    await mergeToRes(...as);
    return res;
}

// Enable or disable one or more elements.
export function enable(value, ...els) {
    for (const el of els) el.disabled = !value;
}

const onHandler = {
    get(obj, prop, recv) {
        return (handler, opts) => {
            obj.addEventListener(prop, handler, opts);
            return recv;
        }
    }
};

// Return a proxy object whose methods set event handlers.
export function on(node) { return new Proxy(node, onHandler); }

const messageSources = new WeakMap();
on(window).message(e => messageSources.get(e.source)?.(e));

// Register a handler for window messages from a given source. At most one
// handler can be registered per source.
export function onMessage(source, fn) {
    messageSources.set(source, fn);
}

// Return true iff the given element is within the root viewport.
//
// WARNING: This function may force a reflow, and may therefore be expensive.
export function isVisible(el) {
    const rect = el.getBoundingClientRect();
    return rect.top >= 0 && rect.left >= 0 &&
           rect.bottom <= document.documentElement.clientHeight &&
           rect.right <= document.documentElement.clientWidth;
}

// Add a tooltip instance to an element.
export function addTooltip(el, opts) {
    return new bootstrap.Tooltip(el, {
        delay: {show: 500, hide: 100},
        trigger: 'hover',
        ...opts,
    });
}

// Show an alert at the top of the article.
export function showAlert(message, kind = 'success') {
    if (message instanceof Error) {
        const e = HtmlError.of(message);
        [message, kind] = [e.html, e.kind ?? 'danger'];
    }
    let el = qs(document, '.tdoc-alerts');
    if (!el) {
        el = qs(document, '.bd-header-article').appendChild(elmt`\
<div class="tdoc-alerts"></div>`);
    }
    el.appendChild(elmt`\
<div class="alert alert-${kind} alert-dismissible" role="alert">\
<div>${message}</div>\
<button type="button" class="btn-close" data-bs-dismiss="alert"\
 aria-label="Close"></button>\
`);
}

// Show a modal dialog.
export function showModal(el) {
    const modal = new bootstrap.Modal(el);
    on(el)['hide.bs.modal'](() => document.activeElement.blur());
    on(el)['hidden.bs.modal'](() => {
        modal.dispose();
        el.remove();
    });
    modal.show();
    return modal;
}

// Call the given function, and set its return value or any thrown exceptions as
// text content of the .message element.
export async function toModalMessage(modal, fn) {
    let msg, err = false;
    try {
        msg = await fn();
    } catch (e) {
        msg = e.message;
        err = true;
    }
    const el = qs(modal, '.message');
    el.textContent = msg ?? "";
    el.classList.toggle('text-danger', err);
    el.classList.toggle('text-success', !err);
}

// Return a <span> containing inline math. The element must be typeset after
// being added to the DOM.
// TODO: Typeset automatically using a web component
export function inlineMath(value) {
    const [start, end] = MathJax.tex?.inlineMath ?? ['\\(', '\\)'];
    return elmt`\
<span class="math notranslate nohighlight">${start}${value}${end}</span>`;
}

// Return a <div> containing display math. The element must be typeset after
// being added to the DOM.
// TODO: Typeset automatically using a web component
export function displayMath(value) {
    // The formatting of the content corresponds to what spinx.ext.mathjax does.
    const parts = [];
    for (const p of value.split('\n\n')) {
        if (p.trim()) parts.push(p);
    }
    const out = [];
    if (parts.length > 1) out.push(' \\begin{align}\\begin{aligned}');
    for (const [i, p] of parts.entries()) {
        const nl = p.includes('\\\\');
        if (nl) out.push('\\begin{split}');
        out.push(p);
        if (nl) out.push('\\end{split}');
        if (i < parts.length - 1) out.push('\\\\');
    }
    if (parts.length > 1) out.push('\\end{aligned}\\end{align} ');
    const [start, end] = MathJax.tex?.displayMath ?? ['\\[', '\\]'];
    return elmt`\
<div class="math notranslate nohighlight">${start}${out.join('')}${end}</div>`;
}

let typeset = globalThis.MathJax?.startup?.promise;
if (!typeset && globalThis.MathJax) {
    if (!MathJax.startup) MathJax.startup = {};
    typeset = new Promise(resolve => {
        MathJax.startup.pageReady = () => {
            return MathJax.startup.defaultPageReady().then(resolve);
        }
    });
}
export const mathJaxReady = typeset;

// Typeset the math contained in one or more elements.
export function typesetMath(...args) {
    typeset = typeset.then(() =>  MathJax.typesetPromise(args))
        .catch(e => console.error(`Math typesetting failed: ${e}`));
    return typeset;
}

// Focus an element if it is visible and no other element has the focus.
//
// WARNING: This function may force a reflow, and may therefore be expensive.
export function focusIfVisible(el) {
    const active = document.activeElement;
    if ((!active || active.tagName === 'BODY') && isVisible(el)) el.focus();
}

// Return the greatest common divisor of two natural numbers.
// TODO(0.77): Remove in favor of math.gcd()
export function gcd(a, b) {
    while (b != 0) {
        [a, b] = [b, a % b]
    }
    return a;
}

// Generate a random integer within an inclusive range.
export function randomInt(min, max) {
    return Math.floor(min + Math.random() * (max - min + 1));
}

// Convert a number to a given radix, optionally left-padding with zeroes.
export function toRadix(value, radix, length) {
    let s = value.toString(radix);
    if (length) s = s.padStart(length, '0');
    return s;
}

// Convert an rgb() or rgba() color to its hex representation.
export function rgb2hex(value) {
    const m = value.match(
        /^rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*(\d+\.?\d*))?\)$/);
    if (!m) return;
    let res = m.slice(1, 4).map(v => toRadix(parseFloat(v), 16, 2)).join('');
    if (m[4] !== undefined) {
        res += toRadix(Math.round(parseFloat(m[4]) * 255), 16, 2);
    }
    return `#${res}`;
}

const cMinus = '-'.charCodeAt(0), cPlus = '+'.charCodeAt(0);
const c0 = '0'.charCodeAt(0), cA = 'A'.charCodeAt(0);

// Convert a string to an integer. Returns undefined if the string is not a
// valid integer.
export function strToInt(s, radix = 10) {
    if (!(2 <= radix && radix <= 36)) return;
    s = s.toUpperCase();
    let i = 0, sign = 1, res = 0, valid = false;
    while (i < s.length) {
        const c = s.charCodeAt(i++);
        if (i === 1) {
            if (c === cPlus) {
                continue;
            } else if (c === cMinus) {
                sign = -1;
                continue;
            }
        }
        let d = 36;
        if (c0 <= c && c < c0 + 10) {
            d = c - c0;
        } else if (cA <= c && c < cA + 26) {
            d = 10 + c - cA;
        }
        if (d >= radix) return;
        res = res * radix + d;
        valid = true;
    }
    if (!valid) return;
    return sign * res;
}

// Return the date of a Date in local time in ISO format.
export function localIso(d) {
    return `\
${d.getFullYear().toString().padStart(4, '0')}\
-${(d.getMonth() + 1).toString().padStart(2, '0')}\
-${d.getDate().toString().padStart(2, '0')}`;
}

// Return true iff the given URL is in the same origin as the page.
export function sameOrigin(url) {
    return new URL(url).origin === location.origin;
}

// Create a data: URL containing the given data.
export function dataUrl(type, data) {
    return `data:${type},${encodeURIComponent(data)}`;
}

// Convert binary data to base64.
export function toBase64(data) {
    return new Promise((resolve, reject) => {
        const reader = Object.assign(new FileReader(), {
            onload: () => {
                const res = reader.result;
                resolve(res.substring(res.indexOf(',') + 1));
            },
            onerror: () => reject(reader.error),
        });
        reader.readAsDataURL(new File([data], '',
                             {type: "application/octet-stream"}));
    });
}

// Convert base64 data to binary.
export async function fromBase64(data) {
    try {
        const res = await fetch(`data:application/octet-stream;base64,${data}`);
        return new Uint8Array(await res.arrayBuffer());
    } catch (e) {
        throw new Error("Invalid base64 input");
    }
}

// Perform a fetch on a JSON API.
export async function fetchJson(url, opts) {
    const method = opts?.method ?? 'POST';
    const hasBody = method !== 'GET';
    const resp = await fetch(url, {
        method, cache: 'no-store', referrer: '',
        body: hasBody ? JSON.stringify(opts?.req ?? {}) : undefined,
        ...opts,
        headers: {
            'Cache-Control': 'no-store',
            ...hasBody ? {'Content-Type': 'application/json'} : undefined,
            ...opts?.headers,
        },
    });
    if (!resp.ok) {
        let msg = await resp.text();
        if (!msg) msg = `${resp.status} ${resp.statusText}`;
        throw new Error(msg, {cause: {status: resp.status}});
    }
    return await resp.json();
}

// Return an Authorization header with the given bearer token.
export function bearerAuthorization(token) {
    return token ? {'Authorization': `Bearer ${token}`} : {};
}

// Return a promise that resolves after the given number of milliseconds.
export function sleep(ms) {
    return new Promise(res => setTimeout(res, ms));
}

// Return a promise that gets rejected after the given number of milliseconds.
export function timeout(ms) {
    const p = new Promise(
        ms !== undefined && ms !== null ?
        ((res, rej) => setTimeout(() => rej(new Error("Timeout")), ms)) :
        (() => undefined));
    p.catch(e => undefined);  // Prevent logging
    return p;
}

// Canonicalize a document path, or the current document if missing.
export function docPath(path) {
    if (path === undefined) path = location.pathname;
    if (path.endsWith('.html')) path = path.slice(0, -5);
    if (path.endsWith('/')) path += 'index';
    return path;
}

// A FIFO buffer of bytes.
export class FifoBuffer {
    constructor(size = 256) {
        this.data = new Uint8Array(size);
        this.begin = this.end = 0;
    }

    // Return the number of bytes in the buffer.
    get length() { return this.end - this.begin; }

    // Read data, but leave it in the buffer.
    peek(begin, end) {
        const len = this.length;
        if (begin > len) begin = len;
        if (end > len) end = len;
        return this.data.slice(this.begin + begin, this.begin + end);
    }

    // Read data from the head of the buffer.
    read(size) {
        const len = this.length;
        if (size > len) size = len;
        const data = this.data.slice(this.begin, this.begin + size);
        this.begin += size;
        if (this.begin === this.end) this.begin = this.end = 0;
        return data;
    }

    // Drop bytes from the head of the buffer.
    drop(size) {
        this.begin += size;
        if (this.begin > this.end) this.begin = this.end = 0;
    }

    // Write data to the tail of the buffer.
    write(data) {
        if (this.length + data.length > this.data.length) {
            const newData = new Uint8Array(Math.max(
                2 * this.data.length, this.data.length + data.length));
            newData.set(this.data.subarray(this.begin, this.end));
            this.data = newData;
            this.end -= this.begin;
            this.begin = 0;
        } else if (this.end + data.length > this.data.length) {
            this.data.copyWithin(0, this.begin, this.end);
            this.end -= this.begin;
            this.begin = 0;
        }
        this.data.set(data, this.end);
        this.end += data.length;
    }

    // Find a value within the buffer.
    findValue(value, pos) {
        if (this.begin + pos + 1 > this.end) return -1;
        const index = this.data.subarray(this.begin + pos, this.end)
                               .indexOf(value);
        return index >= 0 ? pos + index : -1;
    }

    // Find data within the buffer.
    findData(data, pos) {
        if (this.begin + pos + data.length > this.end) return -1;
        const index = this.data.subarray(this.begin + pos, this.end).findIndex(
            (_, i, arr) => {
                if (i + data.length > arr.length) return false;
                for (let j = 0; j < data.length; ++j) {
                    if (arr.at(i + j) !== data.at(j)) return false;
                }
                return true;
            });
        return index >= 0 ? pos + index : -1;
    }

    toString() {
        return this.data.subarray(this.begin, this.end).toString();
    }
}

// An async implementation of the subset of Storage used by AsyncStored that
// manages the data in localStorage at the domain level, with the data shared
// across all sites.
class DomainStorage {
    static async create() {
        if (!(tdoc.local || tdoc.domain_storage.origin)) return localStorage;
        const {port1, port2} = new MessageChannel();
        const origin = tdoc.local ? location.origin
                                  : tdoc.domain_storage.origin;
        await domLoaded;
        const iframe = document.body.appendChild(elmt`\
<iframe class="tdoc-domain-storage" src="${origin}/_static/tdoc/domain.html">\
</iframe>\
`);
        on(iframe).load(() => {
            iframe.contentWindow.postMessage('init', origin, [port2]);
        });
        return new this(port1);
    }

    constructor(port) {
        this.port = port;
        this.id = 0;
        this.msgs = new Map();
        on(port).message(e => this.onMessage(e));
        port.start();
    }

    async getItem(key) { return (await this.transaction({get: key})).value; }
    async setItem(key, value) { await this.transaction({set: key, value}); }
    async removeItem(key) { await this.transaction({remove: key}); }

    async transaction(msg) {
        msg.id = ++this.id;
        const {promise, resolve, reject} = Promise.withResolvers();
        this.msgs.set(msg.id, {resolve, reject});
        this.port.postMessage(msg);
        return await promise;
    }

    onMessage(e) {
        const data = e.data;
        const {resolve, reject} = this.msgs.get(data.id);
        this.msgs.delete(data.id);
        delete data.id;
        if (data.err !== undefined) {
            reject(data.err);
        } else {
            resolve(data);
        }
    }
}

const domainStorage = await DomainStorage.create();

// A base class for stored values.
class StoredBase {
    constructor(key, def, storage) {
        this.key = key;
        this._value = def;
        this._storage = storage;
    }

    get() { return this._value; }

    encode(v) { return v; }
    decode(v) { return v; }
}

// A value that is stored as a string in local or session storage.
export class Stored extends StoredBase {
    static create(key, def, storage = localStorage) {
        const self = new this(key, def, storage);
        const v = self._storage.getItem(self.key);
        if (v !== null) {
            try { self._value = self.decode(v); } catch (e) {}
        }
        return self;
    }

    set(v) { this._value = v; this.store(); }

    update(fn) {
        fn(this._value);
        this.store();
        return this._value;
    }

    store() {
        if (this._value !== undefined && this._value !== null) {
            this._storage.setItem(this.key, this.encode(this._value));
        } else {
            this._storage.removeItem(this.key);
        }
    }
}

// A value that is stored as a string in an async storage.
export class AsyncStored extends StoredBase {
    static async create(key, def, storage = domainStorage) {
        const self = new this(key, def, storage);
        const v = await self._storage.getItem(self.key);
        if (v !== null) {
            try { self._value = self.decode(v); } catch (e) {}
        }
        return self;
    }

    async set(v) { this._value = v; await this.store(); }

    async update(fn) {
        fn(this._value);
        await this.store();
        return this._value;
    }

    async store() {
        if (this._value !== undefined && this._value !== null) {
            await this._storage.setItem(this.key, this.encode(this._value));
        } else {
            await this._storage.removeItem(this.key);
        }
    }
}

const JsonMixin = cls => class extends cls {
    encode(v) { return JSON.stringify(v); }
    decode(v) { return JSON.parse(v); }
};

// A value that is stored as JSON.
export const StoredJson = JsonMixin(Stored);
export const AsyncStoredJson = JsonMixin(AsyncStored);

// Manage an immutable, globally-unique client ID in domain storage.
const clientIdStore = await AsyncStored.create('tdoc:clientId');
if (clientIdStore.get() === undefined) {
    clientIdStore.set(await toBase64(
        crypto.getRandomValues(new Uint8Array(33))));  // Background
}
export const clientId = clientIdStore.get();

// Return an exponential backoff delay.
export function backoff(min, max, retries) {
    let delay = min * 1.3 ** retries;
    if (delay > max) delay = max;
    delay -= delay * 0.4 * Math.random();
    return delay >= min ? delay : min;
}

// Rate-limit function calls. Scheduled functions must be droppable, i.e. all
// calls in a sequence except the last one can be dropped.
export class RateLimited {
    constructor(interval) { this.interval = interval; }

    // Schedule a function. It will be called after "interval" at the latest.
    // Scheduling a new function while the previous one hasn't been run yet
    // replaces the previous one.
    schedule(fn) {
        const active = this.fn;
        this.fn = fn;
        if (!active) setTimeout(() => this.flush(), this.interval);
    }

    // Call the current scheduled function immediately.
    flush() {
        const fn = this.fn;
        delete this.fn;
        if (fn) fn();
    }
}

export class TdocElement extends HTMLElement {
    static #handlers = {};

    static async extend(name, handler) {
        if (!name.startsWith('tdoc-')) {
            throw htmle`\
<code>TdocElement.extend()</code> can only extend <code>&lt;tdoc-*&gt;</code> \
elements.`
        }
        await customElements.whenDefined(name);
        let handlers = TdocElement.#handlers[name];
        if (handlers === undefined) handlers = TdocElement.#handlers[name] = [];
        handlers.push(handler);

        // Call the handler on elements that are already ready.
        const fn = handler.ready
        if (fn !== undefined) {
            const els = Array.prototype.filter.call(qsa(document, name),
                                                    el => el.#ready);
            for (const el of els) {
                try {
                    await fn(el);
                } catch (e) {
                    console.error(e);
                }
            }
        }
    }

    constructor() {
        super();
        this.ready = new Promise(resolve => { this.#readyResolve = resolve; });
    }

    #ready = false;
    #readyResolve;

    async _ready() {
        const handlers = Array.from(
            TdocElement.#handlers[this.localName] ?? []);
        this.#ready = true;
        this.#readyResolve(this);
        for (const handler of handlers) {
            const fn = handler.ready;
            if (fn !== undefined) {
                try {
                    await fn(this);
                } catch (e) {
                    console.error(e);
                }
            }
        }
    }

    async connectedCallback() { await this._ready(); }
}

// Query matching <tdoc-*> elements from a node, then yield them asynchronously
// as they become ready.
export async function* qsaReady(node, selector) {
    const promises = new Map();
    await domLoaded;
    for (const el of qsa(node, selector)) {
        const name = el.localName;
        if (name.startsWith('tdoc-')) {
            await customElements.whenDefined(name);
            promises.set(el, el.ready);
        } else {
            yield el;
        }
    }
    while (promises.size > 0) {
        const el = await Promise.race(promises.values());
        promises.delete(el);
        yield el;
    }
}

export const dyn = {
    // The renderers for dyn elements.
    render: asyncGet({}, {ns: 'dyn', container: 'render'}),

    // A symbol to set on renderers to specify a rendering timeout.
    timeout: Symbol('dyn.timeout'),
};

export class DynElement extends TdocElement {
    async connectedCallback() {
        try {
            let render = await dyn.render[this.type];
            const ms = render[dyn.timeout];
            if (ms !== undefined) this.#handleTimeout(ms);  // Background
            const name = this.name;
            if (name !== undefined) render = render[name];
            const args = this.args;
            this.controller = await render(this, args !== undefined ?
                                           JSON.parse(args) : {});
            this.classList.add('rendered');
            qs(this, '& > .error')?.remove?.();
            await this._ready();
        } catch (e) {
            console.error(e);
            showAlert(e);
        }
    }

    attr(name) {
        const v = this.getAttribute(name);
        return v !== null ? v : undefined;
    }

    // Attribute accessors.
    get type() { return this.attr('type'); }
    get name() { return this.attr('name'); }
    get args() { return this.attr('args'); }

    async #handleTimeout(ms) {
        await sleep(ms);
        if (this.classList.contains('rendered')) return;

        // Report potential issues, e.g. due to blocking on asyncGet attributes.
        const msg = html`\
<div class="error">\
<strong><code>{${this.type}}</code> Rendering seems to have failed.</strong>\
<ul><li>Check the JavaScript console for errors.</li></ul></div>`;
        const ul = qs(msg, 'ul');
        const pending = pendingAsyncGetFor(this.type);
        const cs = [...Object.keys(pending)];
        cs.sort();
        for (const c of cs) {
            const li = ul.appendChild(elmt`\
<li>Check the names of the following <code>${c}</code> attributes: </li>`);
            const as = pending[c];
            as.sort();
            for (const [i, a] of as.entries()) {
                li.appendChild(html`${i > 0 ? ", " : ""}<code>${a}</code>`)
            }
        }
        this.replaceChildren(msg);
    }
}

customElements.define('tdoc-dyn', DynElement);

// Resolve dyn elements of a specific type. If el is missing, all dyn elements
// of that type are returned. If el is a string, the dyn element with that name
// is returned, or an exception is thrown if it cannot be found. Otherwise, el
// is returned unchanged.
export async function resolveDyn(type, el) {
    if (el && typeof el !== 'string') return el;
    await domLoaded;
    const node = qs(document, `\
tdoc-dyn[type="${CSS.escape(type)}"][name="${CSS.escape(el)}"]`);
    if (!node) {
        throw htmle`\
<code>{${type}}</code> Directive not found: <code>${el}</code>`;
    }
    return node;
}
