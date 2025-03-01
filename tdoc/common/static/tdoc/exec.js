// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {domLoaded, element, RateLimited, rootUrl, text} from './core.js';
import {cmstate, cmview, findEditor, newEditor} from './editor.js';

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
            console.error(`:after: node not found: ${id}`);
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
            console.error(`:then: node not found: ${id}`);
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

const storeUpdate = cmstate.Annotation.define();
const editorPrefix = `tdoc:editor:${rootUrl.pathname}:`;

// A base class for {exec} block handlers.
export class Executor {
    static next_run_id = 0;

    // Apply an {exec} block handler class.
    static async apply(cls) {
        cls.ready = cls.init();  // Initialize concurrently
        await domLoaded;
        for (const node of document.querySelectorAll(
                `div.tdoc-exec-runner-${cls.runner}`)) {
            fixLineNos(node);
            const handler = new cls(node);
            node.tdocExec = handler;
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
        const view = findEditor(node);
        return view ? view.state.doc.toString() : this.preText(node);
    }

    constructor(node) {
        this.node = node;
        this.when = node.dataset.tdocWhen;
        this.origText = Executor.preText(this.node).trim();
    }

    // True iff the {exec} block has an editor.
    get editable() { return this.node.dataset.tdocEditor !== undefined; }

    // The name of the local storage key for the editor content.
    get editorKey() {
        const editor = this.node.dataset.tdocEditor;
        return editor ? editorPrefix + editor : undefined;
    }

    // Add an editor to the {exec} block.
    addEditor() {
        const extensions = [];
        if (this.when !== 'never') {
            extensions.push(cmview.keymap.of([
                {key: "Shift-Enter", run: () => this.doRun() || true },
            ]));
        }
        let doc = this.origText;
        const key = this.editorKey;
        if (key) {
            const st = localStorage.getItem(key);
            if (st !== null) doc = st;
            this.storeEditor = new RateLimited(5000);
            const exec = this;
            extensions.push(
                cmview.ViewPlugin.fromClass(class {
                    update(update) { return exec.onEditorUpdate(update); }
                }),
                cmview.EditorView.domEventObservers({
                    'blur': () => this.storeEditor.flush(),
                }),
            );
        }
        const view = newEditor({
            extensions, doc,
            language: this.constructor.highlight,
            parent: this.node.querySelector('div.highlight'),
        });
        view.dom.setAttribute(
            'style', this.node.querySelector('pre').getAttribute('style'));
    }

    // Called on every editor update.
    onEditorUpdate(update) {
        if (!update.docChanged) return;
        for (const tr of update.transactions) {
            if (tr.annotation(storeUpdate)) return;
        }
        const doc = update.state.doc;
        this.storeEditor.schedule(() => {
            const txt = doc.toString();
            if (txt !== this.origText) {
                localStorage.setItem(this.editorKey, txt);
            } else {
                localStorage.removeItem(this.editorKey);
            }
        });
    }

    // Replace the text of the editor, attaching the given annotations to the
    // transaction.
    setEditorText(text, annotations) {
        const view = findEditor(this.node)
        if (!view) return;
        view.dispatch(view.state.update({
            changes: {from: 0, to: view.state.doc.length, insert: text},
            annotations,
        }));
    }

    // Add controls to the {exec} block.
    addControls(controls) {
        if (this.editable && this.origText !== '') {
            controls.appendChild(this.resetEditorControl());
        }
    }

    // Create a "Run" control.
    runControl() {
        const ctrl = element(`\
<button class="fa-play tdoc-run"\
 title="Run${this.editable ? ' (Shift+Enter)' : ''}">\
</button>`);
        ctrl.addEventListener('click', () => this.doRun());
        return ctrl;
    }

    // Create a "Stop" control.
    stopControl() {
        const ctrl = element(
            `<button class="fa-stop tdoc-stop" title="Stop"></button>`);
        ctrl.addEventListener('click', () => this.doStop());
        return ctrl;
    }

    // Create a "Reset" control.
    resetEditorControl() {
        const ctrl = element(`
<button class="fa-rotate-left tdoc-reset-editor"\
 title="Reset editor content"></button>`);
        ctrl.addEventListener('click', () => this.setEditorText(this.origText));
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
            yield {code: Executor.text(node), node};
        }
    }

    // Run the code in the {exec} block.
    async run(run_id) { throw new Error("not implemented"); }

    // Stop the running code.
    async stop(run_id) { throw new Error("not implemented"); }

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
    appendOutputs(...outputs) {
        let prev = this.node;
        for (;;) {
            const next = prev.nextElementSibling;
            if (!next || !next.classList.contains('tdoc-exec-output')) break;
            prev = next;
        }
        prev.after(...outputs);
    }

    // Replace the output nodes associated with the {exec} block.
    replaceOutputs(...outputs) {
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
        this.appendOutputs(output);
        return output;
    }

    setOutputStyle(el) {
        const style = this.node.dataset.tdocOutputStyle;
        if (style) el.setAttribute('style', style);
    }

    sectionedOutput() { return new SectionedOutput(this); }
}

