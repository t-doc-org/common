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
    const importMap = {};

    // Import a module specified relative to the _static directory. Check if the
    // module was already imported via a <script type="module"> tag with a
    // cache-busting src, and use that to avoid importing the module multiple
    // times.
    tdoc.import = mod => {
        let url = new URL(mod, staticUrl).toString();
        const m = importMap[url];
        if (m !== undefined) {
            url = m;
        } else {
            importMap[url] = url;
            for (const el of document.querySelectorAll('script[type=module]')) {
                if (el.src.startsWith(url + '?')) {
                    url = importMap[url] = el.src;
                    break;
                }
            }
        }
        return import(url);
    };

    // Import multiple modules specified relative to the _static directory.
    tdoc.imports = (...modules) => Promise.all(
        modules.map(m => tdoc.import(m)));

    // Return a function that waits for a set of promises before invoking a
    // function. The current script is passed as the first argument.
    tdoc.when = (...args) => {
        const ready = Promise.all(args.slice(0, -1)), fn = args.at(-1);
        return async (...args) => {
            const script = document.currentScript;
            await ready;
            return await fn(script, ...args);
        };
    };

    // Set data-* attributes on the <html> tag.
    Object.assign(document.documentElement.dataset, tdoc.html_data);

    // Disable undesired global keydown event listeners, as they can interfere
    // with per-element listeners.
    const doAddEventListener = window.addEventListener;
    window.addEventListener = (...args) => {
        if (args[0] === 'keydown') {
            const stack = new Error().stack ?? '';
            // Disable the search shortcut.
            if (stack.includes('pydata-sphinx-theme.js')) return;
        }
        return doAddEventListener(...args);
    };

    // Enable an origin trial.
    tdoc.enableOriginTrial = token => {
        const meta = document.createElement('meta');
        meta.httpEquiv = 'origin-trial';
        meta.content = token;
        document.head.append(meta);
    };
    // https://developer.chrome.com/origintrials/#/view_trial/1603844417297317889
    tdoc.enableOriginTrial(`\
AnazgzvWiP27bmtE9xuk594k/IhVQlM2Ho9j9fztj3gDEQUHOTQCLhqH0ihfYkJwtXp4tpDy87EVwfd\
vgrK67AoAAABieyJvcmlnaW4iOiJodHRwczovL3QtZG9jLm9yZzo0NDMiLCJmZWF0dXJlIjoiV2ViQX\
NzZW1ibHlKU1Byb21pc2VJbnRlZ3JhdGlvbiIsImV4cGlyeSI6MTc1MzE0MjQwMH0=`);

    // Set up the SharedArrayBuffer workaround as configured.
    const workers = navigator.serviceWorker;
    const enableSAB = tdoc.enable_sab;
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
