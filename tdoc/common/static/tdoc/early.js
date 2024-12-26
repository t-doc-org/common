// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

'use strict';
(() => {
    // Polyfill Promise.withResolvers if necessary.
    if (!Promise.withResolvers) {
        Promise.withResolvers = () => {
            let resolve, reject;
            const promise = new Promise((res, rej) => {
                resolve = res;
                reject = rej;
            });
            return {promise, resolve, reject};
        };
    }

    const script = document.currentScript;
    const staticUrl = new URL('..', script.src).toString();

    // Import a module specified relative to the _static directory.
    tdoc.import = async module => await import(new URL(module, staticUrl));

    // Set data-* attributes on the <html> tag.
    Object.assign(document.documentElement.dataset, tdoc.html_data);

    // Disable all global keydown event listeners, as they can interfere with
    // per-element listeners. In particular, this disables the search shortcut
    // handler installed by pydata-sphinx-theme.js.
    const doAddEventListener = window.addEventListener;
    window.addEventListener = (...args) => {
        if (args[0] === 'keydown') return;
        return doAddEventListener(...args);
    };

    // Set up the SharedArrayBuffer workaround as configured.
    const workers = navigator.serviceWorker;
    const enableSAB = tdoc['enable_sab'];
    const url = new URL(`../tdoc-worker.js?sab=${enableSAB}`, staticUrl)
        .toString();
    if (enableSAB === 'no') {
        return (async () => {
            const reg = await workers.getRegistration(url);
            if (reg && await reg.unregister()) {
                console.info("[t-doc] Service worker unregistered");
                location.reload();
            }
        })();
    }
    if (crossOriginIsolated && enableSAB === 'cross-origin-isolation') {
        console.info("[t-doc] Cross-origin isolated");
        return;
    }
    if (!isSecureContext) {
        console.warn("[t-doc] Not a secure context; SAB disabled");
        return;
    }
    if (!workers) {
        console.warn("[t-doc] No service worker container; SAB disabled");
        return;
    }
    (async () => {
        const reg = await workers.register(
            url, {type: 'module', scope: script.getAttribute('scope')});
        reg.addEventListener('updatefound', () => {
            console.info('[t-doc] Service worker update');
            location.reload();
        });
        if (reg.active && !workers.controller) location.reload();
    })();
})();
