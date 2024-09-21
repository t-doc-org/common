// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {addEditor, findEditor} from './tdoc-editor.js';

// Wait for the DOM to be loaded.
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

// Create a text node.
export function text(value) {
    return document.createTextNode(value);
}

// Create an element node.
export function element(html) {
    const t = document.createElement('template');
    t.innerHTML = html.trim();
    return t.content.firstChild;
}

// Walk an {exec} :after: tree and yield nodes in depth-first order with
// duplicates removed.
function* walkAfterTree(node, seen) {
    if (seen.has(node)) return;
    seen.add(node);
    const after = node.dataset.tdocAfter;
    for (const a of after ? after.split(/\s+/) : []) {
        const n = document.getElementById(a);
        if (!n) {
            console.error(":after: node not found: ${a}");
            continue;
        }
        if (!n.classList.contains('tdoc-exec')) {
            n = n.parentNode;  // Secondary name as a nested <span>
        }
        yield* walkAfterTree(n, seen);
    }
    yield node;
}

// A base class for {exec} block handlers.
export class Executor {
    // Return a list of all {exec} blocks with the given handler class.
    static query(cls) {
        return document.querySelectorAll(`div.tdoc-exec.highlight-${cls.lang}`);
    }

    // Apply an {exec} block handler class.
    static async apply(cls) {
        await waitLoaded();
        for (const node of Executor.query(cls)) {
            const handler = node.tdocHandler = new cls(node);
            if (handler.editable) handler.addEditor();
            const controls = element(`<div class="tdoc-exec-controls"></div>`);
            handler.addControls(controls);
            if (controls.children.length > 0) node.appendChild(controls);

            // Execute immediately if requested.
            if (handler.when === 'load') handler.tryRun();  // Don't await
        }
    }

    // Return the text content of the <pre> tag of a node.
    static preText(node) {
        return node.querySelector('pre').textContent;
    }

    // Return the text content of the editor associated with a node, an editor
    // was added, or the content of the <pre> tag.
    static text(node) {
        const editor = findEditor(node);
        return editor ? editor.state.doc.toString() : this.preText(node);
    }

    constructor(node) {
        this.node = node;
        this.editable = node.classList.contains('tdoc-editable');
        this.when = node.dataset.tdocWhen;
        this.origText = Executor.preText(this.node).trim();
    }

    // Add an editor to the {exec} block.
    addEditor() {
        addEditor(this.node.querySelector('div.highlight'), {
            language: this.constructor.lang,
            text: this.origText,
            onRun: this.when !== 'never' ? async () => { await this.tryRun(); }
                                         : undefined,
        });
    }

    // Add controls to the {exec} block.
    addControls(controls) {
        if (this.editable && this.origText !== '') {
            controls.appendChild(this.resetControl());
        }
    }

    runControl() {
        const ctrl = element(`\
<button class="tdoc-exec-run"\
 title="Run${this.editable ? ' (Shift+Enter)' : ''}">\
</button>`);
        ctrl.addEventListener('click', async () => { await this.tryRun(); });
        return ctrl;
    }

    stopControl() {
        const ctrl = element(
            `<button class="tdoc-exec-stop" title="Stop"></button>`);
        ctrl.addEventListener('click', async () => { await this.stop(); });
        return ctrl;
    }

    resetControl() {
        const ctrl = element(
            `<button class="tdoc-exec-reset" title="Reset input"></button>`);
        ctrl.addEventListener('click', () => {
            const editor = findEditor(this.node), state = editor.state;
            editor.dispatch(state.update({changes: {
                from: 0, to: state.doc.length,
                insert: this.origText,
            }}));
        });
        return ctrl;
    }

    // Yield the code from the nodes in the :after: chain of the {exec} block.
    *codeBlocks() {
        for (const node of walkAfterTree(this.node, new Set())) {
            yield [Executor.text(node), node]
        }
    }

    // Run the code in the {exec} block.
    async run() { throw Error("not implemented"); }

    // Stop the running code.
    async stop() { throw Error("not implemented"); }

    // Run the code in the {exec} block. Catch and log exceptions.
    async tryRun() {
        try {
            await this.run();
        } catch (e) {
            console.error(e);
        }
    }

    // Append output nodes associated with the {exec} block.
    appendOutputs(outputs) {
        let prev = this.node;
        for (;;) {
            const next = prev.nextElementSibling;
            if (!next || !next.classList.contains('tdoc-exec-output')) break;
            prev = next;
        }
        prev.after(...out);
    }
    // Replace the output nodes associated with the {exec} block.
    replaceOutputs(outputs) {
        let prev = this.node, i = 0;
        for (;; ++i) {
            const next = prev.nextElementSibling;
            if (!next || !next.classList.contains('tdoc-exec-output')) break;
            if (i < outputs.length) {
                prev = outputs[i];
                next.replaceWith(prev);
            } else {
                next.remove();
            }
        }
        prev.after(...outputs.slice(i));
    }
}
