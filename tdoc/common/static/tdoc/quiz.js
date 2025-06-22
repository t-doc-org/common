// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {
    dec, domLoaded, elmt, enable, fromBase64, on, qs, qsa,
} from './core.js';

// TODO(0.51): Remove
export function genTable(node, addCells) {
    // Find the first table that precedes `node`.
    let table;
    while (!table) {
        node = node.previousElementSibling;
        if (!node) {
            console.error("<table> not found");
            return;
        }
        table = qs(node, 'table.table');
    }

    // Add a column to all existing rows for the check button.
    qs(table, 'thead > tr').appendChild(elmt`<th></th>`);
    let tbody = qs(table, 'tbody');
    if (!tbody) tbody = table.appendChild(elmt`<tbody></tbody>`);
    for (const tr of qsa(tbody, 'tr')) {
        tr.appendChild(elmt`<td></td>`);
    }

    function addRow() {
        const row = elmt`<tr class="tdoc-quiz-row text-center"></tr>`;
        const button = elmt`<button class="tdoc-check fa-check"></button>`;
        const {verify, focus} = addCells(table, row, button);
        if (!verify) return;
        row.appendChild(elmt`<td></td>`).appendChild(button);
        on(button).click(() => {
            if (!verify()) return;
            enable(false, button);
            const focus = addRow();
            if (focus) focus.focus();
        });
        tbody.appendChild(row);
        return focus;
    }

    addRow();
}

class QuizBase {
    constructor(quiz) {
        this.quiz = quiz;
        this.hint = qs(quiz, '.tdoc-quiz-hint');
    }

    showHint(field, text, invalid = false) {
        this.hintField = field;
        this.hint.textContent = text;
        this.hint.style.left = this.hint.style.right = '';
        const cr = qs(this.quiz, '.content').getBoundingClientRect();
        const fr = field.getBoundingClientRect();
        const hr = this.hint.getBoundingClientRect();
        this.hint.style.top = `calc(${fr.top - cr.top - hr.height}px - 0.5rem)`;
        if (fr.left + hr.width >= cr.left + cr.width) {
            this.hint.style.right = '0';
        } else {
            this.hint.style.left = `${fr.left - cr.left}px`;
        }
        this.hint.classList.toggle('invalid', invalid);
        this.hint.classList.add('show');
    }

    setupFields(container) {
        this.fields = qsa(container, '.tdoc-quiz-field');
        this.btn = qs(container, 'button.tdoc-check');
        for (const field of this.fields) {
            on(field).blur(e => this.hint.classList.remove('show'));
            if (field instanceof HTMLInputElement && field.type === 'text') {
                on(field).keydown(e => this.onKeyDown(field, e))
            }
        }
        on(this.btn)
            .click(() => this.onClick())
            .blur(e => {
                if (e.relatedTarget !== this.hintField) {
                    this.hint.classList.remove('show');
                }
            });
    }

    onKeyDown(field, e) {
        if (e.altKey || e.ctrlKey || e.metaKey) return;
        if (e.key === 'Enter') {
            e.preventDefault();
            (nextField(this.fields, field) || this.btn).focus()
            if (e.shiftKey) this.btn.click();
        } else if (e.key === 'ArrowUp' && !e.shiftKey) {
            e.preventDefault();
            prevField(this.fields, field)?.focus?.()
        } else if (e.key === 'ArrowDown' && !e.shiftKey) {
            e.preventDefault();
            nextField(this.fields, field)?.focus?.()
        }
    }

    async onClick() {
        this.hint.classList.remove('show');
        let res = true;
        for (const field of this.fields) {
            const args = await this.check(field);
            const ok = !args.invalid && args.ok;
            if (res && !ok) field.focus();
            res = res && ok;
            field.classList.toggle('bad', !ok);
            if (!this.hint.classList.contains('show')) {
                if (args.invalid) {
                    this.showHint(field, args.invalid, true);
                } else if (!args.ok && args.hint) {
                    this.showHint(field, args.hint);
                }
            }
        }
        if (res) {
            enable(false, ...this.fields, this.btn);
            this.onSuccess();
        }
    }

    onSuccess() {}
}

class Quiz extends QuizBase {
    constructor(quiz) {
        super(quiz);
        this.setupFields(quiz);
    }

    async check(field) {
        const args = await checkArgs(field);
        args.apply(checkFns((field.dataset.check || 'default') + ' equal'));
        return args;
    }
}

class TableGenQuiz extends QuizBase {
    constructor(quiz) {
        super(quiz);
        this.table = qs(quiz, 'table');
        this.entries = [];

        // Extract the rows starting at the first placeholder or field. Also,
        // add a column to all existing rows for the check button.
        qs(this.table, 'thead > tr').appendChild(elmt`<th></th>`);
        const tbody = qs(this.table, 'tbody');
        this.preCnt = this.tmplCnt = 0;
        for (const tr of qsa(tbody, 'tr')) {
            if (this.tbody !== undefined
                    || qs(tr, '.tdoc-quiz-ph, .tdoc-quiz-field')) {
                if (!this.tbody) {
                    this.tbody = elmt`<tbody class="tdoc-quiz-entry"></tbody>`;
                }
                this.tbody.appendChild(tr);
                ++this.tmplCnt;
                tr.classList.remove('row-even', 'row-odd');
            } else {
                ++this.preCnt;
            }
            tr.appendChild(elmt`<td></td>`);
        }
        qs(this.tbody, 'tr:last-child > td:last-child')
            .appendChild(elmt`<<button class="tdoc-check fa-check"></button>`)
        if (this.preCnt === 0) tbody.remove();
    }

