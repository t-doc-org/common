// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {bearerAuthorization, domLoaded, fetchJson, text, toBase64} from './tdoc/core.js';
import {decryptSecret, pageKey, random} from './tdoc/crypto.js';

const key = await pageKey('key', 'FJbV5IShbHru');
const token = await decryptSecret(key, {
    iv: 'QL9XKY39mT5OtxbY',
    data: 'PuPII8bR2FZNjsahCUBQR1ABT6iR3VO09n43BM3R81UGIxR8mFuNdmcoXyabZrYX',
});

const storeUrl = tdoc.store_url || `${location.origin}/*store`;
const session = await toBase64(await random(18));

function log(data) {
    return fetchJson(`${storeUrl}/log`, {
        headers: bearerAuthorization(token),
        body: {
            'time': Date.now(),
            'location': location.origin + location.pathname,
            'session': session, 'data': data,
        },
    });
}

let count = 0;

domLoaded.then(() => {
    const app = document.querySelector('.tdoc-web-app');
    app.querySelector('button').addEventListener('click', async () => {
        ++count;
        app.querySelector('span').replaceChildren(text(`${count}`));
        console.log(await log({'count': count}));
    });
});
