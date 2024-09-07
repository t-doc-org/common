// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {default as sqlite3_init} from './sqlite3-worker1-promiser.mjs';
import {addEditor, findEditor} from './tdoc-editor.js';

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

    // TODO: Prevent multiple parallel executions of the same node, and disable
    //       the "Run" button while executing.

    let result, tbody;
    const db = await Database.open(`file:db-${db_num++}?vfs=memdb`);
    try {
        for (const [i, node] of nodes.entries()) {
            await db.exec(getText(node), res => {
                if (res.columnNames.length === 0) return;
                if (i < nodes.length - 1) return;
                if (!result) {
                    result = element(`\
<div class="pst-scrollable-table-container tdoc-exec-output">\
<table class="table"><thead><tr></tr></thead><tbody></tbody></table>\
</div>`);
                    const tr = result.querySelector('tr');
                    for (const col of res.columnNames) {
                        const th = tr.appendChild(element(
                            `<th class="text-center"></th>`));
                        th.appendChild(text(col));
                    }
                    tbody = result.querySelector('tbody');
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
    } catch (e) {
        let msg;
        if (e.dbId === db.dbId) {
            msg = /^(SQLITE_ERROR: sqlite3 result code \d+: )?(.*)$/
                    .exec(e.result.message)[2]
        } else {
            console.error(e);
            msg = e.toString();
        }
        result = element(`\
<div class="tdoc-exec-output tdoc-error"><strong>Error:</strong></div>`);
        result.appendChild(text(` ${msg}`));
    } finally {
        await db.close();
    }
    replaceResults(exec, result ? [result] : []);
}

async function tryExecute(exec) {
    try {
        await execute(exec);
    } catch (e) {
        console.error(e);
    }
}

function getOrigText(exec) {
    return exec.querySelector('pre').textContent;
}

function getText(exec) {
    const editor = findEditor(exec);
    return editor ? editor.state.doc.toString() : getOrigText(exec);
}

function replaceResults(exec, results) {
    let prev = exec, i = 0;
    for (;; ++i) {
        const next = prev.nextElementSibling;
        if (!next || !next.classList.contains('tdoc-exec-output')) break;
        if (i < results.length) {
            prev = results[i];
            next.replaceWith(prev);
        } else {
            next.remove();
        }
    }
    for (; i < results.length; ++i) {
        const res = results[i];
        prev.after(res);
        prev = res;
    }
}

await waitLoaded();
console.info("SQLite version:", (await Database.config()).version.libVersion);

for (const exec of document.querySelectorAll('div.tdoc-exec.highlight-sql')) {
    // If the field is editable, create the editor.
    const editable = exec.classList.contains('tdoc-editable');
    const when = exec.dataset.tdocWhen;
    let origText;
    if (editable) {
        origText = getOrigText(exec).trim();
        addEditor(exec.querySelector('div.highlight'), {
            language: 'sql',
            text: origText,
            onRun: when !== 'never' ? async () => { await tryExecute(exec); }
                                    : undefined,
        });
    }

    // Execute immediately if requested.
    if (when === 'load') tryExecute(exec);  // Intentionally don't await

    // Add execution controls.
    const controls = element(`<div class="tdoc-exec-controls"></div>`);
    if (when === 'click' || (editable && when !== 'never')) {
        controls.appendChild(element(`\
<button class="tdoc-exec-run" title="Run${editable ? ' (Shift+Enter)' : ''}">\
</button>`))
            .addEventListener('click', async () => { await tryExecute(exec); });
    }
    if (editable && origText !== '') {
        controls.appendChild(element(
            `<button class="tdoc-exec-reset" title="Reset input"></button>`))
            .addEventListener('click', () => {
                const editor = findEditor(exec), state = editor.state;
                editor.dispatch(state.update({changes: {
                    from: 0, to: state.doc.length,
                    insert: origText,
                }}));
            });
    }
    if (controls.children.length > 0) exec.appendChild(controls);
}
