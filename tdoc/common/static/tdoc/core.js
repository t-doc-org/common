// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

// UTF-8 text encoder and decoder.
export const enc = new TextEncoder();
export const dec = new TextDecoder();

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

// Create an element node.
export function element(html) {
    const t = document.createElement('template');
    t.innerHTML = html.trim();
    return t.content.firstChild;
}

// Return true iff the given element is within the root viewport.
export function isVisible(el) {
    const rect = el.getBoundingClientRect();
    return rect.top >= 0 && rect.left >= 0 &&
           rect.bottom <= document.documentElement.clientHeight &&
           rect.right <= document.documentElement.clientWidth;
}

// Focus an element if it is visible and no other element has the focus.
export function focusIfVisible(el) {
    const active = document.activeElement;
    if ((!active || active.tagName === 'BODY') && isVisible(el)) el.focus();
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
