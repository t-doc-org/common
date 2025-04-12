// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

const build = tdoc['build'];
console.info(`[t-doc] Build tag: ${build}`);
const dec = new TextDecoder();

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function reloadOnTagChange() {
    for (;;) {
        try {
            const resp = await fetch(
                `${document.location.origin}/*build?t=${build}`);
            if (resp.ok) {
                let tag = '';
                const reader = resp.body.getReader();
                try {
                    for (;;) {
                      const {value, done} = await reader.read();
                      tag += dec.decode(value).trim();
                      if (done) break;
                    }
                } finally {
                    reader.releaseLock();
                }
                if (tag === '') continue;
                if (tag !== build) location.reload();
            }
        } catch (e) {}
        await sleep(1000);
    }
}

if (build) reloadOnTagChange();
