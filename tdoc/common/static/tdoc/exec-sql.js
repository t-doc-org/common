// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {default as sqlite3_init} from '../sqlite/sqlite3-worker1-promiser.mjs';
import {element, text} from './core.js';
import {Executor, UserError} from './exec.js';

let promiser;

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
        if (!sql) sql = ' ';  // Avoid exception on empty statements
        await promiser('exec', {dbId: this.dbId, sql, callback: on_result});
    }
}

class SqlExecutor extends Executor {
    static lang = 'sql';

    static async init() {
        promiser = await sqlite3_init({
            // debug: console.debug,
        });
        const config = await Database.config();
        console.info(`[t-doc] SQLite ${config.version.libVersion}`);
    }

    addControls(controls) {
        if (this.when === 'click' || (this.editable && this.when !== 'never')) {
            this.runCtrl = controls.appendChild(this.runControl());
            this.runCtrl.disabled = true;
        }
        super.addControls(controls);
    }

    onReady() {
        if (this.runCtrl) this.runCtrl.disabled = false;
    }

    preRun(run_id) {
        if (this.runCtrl) this.runCtrl.disabled = true;
    }

    postRun(run_id) {
        if (this.runCtrl) this.runCtrl.disabled = false;
    }

    async run(run_id) {
        let db;
        try {
            this.replaceOutputs([]);
            db = await Database.open(`file:db-${run_id}?vfs=memdb`);
            let output, tbody;
            for (const [code, node] of this.codeBlocks()) {
                await db.exec(code, res => {
                    if (res.columnNames.length === 0) return;
                    if (!output) {
                        output = this.outputTable(res.columnNames);
                        tbody = output.querySelector('tbody');
                        this.appendOutputs([output]);
                    }
                    if (res.row) {
                        tbody.appendChild(this.resultRow(res.row));
                    } else {
                        if (tbody.children.length === 0) {
                            tbody.appendChild(
                                this.noResultsRow(res.columnNames));
                        }
                        output = undefined;
                        tbody = undefined;
                    }
                });
            }
        } catch (e) {
            if (e.dbId !== db.dbId) throw e;
            throw new UserError(
                /^(SQLITE_[A-Z0-9_]+: sqlite3 result code \d+: )?(.*)$/
                    .exec(e.result.message)[2]);
        } finally {
            if (db) await db.close();
        }
    }

    async stop(run_id) {}

    outputTable(columns) {
        const output = element(`\
<div class="tdoc-exec-output"><div class="pst-scrollable-table-container">\
<table class="table"><thead><tr></tr></thead><tbody></tbody></table>\
</div></div>`);
        this.setOutputStyle(
            output.querySelector('.pst-scrollable-table-container'));
        const tr = output.querySelector('tr');
        for (const col of columns) {
            tr.appendChild(element(`<th class="text-center"></th>`))
                .appendChild(text(col));
        }
        if (this.runCtrl) {
            output.appendChild(element(`\
<button class="fa-xmark tdoc-remove" title="Remove"></button>`))
                .addEventListener('click', () => { output.remove(); });
        }
        return output;
    }

    resultRow(row) {
        const tr = element(`<tr></tr>`);
        for (const val of row) {
            tr.appendChild(element(`<td class="text-center"></td>`))
                .appendChild(val === null ? element(`<code>NULL</code>`)
                                          : text(val));
        }
        return tr;
    }

    noResultsRow(columns) {
        return element(`\
<tr class="tdoc-no-results">\
<td colspan="${columns.length}">No results</td>\
</tr>`);
    }
}

Executor.apply(SqlExecutor);
