// Copyright 2025 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {bearerAuthorization, fetchJson, rootUrl} from './core.js';

export const url = (() => {
    if (tdoc.dev) return '/*api';
    if (tdoc.api_url) return tdoc.api_url;
    const loc = new URL(location);
    if (loc.host === 't-doc.org' || loc.host.endsWith('.t-doc.org')) {
        return `${loc.protocol}//api.t-doc.org`;
    }
    return null;
})();
if (url) console.info(`[t-doc] API server: ${url}`);

export function log(session, data, options) {
    return fetchJson(`${url}/log`, {
        headers: bearerAuthorization(options?.token),
        body: {
            'time': Date.now(),
            'location': location.origin + location.pathname,
            'session': session, 'data': data,
        },
    });
}
