// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

// UTF-8 text encoder and decoder.
export const enc = new TextEncoder();
export const dec = new TextDecoder();

// The dataset of the <html> tag.
export const htmlData = document.documentElement.dataset;

// The URL of the root of the site.
export const rootUrl = new URL('../..', import.meta.url);

// Information about the page.
export const page = {
    origin: tdoc.dev ? '' : location.origin,
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

// Resolves when the DOM content has loaded and deferred scripts have executed.
export const domLoaded = new Promise(resolve => {
    if (document.readyState !== 'loading') {
        resolve();
    } else {
        document.addEventListener('DOMContentLoaded', resolve);
    }
});

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
    if (html.length === 1 && !values[0]) return html[0];
    const parts = [];
    for (const [i, s] of html.entries()) {
        parts.push(s);
        const v = values[i];
        if (v) parts.push(escape(v.toString()));
    }
    return parts.join('');
}

// Create an DocumentFragment node.
export function html(tmpl, ...values) {
    if (typeof tmpl !== 'string') tmpl = interpolateHtml(tmpl, values);
    const el = document.createElement('template');
    el.innerHTML = tmpl;
    return el.content;
}

// Create an Element node.
export function elmt(tmpl, ...values) {
    return html(tmpl, ...values).firstElementChild;
}

// Query a single matching element from a node.
export function qs(node, selector) {
    return node?.querySelector?.(selector);
}

const emptyNodeList = document.createElement('template').querySelectorAll('p');

// Query all matching elements from a node.
export function qsa(node, selector) {
    if (node === undefined || node === null) return emptyNodeList;
    return node.querySelectorAll(selector);
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

// Return a <span> containing inline math. The element must be typeset after
// being added to the DOM.
export function inlineMath(value) {
    const [start, end] = MathJax.tex?.inlineMath ?? ['\\(', '\\)'];
    return elmt`\
<span class="math notranslate nohighlight">${start}${value}${end}</span>`;
}

// Return a <div> containing display math. The element must be typeset after
// being added to the DOM.
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
                resolve(res.substr(res.indexOf(',') + 1));
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
    const resp = await fetch(url, {
        method: 'POST',
        cache: 'no-cache',
        referrer: '',
        ...opts,
        headers: {
            'Content-Type': 'application/json',
            ...opts.headers || {},
        },
        ...opts.body ? {body: JSON.stringify(opts.body)} : {},
    });
    if (resp.status !== 200) {
        throw Error(`Request failed: ${resp.status} ${resp.statusText}`,
                    {cause: {status: resp.status}});
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
        if (!(tdoc.dev || tdoc.domain_storage.origin)) return localStorage;
        const {port1, port2} = new MessageChannel();
        const origin = tdoc.dev ? location.origin
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
