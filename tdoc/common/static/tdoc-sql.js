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

function addChild(parent, tag) {
    const el = document.createElement(tag);
    parent.appendChild(el);
    return el;
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
        // TODO: Check if final result has anything useful
        // TODO: Check if other args could be useful, e.g. for splitting a
        // script into multiple statements
        await promiser('exec', {dbId: this.dbId, sql, callback: on_result});
    }

    async *query(sql) {
        let notify, queue;
        let promise = new Promise(resolve => { notify = resolve; });
        const exec = this.exec(sql, res => {
            if (queue) {
                queue.push(res);
            } else {
                queue = [res]
                notify(queue);
                promise = new Promise(resolve => { notify = resolve; });
            }
        });
        let done = false;
        while (!done) {
            const q = await promise;
            queue = undefined;
            for (const res of q) {
                done = !res.row;
                if (done) break;
                yield res;
            }
        }
        await exec;
    }
}

async function execute(exec) {
    const pre = exec.querySelector('pre');
    if (!pre) {
        console.error("<pre> element not found");
        return;
    }
    // TODO: Find dependencies
    const sql = pre.innerText;
    let results, tbody;
    const db = await Database.open('file:db?vfs=memdb');
    try {
        // TODO: Execute dependencies
        // TODO: Report errors in output
        for await (const res of db.query(sql)) {
            if (!results) {
                // TODO: Remove previous result table
                results = document.createElement('div');
                results.classList.add('pst-scrollable-table-container',
                                      'tdoc-sql-results');
                const table = addChild(results, 'table');;
                table.classList.add('table');
                const thead = addChild(table, 'thead');
                const tr = addChild(thead, 'tr');
                tr.classList.add('row-odd');
                for (const col of res.columnNames) {
                    const th = addChild(tr, 'th')
                    th.classList.add('text-center');
                    th.appendChild(text(col));
                }
                tbody = addChild(table, 'tbody');
            }
            const tr = addChild(tbody, 'tr');
            tr.classList.add(res.rowNumber % 2 === 0 ? 'row-odd' : 'row-even');
            for (const val of res.row) {
                const td = addChild(tr, 'td')
                td.classList.add('text-center');
                td.appendChild(text(val));
            }
        }
        if (results) exec.after(results);
    } finally {
        await db.close();
    }
}

await waitLoaded();
console.info("SQLite version:", (await Database.config()).version.libVersion);

for (const el of document.querySelectorAll('div.tdoc-exec.highlight-sql')) {
    await execute(el);
}
