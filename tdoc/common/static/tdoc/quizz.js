// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {element, focusIfVisible, text} from './core.js';

function find(node, next) {
    let nodes = node.closest('ol, ul')?.querySelectorAll?.('.tdoc-quizz') ?? [];
    const mask = next ? Node.DOCUMENT_POSITION_FOLLOWING :
                        Node.DOCUMENT_POSITION_PRECEDING;
    let found;
    for (const el of nodes) {
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
export function question(node, prompt, check) {
    const div = element(`\
<div class="tdoc-quizz">\
<div class="prompt"></div>\
<div class="input">\
<input autocapitalize="off" autocomplete="off" autocorrect="off"\
 spellcheck="false"><button class="tdoc-check fa-check"></button></div>\
<div class="hint hide"></div>\
</div>`);
    if (prompt) {
        if (typeof prompt === 'string') prompt = text(prompt);
        div.querySelector('.prompt').appendChild(prompt);
    }
    const input = div.querySelector('input');
    const btn = div.querySelector('button');
    const hint = div.querySelector('.hint');
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
    input.addEventListener('input', () => {
        input.parentNode.classList.remove('good', 'bad');
        hint.classList.add('hide');
    });
    input.addEventListener('keydown', (e) => {
        if (e.altKey || e.ctrlKey || e.metaKey) return;
        if (e.key === 'Enter') {
            e.preventDefault();
            if (!checkResp(input.value)) return;
            find(div, true)?.querySelector?.('input')?.focus?.()
        } else if (e.key === 'ArrowUp' && !e.shiftKey) {
            e.preventDefault();
            find(div, false)?.querySelector?.('input')?.focus?.()
        } else if (e.key === 'ArrowDown' && !e.shiftKey) {
            e.preventDefault();
            find(div, true)?.querySelector?.('input')?.focus?.()
        }
    });
    input.addEventListener('blur', () => hint.classList.add('hide'));
    btn.addEventListener('click', () => checkResp(input.value));
    btn.addEventListener('blur', (e) => {
        if (e.relatedTarget !== input) hint.classList.add('hide');
    });
    node.after(div);
    focusIfVisible(input);
    return div;
}
