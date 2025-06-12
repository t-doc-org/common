// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {
    dec, domLoaded, elmt, enable, focusIfVisible, fromBase64, html, on, qs, qsa,
    text, typesetMath,
} from './core.js';

function find(node, next) {
    const mask = next ? Node.DOCUMENT_POSITION_FOLLOWING :
                        Node.DOCUMENT_POSITION_PRECEDING;
    let found;
    for (const el of qsa(node.closest('ol, ul'), '.tdoc-jsquizz')) {
        if (node.compareDocumentPosition(el) & mask) {
            if (next) return el;
            found = el;
        } else if (!next) {
            break;
        }
    }
    return found;
}

// Add a quizz question with a reply input field after the given node. Return
// the quizz question container element.
export function question(node, opts, check) {
    const div = elmt`\
<div class="tdoc-jsquizz">\
<div class="prompt"></div>\
<div class="input">\
<input type="text" autocapitalize="off" autocomplete="off" autocorrect="off"\
 spellcheck="false"><button class="tdoc-check fa-check"></button></div>\
<div class="hint hide"></div>\
</div>`;
    if (typeof opts === 'string') {
        opts = {prompt: opts ? text(opts) : undefined, math: true};
    }
    let prompt, p = opts?.prompt;
    if (p) {
        prompt = qs(div, '.prompt');
        prompt.appendChild(typeof p === 'string' ? text(p) : p);
    }
    const input = qs(div, 'input'), btn = qs(div, 'button');
    const hint = qs(div, '.hint');
    function checkResp(resp) {
        input.parentNode.classList.remove('good', 'bad');
        hint.classList.add('hide');
        let res = check(resp);
        input.parentNode.classList.add(res === true ? 'good' : 'bad');
        if (typeof res === 'string' && res !== '') res = text(res);
        if (res instanceof Node) {
            hint.replaceChildren(res);
            hint.classList.remove('hide');
        }
        return res === true;
    }
    on(input).input(() => {
        input.parentNode.classList.remove('good', 'bad');
        hint.classList.add('hide');
    }).keydown(e => {
        if (e.altKey || e.ctrlKey || e.metaKey) return;
        if (e.key === 'Enter') {
            e.preventDefault();
            if (!checkResp(input.value)) return;
            qs(find(div, true), 'input')?.focus?.()
        } else if (e.key === 'ArrowUp' && !e.shiftKey) {
            e.preventDefault();
            qs(find(div, false), 'input')?.focus?.()
        } else if (e.key === 'ArrowDown' && !e.shiftKey) {
            e.preventDefault();
            qs(find(div, true), 'input')?.focus?.()
        }
    }).blur(() => hint.classList.add('hide'));
    on(btn).click(() => checkResp(input.value))
        .blur(e => {
            if (e.relatedTarget !== input) hint.classList.add('hide');
        });
    node.after(div);
    focusIfVisible(input);
    if (prompt && opts.math) typesetMath(prompt);  // Typeset in the background
    return div;
}

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
        const row = elmt`<tr class="tdoc-quizz-row text-center"></tr>`;
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

function setup(quizz) {
    const hint = qs(quizz, '.tdoc-quizz-hint');
    const fields = qsa(quizz, '.tdoc-quizz-field');
    const check = qs(quizz, 'button.tdoc-check');
    for (const field of fields) {
        focusIfVisible(field);
        on(field).keydown(e => {
            if (e.altKey || e.ctrlKey || e.metaKey) return;
            if (e.key === 'Enter') {
                e.preventDefault();
                (nextField(fields, field) || check).focus()
            } else if (e.key === 'ArrowUp' && !e.shiftKey) {
                e.preventDefault();
                prevField(fields, field)?.focus?.()
            } else if (e.key === 'ArrowDown' && !e.shiftKey) {
                e.preventDefault();
                nextField(fields, field)?.focus?.()
            }
        }).blur(e => hint.classList.remove('show'));
    }
    let hintField;
    on(check).click(async () => {
        hint.classList.remove('show');
        let res = true;
        for (const field of fields) {
            const args = await checkAnswer(quizz, field);
            res = res && args.ok;
            field.classList.toggle('bad', !args.ok);
            field.classList.toggle('invalid', !!args.invalid);
            if (!args.ok && args.hint && !hint.classList.contains('show')) {
                hintField = field;
                hint.textContent = args.hint;
                const qr = quizz.getBoundingClientRect();
                const fr = field.getBoundingClientRect();
                const hr = hint.getBoundingClientRect();
                hint.style.top =
                    `calc(${fr.top - qr.top - hr.height}px - 0.5rem)`;
                hint.classList.add('show');
            }
        }
        quizz.classList.toggle('good', res);
        if (res) enable(false, check, ...fields);
    }).blur(e => {
        if (e.relatedTarget !== hintField) hint.classList.remove('show');
    });
    on(qs(quizz, 'button.tdoc-reset')).click(() => {
        quizz.classList.toggle('good', false);
        enable(true, check, ...fields);
        for (const field of fields) field.value = '';
         fields[0].focus();
    });
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

// TODO: Add optional check arguments, e.g. split(,)

export const checks = {
    default(args) {
        checks.trim(args);
        checks.equal(args);
    },
    split(args) {
        args.solution = args.solution.split(',');
    },
    trim(args) {
        args.applyAnsSol(v => v.trim());
    },
    lowercase(args) {
        args.applyAnsSol(v => v.toLowerCase());
    },
    uppercase(args) {
        args.applyAnsSol(v => v.toUpperCase());
    },
    equal(args) {
        args.ok = args.solution instanceof Array ?
                  args.solution.includes(answer) :
                  args.answer === args.solution;
    },
    json(args) {
        args.solution = JSON.parse(solution);
    },
    map(args) {
        const s = args.solution[answer] ?? args.solution[0] ?? false;
        const ts = typeof s;
        if (ts === 'boolean') {
            args.ok = s;
        } else if (ts === 'string') {
            args.hint = s;
        }
    },
    indirect(args) {
        args.apply(checkFns(args.solution));
    }
};

function checkFns(spec) {
    return spec.trim().split(/\s+/).filter(c => c).map(c => checks[c]);
}

async function checkAnswer(quizz, field) {
    const args = {
        field,
        answer: field.value,
        solution: dec.decode(await fromBase64(field.dataset.text)),
        hint: field.dataset.hint,

        apply(fns) {
            for (const fn of fns) {
                if (!fn) this.invalid = true;
                if (this.invalid || this.ok !== undefined) break;
                fn(this);
            }
        },

        applyAnsSol(fn) {
            for (const name of ['answer', 'solution']) {
                const v = this[name];
                if (v === undefined) continue;
                if (v instanceof Array) {
                    this[name] = v.map(v => fn(v));
                } else {
                    this[name] = fn(v);
                }
            }
        }
    };
    args.apply(checkFns(field.dataset.check || 'default'));
    return args;
}

// Set up quizzes.
domLoaded.then(() => {
    for (const quizz of qsa(document, '.tdoc-quizz')) setup(quizz);
});
