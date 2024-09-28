// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {addEditor, findEditor} from './tdoc-editor.js';

// Resolves when the DOM content has loaded and deferred scripts have executed.
const loaded = new Promise(resolve => {
    if (document.readyState !== 'loading') {
        resolve();
    } else {
        document.addEventListener('DOMContentLoaded', resolve);
    }
});

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

// Return a promise and its resolve and reject functions.
export function signal() {
    let resolve, reject;
    const promise = new Promise((res, rej) => { resolve = res; reject = rej; });
    return {promise, resolve, reject};
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

// An error that is caused by the user, and that doesn't need to be logged.
export class UserError extends Error {
    toString() { return this.message; }
}

// A base class for {exec} block handlers.
export class Executor {
    static next_run_id = 0;

    // Apply an {exec} block handler class.
    static async apply(cls) {
        cls.ready = cls.init();  // Initialize concurrently
        await loaded;
        for (const node of document.querySelectorAll(
                `div.tdoc-exec.highlight-${cls.lang}`)) {
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
            onRun: this.when !== 'never' ? async () => { await this.doRun(); }
                                         : undefined,
        });
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
<button class="fa-play" title="Run${this.editable ? ' (Shift+Enter)' : ''}">\
</button>`);
        ctrl.addEventListener('click', async () => { await this.doRun(); });
        return ctrl;
    }

    // Create a "Stop" control.
    stopControl() {
        const ctrl = element(
            `<button class="fa-stop" title="Stop"></button>`);
        ctrl.addEventListener('click', async () => { await this.doStop(); });
        return ctrl;
    }

    // Create a "Reset" control.
    resetControl() {
        const ctrl = element(
            `<button class="fa-rotate-left" title="Reset input"></button>`);
        ctrl.addEventListener('click', () => {
            const editor = findEditor(this.node), state = editor.state;
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
        for (const node of walkAfterTree(this.node, new Set())) {
            yield [Executor.text(node), node]
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
}

// Prevent doctools.js from capturing editor key events, in case keyboard
// shortcuts are enabled.
await loaded;
if (typeof BLACKLISTED_KEY_CONTROL_ELEMENTS !== 'undefined') {
    BLACKLISTED_KEY_CONTROL_ELEMENTS.add('DIV');
}
