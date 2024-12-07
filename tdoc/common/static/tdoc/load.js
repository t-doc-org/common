// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {domLoaded, element} from './core.js';

// Prevent doctools.js from capturing editor key events, in case keyboard
// shortcuts are enabled.
domLoaded.then(() => {
    if (typeof BLACKLISTED_KEY_CONTROL_ELEMENTS !== 'undefined') {
        BLACKLISTED_KEY_CONTROL_ELEMENTS.add('DIV');
    }
});

// Handle admonition expansion. The button is needed to enable keyboard focus.
domLoaded.then(() => {
    for (const el of document.querySelectorAll('.admonition.dropdown')) {
        const title = el.querySelector('.admonition-title')
        title.addEventListener('click', () => {
            el.classList.toggle('expand');
        });
        // Enable keyboard navigation.
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
