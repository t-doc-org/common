// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {element, focusIfVisible, text} from './core.js';

// Add a quizz question with a reply input field after the given node. Return
// the quizz question container element.
export function question(node, prompt, check) {
    const div = element(`\
<div class="tdoc-quizz">\
<div class="prompt"></div>\
<div class="input">\
<input autocapitalize="off" autocomplete="off" autocorrect="off"\
 spellcheck="false"><button class="tdoc-check fa-check"></button></div>\
</div>`);
    if (prompt) {
        if (typeof prompt === 'string') prompt = text(prompt);
        div.querySelector('.prompt').appendChild(prompt);
    }
    const input = div.querySelector('input');
    const btn = div.querySelector('button');
    function checkResp(resp) {
        input.parentNode.classList.remove('good', 'bad');
        input.parentNode.classList.add(check(resp) ? 'good' : 'bad');
    }
    input.addEventListener('input', () => {
        input.parentNode.classList.remove('good', 'bad');
    });
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.altKey && !e.ctrlKey && !e.metaKey) {
            e.preventDefault();
            btn.click();
        }
    });
    btn.addEventListener('click', () => { checkResp(input.value); });
    node.after(div);
    focusIfVisible(input);
    return div;
}
