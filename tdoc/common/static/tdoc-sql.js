// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {default as sqlite3_init} from './sqlite3-worker1-promiser.mjs';
import {Executor, element, text} from './tdoc-exec.js';

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

class SqlExecutor extends Executor {
    static lang = 'sql';
    static db_num = 0;

    async run() {
        let output, tbody;
        const db = await Database.open(
            `file:db-${SqlExecutor.db_num++}?vfs=memdb`);
        try {
            for (const [code, node] of this.codeBlocks()) {
                await db.exec(code, res => {
                    if (node !== this.node) return;
                    if (res.columnNames.length === 0) return;
                    if (!output) {
                        output = element(`\
<div class="tdoc-exec-output pst-scrollable-table-container">\
<table class="table"><thead><tr></tr></thead><tbody></tbody></table>\
</div>`);
                        const tr = output.querySelector('tr');
                        for (const col of res.columnNames) {
                            const th = tr.appendChild(element(
                                `<th class="text-center"></th>`));
                            th.appendChild(text(col));
                        }
                        tbody = output.querySelector('tbody');
                    }
                    if (res.row) {
                        const tr = tbody.appendChild(element(`<tr></tr>`));
                        for (const val of res.row) {
                            tr.appendChild(element(
                                    `<td class="text-center"></td>`))
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
        } catch (e) {
            let msg;
            if (e.dbId === db.dbId) {
                msg = /^(SQLITE_ERROR: sqlite3 result code \d+: )?(.*)$/
                        .exec(e.result.message)[2]
            } else {
                console.error(e);
                msg = e.toString();
            }
            output = element(`\
<div class="tdoc-exec-output tdoc-error"><strong>Error:</strong></div>`);
            output.appendChild(text(` ${msg}`));
        } finally {
            await db.close();
        }
        this.replaceOutputs(output ? [output] : []);
    }
}

const config = await Database.config();
console.info(`[t-doc] SQLite version: ${config.version.libVersion}`);
Executor.apply(SqlExecutor);
