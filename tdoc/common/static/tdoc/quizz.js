// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {elmt, focusIfVisible, html, on, qs, qsa, text, typesetMath} from './core.js';

function find(node, next) {
    const mask = next ? Node.DOCUMENT_POSITION_FOLLOWING :
                        Node.DOCUMENT_POSITION_PRECEDING;
    let found;
    for (const el of qsa(node.closest('ol, ul'), '.tdoc-quizz')) {
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
    const div = elmt(`\
<div class="tdoc-quizz">\
<div class="prompt"></div>\
<div class="input">\
<input autocapitalize="off" autocomplete="off" autocorrect="off"\
 spellcheck="false"><button class="tdoc-check fa-check"></button></div>\
<div class="hint hide"></div>\
</div>`);
    if (typeof opts === 'string') {
        opts = {prompt: opts ? text(opts) : undefined, math: true};
    }
    let prompt, p = opts?.prompt;
    if (p) {
        if (typeof p === 'string') p = (opts.html ? html : text)(p);
        prompt = qs(div, '.prompt');
        prompt.appendChild(p);
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
