// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import * as sl from './_static/sabayon-listeners.js';

const enableSAB = new URL(location).searchParams.get('sab');

addEventListener('install', () => skipWaiting());
addEventListener('activate', e => e.waitUntil(clients.claim()));

addEventListener('message', e => {
    if (enableSAB === 'sabayon') sl.message(e);
});

addEventListener('fetch', (e) => {
    switch (enableSAB) {
    case 'cross-origin-isolation':
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
        break;
    case 'sabayon':
        sl.fetch(e);
        break;
    }
});