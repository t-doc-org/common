// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

(({document: doc, navigator: {serviceWorker: workers}}) => {
    if (!doc) {
        // Running in the service worker.
        addEventListener('install', () => skipWaiting());
        addEventListener('activate', e => e.waitUntil(clients.claim()));

        // Capture fetch() requests and add the relevant headers.
        addEventListener('fetch', e => {
            const req = e.request;
            if (req.cache === 'only-if-cached' && req.mode !== 'same-origin') {
                return;
            }
            e.respondWith((async () => {
                const resp = await fetch(req);
                const {status, statusText, body} = resp;
                if (status === 0 || status >= 400) return resp;
                const headers = new Headers(resp.headers);
                headers.set('Cross-Origin-Embedder-Policy', 'require-corp');
                headers.set('Cross-Origin-Opener-Policy', 'same-origin');
                headers.set('Cross-Origin-Resource-Policy', 'cross-origin');
                return new Response(resp.body, {status, statusText, headers});
            })());
        });
        return;
    }

    // Running in the main thread.
    if (crossOriginIsolated === undefined) return;  // COI unsupported

    // Unregister the service worker if COI is disabled.
    const script = doc.currentScript;
    if (!tdocCrossOriginIsolate) {
        return (async () => {
            const reg = await workers.getRegistration(script.src);
            if (!reg) return;
            if (!await reg.unregister()) return;
            console.info("[t-doc] COI service worker unregistered");
            location.reload();
        })();
    }

    // Register the service worker if necessary.
    if (crossOriginIsolated) {
        console.info("[t-doc] Cross-origin isolated");
        return;
    }
    if (!isSecureContext) {
        console.warn("[t-doc] Not a secure context; COI disabled");
        return;
    }
    if (!workers) {
        console.warn("[t-doc] No service worker container; COI disabled");
        return;
    }
    (async () => {
        const reg = await workers.register(
            script.src, {scope: script.getAttribute('scope')});
        console.info('[t-doc] COI service worker registered');
        reg.addEventListener('updatefound', () => location.reload());
        if (reg.active && !workers.controller) location.reload();
    })();
})(self);
