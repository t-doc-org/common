// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

// UTF-8 text encoder and decoder.
export const enc = new TextEncoder();
export const dec = new TextDecoder();

// The URL of the root of the book.
export const rootUrl = new URL('../..', import.meta.url);

// Resolves when the DOM content has loaded and deferred scripts have executed.
export const domLoaded = new Promise(resolve => {
    if (document.readyState !== 'loading') {
        resolve();
    } else {
        document.addEventListener('DOMContentLoaded', resolve);
    }
});

// Create a text node.
export function text(value) {
    return document.createTextNode(value);
}

// Create an DocumentFragment node.
export function html(html) {
    const el = document.createElement('template');
    el.innerHTML = html;
    return el.content;
}

// Create an element node.
export function element(html) {
    const el = document.createElement('template');
    el.innerHTML = html.trim();
    return el.content.firstChild;
}

// Return true iff the given element is within the root viewport.
export function isVisible(el) {
    const rect = el.getBoundingClientRect();
    return rect.top >= 0 && rect.left >= 0 &&
           rect.bottom <= document.documentElement.clientHeight &&
           rect.right <= document.documentElement.clientWidth;
}

// Return a <span> containing inline math. The element must be typeset after
// being added to the DOM.
export function inlineMath(value) {
    const el = element('<span class="math notranslate nohighlight"></span>');
    const [start, end] = MathJax.tex?.inlineMath ?? ['\\(', '\\)'];
    el.appendChild(text(`${start}${value}${end}`));
    return el;
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
    const el = element('<div class="math notranslate nohighlight"></div>');
    const [start, end] = MathJax.tex?.displayMath ?? ['\\[', '\\]'];
    el.appendChild(text(`${start}${out.join('')}${end}`));
    return el;
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
export function focusIfVisible(el) {
    const active = document.activeElement;
    if ((!active || active.tagName === 'BODY') && isVisible(el)) el.focus();
}

const cMinus = '-'.charCodeAt(0), cPlus = '+'.charCodeAt(0);
const c0 = '0'.charCodeAt(0), cA = 'A'.charCodeAt(0);

// Convert a string to an integer. Returns undefined if the string is not a
// valid integer.
export function strToInt(s, radix = 10) {
    if (!(2 <= radix && radix <= 36)) return;
    s = s.toUpperCase();
    let i = 0, sign = 1, res = 0;
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
    }
    return sign * res;
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
        throw Error(`Request failed: ${resp.status} ${resp.statusText}`);
    }
    return await resp.json();
}

// Return an Authorization header with the given bearer token.
export function bearerAuthorization(token) {
    return token ? {'Authorization': `Bearer ${token}`} : {};
}

// Return a promise that resolves after the given number of milliseconds.
export function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Canonicalize a document path, or the current document if missing.
export function docPath(path) {
    if (path === undefined) path = document.location.pathname;
    if (path.endsWith('.html')) path = path.slice(0, -5);
    if (path.endsWith('/')) path += 'index';
    return path;
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