class SectionedOutput {
    constructor(exec) { this.exec = exec; }

    remove() {
        if (this.output) this.output.remove();
    }

    render(name, html) {
        const new_el = element(html);
        new_el.tdocName = name;
        if (!this.output?.parentNode) {
            this.output = element(
                `<div class="tdoc-exec-output tdoc-sectioned"></div>`);
            this.exec.appendOutputs(this.output);
        }
        for (const el of this.output.children) {
            if (el.tdocName > name) {
                el.before(new_el);
                return new_el;
            }
            if (el.tdocName === name) {
                el.replaceWith(new_el);
                return new_el;
            }
        }
        this.output.appendChild(new_el);
        return new_el;
    }

    consoleOut(name) { return new ConsoleOut(this, name); }

    input(name, prompt) {
        const div = this.render(name, `<div class="tdoc-input"></div>`);
        if (prompt) {
            div.appendChild(element(`<div class="prompt"></div>`))
                .appendChild(text(prompt));
        }
        return div;
    }

    lineInput(name, prompt, onSend) {
        const div = this.input(name, prompt);
        const input = div.appendChild(element(`\
<input class="input" autocapitalize="off" autocomplete="off"\
 autocorrect="off" spellcheck="false">`));
        const btn = div.appendChild(element(`\
<button class="tdoc-send" title="Send input (Enter)">Send</button>`));
        btn.addEventListener('click', () => onSend(input));
        input.addEventListener('keydown', e => {
            if (e.key === 'Enter' && !e.altKey && !e.ctrlKey && !e.metaKey) {
                e.preventDefault();
                btn.click();
            }
        });
        return {div, input};
    }

    multilineInput(name, prompt, onSend) {
        const div = this.input(name, prompt);
        const input = div.appendChild(element(`\
<div class="input tdoc-autosize">\
<textarea rows="1" autocapitalize="off" autocomplete="off"\
 autocorrect="off" spellcheck="false"\
 oninput="this.parentNode.dataset.text = this.value"></textarea>\
</div>`))
            .querySelector('textarea');
        const btn = div.appendChild(element(`\
<button class="tdoc-send" title="Send input (Shift+Enter)">Send</button>`));
        btn.addEventListener('click', () => onSend(input));
        input.addEventListener('keydown', e => {
            if (e.key === 'Enter' && e.shiftKey && !e.altKey &&
                    !e.ctrlKey && !e.metaKey) {
                e.preventDefault();
                btn.click();
            }
        });
        return {div, input};
    }
}

const form_feed = '\x0c';

class ConsoleOut {
    constructor(output) {
        this.output = output;
        this.name = name;
        this.decoders = new Map();
    }

    clear() {
        if (!this.out) return;
        this.out.remove();
        delete this.out;
        this.decoders.clear();
    }

    write(stream, data, done) {
        // Convert to string if necessary.
        if (typeof data !== 'string') {
            let dec = this.decoders.get(stream);
            if (!dec) {
                dec = new TextDecoder();
                this.decoders.set(stream, dec);
            }
            data = dec.decode(data, {stream: !done});
        }

        // Handle form feed characters by clearing the output.
        const i = data.lastIndexOf(form_feed);
        if (i >= 0) {
            data = data.slice(i + 1);
            if (this.out) {
                if (data.length > 0) {
                    this.out.querySelector('pre').replaceChildren();
                } else {
                    this.out.remove();
                    delete this.out;
                }
            }
        }

        // Create the output node if necessary.
        if (data.length === 0) return;
        if (!this.out?.isConnected) {
            const div = this.out = this.output.render(
                this.name, `<div class="highlight"><pre></pre></div>`);
            div.appendChild(element(`\
<button class="fa-xmark tdoc-remove" title="Remove"></button>`))
                .addEventListener('click', () => div.remove());
            const pre = div.querySelector('pre');
            this.output.exec.setOutputStyle(pre);
        }
        const out = this.out.querySelector('pre');

        // Append the text and scroll if at the bottom.
        let node = text(data);
        if (stream) {
            const el = element(`<span class="${stream}"></span>`);
            el.appendChild(node);
            node = el;
        }
        const atBottom = Math.abs(
            out.scrollHeight - out.scrollTop - out.clientHeight) <= 1;
        out.appendChild(node);
        if (atBottom) out.scrollTo(out.scrollLeft, out.scrollHeight);
    }
}

// Ensure that the text of editors is stored before navigating away.
addEventListener('beforeunload', () => {
    for (const node of document.querySelectorAll(
            'div.tdoc-exec[data-tdoc-editor]')) {
        const storer = node.tdocExec.storeEditor;
        if (storer) storer.flush();
    }
});

// Update the text of editors when their stored content changes.
addEventListener('storage', e => {
    if (e.storageArea !== localStorage) return;
    if (!e.key.startsWith(editorPrefix)) return;
    const name = e.key.slice(editorPrefix.length);
    const node = document.querySelector(
        `div.tdoc-exec[data-tdoc-editor="${CSS.escape(name)}"]`);
    if (!node) return;
    node.tdocExec.setEditorText(e.newValue, [storeUpdate.of(true)]);
});
