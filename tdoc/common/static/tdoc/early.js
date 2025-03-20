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
    tdoc.import = module => import(new URL(module, staticUrl));

    // Import multiple modules specified relative to the _static directory.
    tdoc.imports = (...modules) => Promise.all(
        modules.map(m => import(new URL(m, staticUrl))));

    // Return a function that waits for a set of promises before invoking a
    // function. The current script is passed as the first argument.
    tdoc.when = (...args) => {
        let ready = Promise.all(args.slice(0, -1));
        const fn = args.at(-1);
        return async (...args) => {
            let script = document.currentScript;
            await ready;
            return await fn(script, ...args);
        };
    };

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

    // Enable origin trials
    function enableOriginTrial(token) {
        const meta = document.createElement('meta');
        meta.httpEquiv = 'origin-trial';
        meta.content = token;
        document.head.append(meta);
    }
    // https://developer.chrome.com/origintrials/#/view_trial/1603844417297317889
    enableOriginTrial(`\
Ao6LvHcUOFEV1phI13OFiPm4SiJNS+CbkMZbtiypgmN6RpB63mKB0YnLuLLNdDUCPRtOzT9K8M1VCnX\
72U5Z1goAAABieyJvcmlnaW4iOiJodHRwczovL3QtZG9jLm9yZzo0NDMiLCJmZWF0dXJlIjoiV2ViQX\
NzZW1ibHlKU1Byb21pc2VJbnRlZ3JhdGlvbiIsImV4cGlyeSI6MTc0NDY3NTIwMH0=`);
    // https://developer.microsoft.com/en-us/microsoft-edge/origin-trials/trials/cea04bbf-b9ff-4ae6-8ea8-454bef2f6e6b
    enableOriginTrial(`\
A3yGefyVRes8vnz4JYPA6lAUM2jtb0H7pmnljIna6+dq16pv+UkC2ZxrvRTim2QxdgA1LeU2w4rOPAU\
M9fnLtQIAAABieyJvcmlnaW4iOiJodHRwczovL3QtZG9jLm9yZzo0NDMiLCJmZWF0dXJlIjoiV2ViQX\
NzZW1ibHlKU1Byb21pc2VJbnRlZ3JhdGlvbiIsImV4cGlyeSI6MTc0MjEzOTg5N30=`);

    // Set up the SharedArrayBuffer workaround as configured.
    const workers = navigator.serviceWorker;
    const enableSAB = tdoc['enable_sab'];
    const url = new URL(`../tdoc-worker.js?sab=${enableSAB}`, staticUrl)
        .toString();
    if (enableSAB === 'no' && workers) {
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
