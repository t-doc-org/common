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
        // TODO: Pass name and vfs separately
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
    const pre = exec.querySelector('pre');
    if (!pre) {
        console.error("<pre> element not found");
        return;
    }
    // TODO: Find dependencies
    const sql = pre.innerText;
    let results, tbody;
    const db = await Database.open(`file:db-${db_num++}?vfs=memdb`);
    try {
        // TODO: Remove previous result and error
        // TODO: Execute dependencies
        await db.exec(sql, res => {
            if (!results) {
                results = element(`\
<div class="pst-scrollable-table-container tdoc-exec-output">\
<table class="table">\
<thead><tr class="row-odd"></tr></thead>\
<tbody></tbody>\
</table>\
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
                const tr = tbody.appendChild(element(
                    `<tr class="${(res.rowNumber - 1) % 2 === 0 ? 'row-even'
                                  : 'row-odd'}"></tr>`));
                for (const val of res.row) {
                    const td = tr.appendChild(element(
                        `<td class="text-center"></td>`));
                    td.appendChild(text(val));
                }
            } else if (tbody.children.length === 0) {
                tbody.appendChild(element(`\
<tr class="row-odd tdoc-no-results">\
<td colspan="${res.columnNames.length}">No results</td>\
</tr>`))
            }
        });
        if (results) exec.after(results);
    } catch (e) {
        if (e.dbId == db.dbId) {
            results = element(`\
<div class="tdoc-exec-output tdoc-error"><span>Error:</span></div>`);
            const msg = /^(SQLITE_ERROR: sqlite3 result code \d+: )?(.*)$/
                        .exec(e.result.message)[2];
            results.appendChild(text(` ${msg}`));
            exec.after(results);
        } else {
            console.error(e);
        }
    } finally {
        await db.close();
    }
}

await waitLoaded();
console.info("SQLite version:", (await Database.config()).version.libVersion);

// TODO: Execute concurrently
for (const el of document.querySelectorAll('div.tdoc-exec.highlight-sql')) {
    try {
        await execute(el);
    } catch (e) {
        console.error(e);
    }
}
