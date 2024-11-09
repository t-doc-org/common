// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {domLoaded, text, element} from './core.js'
import {addEditor, findEditor} from './editor.js';

// An error that is caused by the user, and that doesn't need to be logged.
export class UserError extends Error {
    toString() { return this.message; }
}

// Walk an {exec} :after: graph and yield nodes in depth-first order. Then walk
// the :after: graph of :then: references. Remove duplicates.
function* walkNodes(node, seen) {
    const isRoot = !seen;
    if (!seen) seen = new Set();
    if (seen.has(node)) return;
    seen.add(node);
    const after = node.dataset.tdocAfter;
    for (const id of after ? after.split(/\s+/) : []) {
        const n = nodeById(id);
        if (!n) {
            console.error(":after: node not found: ${id}");
            continue;
        }
        yield* walkNodes(n, seen);
    }
    yield node;
    if (!isRoot) return;
    const then_ = node.dataset.tdocThen;
    for (const id of then_ ? then_.split(/\s+/) : []) {
        const n = nodeById(id);
        if (!n) {
            console.error(":then: node not found: ${id}");
            continue;
        }
        yield* walkNodes(n, seen);
    }
}

// Return the {exec} node with the given ID.
function nodeById(id) {
    const node = document.getElementById(id);
    if (!node) return;
    if (node.classList.contains('tdoc-exec')) return node;
    return node.parentNode;  // Secondary name as a nested <span>
}

// Move the content of .lineno nodes to the data-n attribute. It is added back
// in CSS, but won't appear in text content.
function fixLineNos(node) {
    for (const ln of node.querySelectorAll('.linenos')) {
        ln.dataset.n = ln.textContent;
        ln.replaceChildren();
    }
}

// A base class for {exec} block handlers.
export class Executor {
    static next_run_id = 0;

    // Apply an {exec} block handler class.
    static async apply(cls) {
        cls.ready = cls.init();  // Initialize concurrently
        await domLoaded;
        for (const node of document.querySelectorAll(
                `div.tdoc-exec.highlight-${cls.lang}`)) {
            fixLineNos(node);
            const handler = new cls(node);
            if (handler.editable) handler.addEditor();
            const controls = element(`<div class="tdoc-exec-controls"></div>`);
            handler.addControls(controls);
            if (controls.children.length > 0) node.appendChild(controls);
            cls.ready.then(() => { handler.onReady(); });

            // Execute immediately if requested.
            if (handler.when === 'load') handler.doRun();  // Don't await
        }
    }

    // Return the text content of the <pre> tag of a node.
    static preText(node) {
        return node.querySelector('pre').textContent;
    }

    // Return the text content of the editor associated with a node if an editor
    // was added, or the content of the <pre> tag.
    static text(node) {
        const [editor, _] = findEditor(node);
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
        const [_, node] = addEditor(this.node.querySelector('div.highlight'), {
            language: this.constructor.lang,
            text: this.origText,
            onRun: this.when !== 'never' ? async () => { await this.doRun(); }
                                         : undefined,
        });
        node.setAttribute('style',
                          this.node.querySelector('pre').getAttribute('style'));
    }

    // Add controls to the {exec} block.
    addControls(controls) {
        if (this.editable && this.origText !== '') {
            controls.appendChild(this.resetControl());
        }
    }

    // Create a "Run" control.
    runControl() {
        const ctrl = element(`\
<button class="fa-play tdoc-run"\
 title="Run${this.editable ? ' (Shift+Enter)' : ''}">\
</button>`);
        ctrl.addEventListener('click', async () => { await this.doRun(); });
        return ctrl;
    }

    // Create a "Stop" control.
    stopControl() {
        const ctrl = element(
            `<button class="fa-stop tdoc-stop" title="Stop"></button>`);
        ctrl.addEventListener('click', async () => { await this.doStop(); });
        return ctrl;
    }

    // Create a "Reset" control.
    resetControl() {
        const ctrl = element(`
<button class="fa-rotate-left tdoc-reset"\
 title="Reset editor content"></button>`);
        ctrl.addEventListener('click', () => {
            const [editor, _] = findEditor(this.node), state = editor.state;
            editor.dispatch(state.update({changes: {
                from: 0, to: state.doc.length,
                insert: this.origText,
            }}));
        });
        return ctrl;
    }

    // Called after init() terminates.
    onReady() {}

    // Called just before run().
    preRun() {}

    // Called just after run().
    postRun() {}

    // Yield the code from the nodes in the :after: chain of the {exec} block.
    *codeBlocks() {
        for (const node of walkNodes(this.node)) {
            yield [Executor.text(node), node];
        }
    }

    // Run the code in the {exec} block.
    async run(run_id) { throw Error("not implemented"); }

    // Stop the running code.
    async stop(run_id) { throw Error("not implemented"); }

    // Run the code in the {exec} block.
    async doRun() {
        await this.constructor.ready;
        while (this.running) await this.doStop();
        const {promise, resolve} = Promise.withResolvers();
        this.running = promise;
        const run_id = this.run_id = Executor.next_run_id;
        Executor.next_run_id = run_id < Number.MAX_SAFE_INTEGER ?
                               run_id + 1 : 0;
        try {
            this.preRun(run_id);
            try {
                await this.run(run_id);
            } finally {
                this.postRun(run_id);
            }
        } catch (e) {
            if (!(e instanceof UserError)) console.error(e);
            this.appendErrorOutput().appendChild(text(` ${e.toString()}`));
        } finally {
            delete this.run_id;
            resolve();
            delete this.running;
        }
    }

    // Stop the code in the {exec} block if it is running.
    async doStop() {
        if (!this.running) return;
        try {
            await this.stop(this.run_id);
        } catch (e) {
            console.error(e);
        } finally {
            if (this.running) await this.running;
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
        prev.after(...outputs);
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

    // Append an error output node associated with the {exec} block.
    appendErrorOutput() {
        const output = element(`\
<div class="tdoc-exec-output tdoc-error"><strong>Error:</strong></div>`);
        this.appendOutputs([output]);
        return output;
    }

    setOutputStyle(el) {
        const style = this.node.dataset.tdocOutputStyle;
        if (style) el.setAttribute('style', style);
    }
}