    setGenerator(fn) {
        this.generate = fn;
        this.addEntry();
    }

    addEntry(focus) {
        // Compute if row highlighting needs to be inverted.
        const inv = (this.preCnt + this.entries.length * this.tmplCnt) & 1 === 1;

        // Generate a new entry, and avoid duplicates if possible.
        let entry;
        for (let t = 0; t < 20; ++t) {
            entry = this.generate();
            if (!entry.equal) break;
            let end = this.entries.length;
            if (entry.history && entry.history < end) end = entry.history;
            let ok = true;
            for (let i = 0; i < end; ++i) {
                if (entry.equal(this.entries[this.entries.length - 1 - i])) {
                    ok = false;
                    break;
                }
            }
            if (ok) break;
        }
        this.entries.push(entry);

        // Set up the <tbody> for the new entry.
        const tbody = this.tbody.cloneNode(true);
        if (inv) tbody.classList.add('inv');
        for (const ph of qsa(tbody, '.tdoc-quiz-ph')) {
            entry[ph.dataset.text](ph);
        }
        this.table.appendChild(tbody);
        this.setupFields(tbody);
        if (focus) qs(tbody, '.tdoc-quiz-field')?.focus?.();
    }

    async check(field) {
        const args = await checkArgs(field);
        args.apply(checkFns(field.dataset.check));
        this.entries[this.entries.length - 1][args.text](args);
        return args;
    }

    onSuccess() { this.addEntry(true); }
}

export async function generator(name, fn) {
    await setupDone;
    for (const quiz of qsa(document, '.tdoc-quiz')) {
        if (quiz.dataset.gen === name) quiz.tdocQuiz.setGenerator(fn);
    }
}

function prevField(fields, field) {
    let prev;
    for (const f of fields) {
        if (f === field) return prev;
        prev = f;
    }
}

function nextField(fields, field) {
    let found = false;
    for (const f of fields) {
        if (found) return f;
        if (f === field) found = true;
    }
}

// TODO(0.51): Un-export
export const checks = {
    default(args) { checks.trim(args); },
    split(args, param = ',') { args.solution = args.solution.split(param); },
    trim(args) { args.applyAS(v => v.trim()); },
    remove: (args, param = '\\s+') => {
        args.applyAS(v => v.replaceAll(new RegExp(param, 'g'), ''));
    },
    // TODO(0.51): Remove
    'remove-whitespace': (args) => {
        args.applyAS(v => v.replaceAll(/\s+/g, ''));
    },
    lowercase(args) { args.applyAS(v => v.toLowerCase()); },
    uppercase(args) { args.applyAS(v => v.toUpperCase()); },
    json(args) { args.solution = JSON.parse(args.solution); },
    indirect(args) { args.apply(checkFns(args.text)); },
    equal(args) {
        if (args.solution instanceof Array) {
            args.ok = args.solution.includes(args.answer);
        } else if (typeof args.solution === 'object') {
            const res = args.solution[args.answer] ?? false;
            args.ok = res === true;
            if (typeof res === 'string') args.hint = res;
        } else {
            args.ok = args.answer === args.solution;
        }
    },
};

export function check(name, fn) {
    checks[name] = fn;
}

function checkFns(spec) {
    if (!spec || !spec.trim()) return [];
    return spec.trim().split(/\s+/).filter(c => c).map(c => {
        const m = /([^(]+)\((.*)\)/.exec(c);
        let fn;
        if (m) {
            const cfn = checks[m[1]];
            if (cfn) fn = args => cfn(args, m[2]);
        } else {
            fn = checks[c];
        }
        return [fn, c];
    });
}

async function checkArgs(field) {
    const text = dec.decode(await fromBase64(field.dataset.text));
    return {
        field,
        text,
        role: field.dataset.role,
        answer: field.value,
        solution: text,
        hint: field.dataset.hint,

        apply(fns) {
            for (const [fn, name] of fns) {
                if (!fn) this.invalid = `Unknown check: ${name}`;
                if (this.invalid || this.ok !== undefined) break;
                fn(this);
            }
        },

        applyAS(fn) {
            for (const name of ['answer', 'solution']) {
                const v = this[name];
                if (v === undefined) continue;
                if (v instanceof Array) {
                    this[name] = v.map(v => fn(v));
                } else if (typeof v === 'string') {
                    this[name] = fn(v);
                }
            }
        }
    };
}

const types = {'static': Quiz, 'table': TableGenQuiz};

// Set up quizzes.
const setupDone = domLoaded.then(() => {
    for (const quiz of qsa(document, '.tdoc-quiz')) {
        quiz.tdocQuiz = new types[quiz.dataset.type](quiz);
    }
});
