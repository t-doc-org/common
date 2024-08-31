// Copyright 2024 Caroline Blank <caro@c-space.org>
// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {default as sqlite3_init} from './jswasm/sqlite3-worker1-promiser.mjs';

function waitLoaded() {
    return new Promise(resolve => {
        if (document.readyState !== 'loading') {
            resolve();
        } else if (document.addEventListener) {
            document.addEventListener('DOMContentLoaded', resolve);
        } else {
            document.attachEvent('onreadystatechange', () => {
                if (document.readyState === 'interactive') resolve();
            });
        }
    });
}

function text(value) {
    return document.createTextNode(value);
}

function element(html) {
    const t = document.createElement('template');
    t.innerHTML = html.trim();
    return t.content.firstChild;
}

const promiser = await sqlite3_init({
    // debug: console.debug,
});

class Database {
    static async config() {
        return (await promiser('config-get', {})).result;
    }

    static async open(filename) {
        let {dbId} = await promiser('open', {filename});
        return new Database(dbId);
    }

    constructor(dbId) {
        this.dbId = dbId;
    }

    async close() {
        if (this.dbId) {
            // TODO: Check if "unlink" makes any difference
            await promiser('close', {dbId: this.dbId, unlink: true});
            delete this.dbId;
        }
    }

    async exec(sql, on_result) {
        // TODO: Check if other args could be useful, e.g. for splitting a
        // script into multiple statements
        await promiser('exec', {dbId: this.dbId, sql, callback: on_result});
    }
}

let db_num = 0;

async function execute(exec) {
    // Compute the chain of nodes to execute.
    const nodes = [];
    for (let node = exec; node;) {
        if (node.classList.contains('tdoc-exec')) {
            nodes.push(node);
            node = document.getElementById(node.dataset.tdocAfter)
        } else {  // Secondary name as a nested <span>
            node = node.parentNode;
        }
    }
    nodes.reverse();

    removeResults(exec);
    let results, tbody;
    const db = await Database.open(`file:db-${db_num++}?vfs=memdb`);
    try {
        for (const [i, node] of nodes.entries()) {
            const pre = node.querySelector('pre');
            if (!pre) {
                console.error("<pre> element not found in node ", node);
                continue;
            }
            await db.exec(pre.innerText, res => {
                if (res.columnNames.length === 0) return;
                if (i < nodes.length - 1) return;
                if (!results) {
                    results = element(`\
<div class="pst-scrollable-table-container tdoc-exec-output">\
<table class="table"><thead><tr></tr></thead><tbody></tbody></table>\
</div>`);
                    const tr = results.querySelector('tr');
                    for (const col of res.columnNames) {
                        const th = tr.appendChild(element(
                            `<th class="text-center"></th>`));
                        th.appendChild(text(col));
                    }
                    tbody = results.querySelector('tbody');
                }
                if (res.row) {
                    const tr = tbody.appendChild(element(`<tr></tr>`));
                    for (const val of res.row) {
                        tr.appendChild(element(`<td class="text-center"></td>`))
                            .appendChild(val === null ?
                                         element(`<code>NULL</code>`) :
                                         text(val));
                    }
                } else if (tbody.children.length === 0) {
                    tbody.appendChild(element(`\
<tr class="tdoc-no-results">\
<td colspan="${res.columnNames.length}">No results</td>\
</tr>`))
                }
            });
        }
        if (results) exec.after(results);
    } catch (e) {
        let msg;
        if (e.dbId === db.dbId) {
            msg = /^(SQLITE_ERROR: sqlite3 result code \d+: )?(.*)$/
                    .exec(e.result.message)[2]
        } else {
            msg = e.toString();
        }
        results = element(`\
<div class="tdoc-exec-output tdoc-error"><strong>Error:</strong></div>`);
        results.appendChild(text(` ${msg}`));
        exec.after(results);
    } finally {
        await db.close();
    }
}

async function tryExecute(exec) {
    try {
        await execute(exec);
    } catch (e) {
        console.error(e);
    }
}

function removeResults(exec) {
    for (;;) {
        const next = exec.nextElementSibling;
        if (!next || !next.classList.contains('tdoc-exec-output')) break;
        next.parentNode.removeChild(next);
    }
}

await waitLoaded();
console.info("SQLite version:", (await Database.config()).version.libVersion);

for (const exec of document.querySelectorAll('div.tdoc-exec.highlight-sql')) {
    const when = exec.dataset.tdocWhen;
    if (when === 'load') {
        tryExecute(exec);  // Intentionally don't await
    } else if (when === 'click') {
        const controls = exec.appendChild(element(`\
<div class="tdoc-exec-controls">\
<button class="tdoc-exec-run" title="Run"></button>\
<button class="tdoc-exec-reset" title="Reset"></button>\
</div>`));
        controls.querySelector('.tdoc-exec-run').addEventListener(
            'click', async () => { await tryExecute(exec); });
        controls.querySelector('.tdoc-exec-reset').addEventListener(
            'click', () => { removeResults(exec); });
    }
}
