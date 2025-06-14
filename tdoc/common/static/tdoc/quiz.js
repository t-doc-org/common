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
    for (const el of qsa(node.closest('ol, ul'), '.tdoc-jsquiz')) {
        if (node.compareDocumentPosition(el) & mask) {
            if (next) return el;
            found = el;
        } else if (!next) {
            break;
        }
    }
    return found;
}

// Add a quiz question with a reply input field after the given node. Return
// the quiz question container element.
export function question(node, opts, check) {
    const div = elmt`\
<div class="tdoc-jsquiz">\
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

function setup(quiz) {
    const hint = qs(quiz, '.tdoc-quiz-hint');
    let hintField;

    function showHint(field, text, invalid = false) {
        hintField = field;
        hint.textContent = text;
        const qr = quiz.getBoundingClientRect();
        const fr = field.getBoundingClientRect();
        const hr = hint.getBoundingClientRect();
        hint.style.top = `calc(${fr.top - qr.top - hr.height}px - 0.5rem)`;
        hint.classList.toggle('invalid', invalid);
        hint.classList.add('show');
    }

    const fields = qsa(quiz, '.tdoc-quiz-field');
    const check = qs(quiz, 'button.tdoc-check');
    for (const field of fields) {
        focusIfVisible(field);
        on(field).blur(e => hint.classList.remove('show'));
        if (field instanceof HTMLInputElement && field.type === 'text') {
            on(field).keydown(e => {
                if (e.altKey || e.ctrlKey || e.metaKey) return;
                if (e.key === 'Enter') {
                    e.preventDefault();
                    (nextField(fields, field) || check).focus()
                    if (e.shiftKey) check.click();
                } else if (e.key === 'ArrowUp' && !e.shiftKey) {
                    e.preventDefault();
                    prevField(fields, field)?.focus?.()
                } else if (e.key === 'ArrowDown' && !e.shiftKey) {
                    e.preventDefault();
                    nextField(fields, field)?.focus?.()
                }
            })
        }
    }

    on(check).click(async () => {
        hint.classList.remove('show');
        let res = true;
        for (const field of fields) {
            const args = await checkAnswer(quiz, field);
            const ok = !args.invalid && args.ok;
            if (res && !ok) field.focus();
            res = res && ok;
            field.classList.toggle('bad', !ok);
            if (!hint.classList.contains('show')) {
                if (args.invalid) {
                    showHint(field, args.invalid, true);
                } else if (!args.ok && args.hint) {
                    showHint(field, args.hint);
                }
            }
        }
        quiz.classList.toggle('good', res);
        if (res) enable(false, check, ...fields);
    }).blur(e => {
        if (e.relatedTarget !== hintField) hint.classList.remove('show');
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

export const checks = {
    default(args) { checks.trim(args); },
    split(args) { args.solution = args.solution.split(','); },
    trim(args) { args.applyAS(v => v.trim()); },
    'remove-whitespace': (args) => {
        args.applyAS(v => v.replaceAll(/\s+/g, ''));
    },
    lowercase(args) { args.applyAS(v => v.toLowerCase()); },
    uppercase(args) { args.applyAS(v => v.toUpperCase()); },
    json(args) { args.solution = JSON.parse(args.solution); },
    indirect(args) { args.apply(checkFns(args.solution)); },
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

function checkFns(spec) {
    return spec.trim().split(/\s+/).filter(c => c).map(c => [checks[c], c]);
}

async function checkAnswer(quiz, field) {
    const args = {
        field,
        role: field.dataset.role,
        answer: field.value,
        solution: dec.decode(await fromBase64(field.dataset.text)),
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
    args.apply(checkFns((field.dataset.check || 'default') + ' equal'));
    return args;
}

// Set up quizzes.
domLoaded.then(() => {
    for (const quiz of qsa(document, '.tdoc-quiz')) setup(quiz);
});
