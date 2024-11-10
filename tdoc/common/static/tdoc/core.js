// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

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

// Prevent doctools.js from capturing editor key events, in case keyboard
// shortcuts are enabled.
domLoaded.then(() => {
    if (typeof BLACKLISTED_KEY_CONTROL_ELEMENTS !== 'undefined') {
        BLACKLISTED_KEY_CONTROL_ELEMENTS.add('DIV');
    }
});

// Handle admonition expansion.
domLoaded.then(() => {
    for (const el of document.querySelectorAll('.admonition.dropdown')) {
        const title = el.querySelector('.admonition-title')
        title.addEventListener('click', () => {
            el.classList.toggle('expand');
        });
        const btn = title.appendChild(element('<button></button>'));
        btn.addEventListener('click', (e) => {
            el.classList.toggle('expand');
            e.stopPropagation();
        });
    }
});

// Handle solution toggling.
globalThis.tdocToggleSolutions = () => {
    const ds = document.documentElement.dataset;
    if (ds.tdocSolutions === 'hide') {
        delete ds.tdocSolutions;
    } else {
        ds.tdocSolutions = 'hide';
    }
};
