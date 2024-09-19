// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

(({document: doc, navigator: {serviceWorker: workers}}) => {
    if (!doc) {
        // Running in the service worker. Capture fetch() requests and add the
        // relevant headers.
        addEventListener('install', () => skipWaiting());
        addEventListener('activate', e => e.waitUntil(clients.claim()));
        addEventListener('fetch', e => {
            const req = e.request;
            if (req.cache === 'only-if-cached' && req.mode !== 'same-origin') {
                return;
            }
            e.respondWith((async () => {
                const resp = await fetch(req);
                const {status, statusText, body} = resp;
                if (!status || status >= 400) return resp;
                const headers = new Headers(resp.headers);
                headers.set('Cross-Origin-Embedder-Policy', 'require-corp');
                headers.set('Cross-Origin-Opener-Policy', 'same-origin');
                headers.set('Cross-Origin-Resource-Policy', 'cross-origin');
                return new Response(resp.body, {status, statusText, headers});
            })());
        });
        return;
    }

    // Running in the main thread. Register the service worker if necessary.
    if (crossOriginIsolated) {
        console.info("[t-doc] Already cross-origin isolated");
        return;
    }
    if (!isSecureContext) {
        console.warn("[t-doc] Not a secure context; COI workaround disabled");
        return;
    }
    if (!workers) {
        console.warn(
            "[t-doc] No service worker container; COI workaround disabled");
        return;
    }
    const script = doc.currentScript;
    workers.register(script.src, {scope: script.getAttribute('scope')})
        .then(reg => {
            console.info('[t-doc] COI service worker registered');
            reg.addEventListener('updatefound', () => location.reload());
            if (reg.active && !workers.controller) location.reload();
        })
        .catch(e => {
            console.error(
                `[t-doc] Failed to register COI service worker: ${e}`);
        });
})(self);
