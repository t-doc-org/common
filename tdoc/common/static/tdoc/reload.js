// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

const build = tdoc['build'];
console.info(`[t-doc] Build tag: ${build}`);

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function reloadOnTagChange() {
    for (;;) {
        try {
            const resp = await fetch(
                `${document.location.origin}/*build?t=${build}`);
            if (resp.ok) {
                const tag = (await resp.text()).trim();
                if (tag === '') continue;
                if (tag !== build) location.reload();
            }
        } catch (e) {}
        await sleep(1000);
    }
}

if (build) reloadOnTagChange();
