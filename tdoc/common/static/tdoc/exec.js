// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {
    asyncProps, elmt, on, qs, qsa, RateLimited, showAlert, Stored, TdocElement,
    text,
} from './core.js';
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
    const after = node.runner.after;
    for (const name of after ? after.split(/\s+/) : []) {
        const n = nodeByName(node.runner.constructor.name, name);
        if (!n) {
            console.error(`:after: node not found: ${name}`);
            continue;
        }
        yield* walkNodes(n, seen);
    }
    yield node;
    if (!isRoot) return;
    const then_ = node.runner.then;
    for (const name of then_ ? then_.split(/\s+/) : []) {
        const n = nodeByName(node.runner.constructor.name, name);
        if (!n) {
            console.error(`:then: node not found: ${name}`);
            continue;
        }
        yield* walkNodes(n, seen);
    }
}

// Return the {exec} node with the given runner and name.
function nodeByName(runner, name) {
    return qs(document, `\
tdoc-exec[runner="${CSS.escape(runner)}"][name="${CSS.escape(name)}"]`)
}

// Move the content of .lineno nodes to the data-n attribute. It is added back
// in CSS, but won't appear in text content.
function fixLineNos(node) {
    for (const ln of qsa(node, '.linenos')) {
        ln.dataset.n = ln.textContent;
        ln.replaceChildren();
    }
}

const storeUpdate = cmstate.Annotation.define();
const editorPrefix = 'tdoc:editor:';

const runners = asyncProps({}, {name: 'exec.runners'});

export class ExecElement extends TdocElement {
    async connectedCallback() {
        try {
            const cls = await runners[this.getAttribute('runner')];
            this.runner = new cls(this);
            await this.runner.init();
            await this._ready();

            // Execute immediately if requested.
            if (this.runner.when === 'load') this.runner.doRun();  // Background
        } catch (e) {
            console.error(e);
            await showAlert(e);
        }
    }
}

customElements.define('tdoc-exec', ExecElement);

// A base class for {exec} block handlers.
export class Runner {
    static next_run_id = 0;

    // Register a runner class.
    static register(cls) {
        cls.ready = cls.init(tdoc.exec?.[cls.name] ?? {});  // Background
        runners[cls.name] = cls;
    }

    // Initialize the runner.
    static async init(config) {}

    constructor(node) { this.node = node; }

    async init() {
        fixLineNos(this.node);
        if (this.editable) this.addEditor();
        const controls = elmt`<div class="tdoc-exec-controls"></div>`;
        this.addControls(controls);
        if (controls.children.length > 0) this.node.appendChild(controls);
        await this.constructor.ready;
        this.onReady();
    }

    attr(name) {
        const v = this.node.getAttribute(name);
        return v !== null ? v : undefined;
    }

    // Attribute accessors.
    get after() { return this.attr('after'); }
    get consoleStyle() { return this.attr('console-style'); }
    get editor() { return this.attr('editor'); }
    get env() { return this.attr('env'); }
    get outputStyle() { return this.attr('output-style'); }
    get reset() { return this.attr('reset'); }
    get then() { return this.attr('then'); }
    get when() { return this.attr('when'); }

    // The configuration for the runner.
    get config() { return tdoc.exec?.[this.constructor.name] ?? {}; }

    // True iff the {exec} block has an editor.
    get editable() { return this.editor !== undefined; }

    // The ID of the editor.
    get editorId() { return this.editor || undefined; }

    // Add an editor to the {exec} block.
    addEditor() {
        const runner = this;
        const extensions = [
            cmview.ViewPlugin.fromClass(class {
                update(update) { return runner.onEditorUpdate(update); }
            }),
        ];
        if (this.when !== 'never') {
            extensions.push(cmview.keymap.of([
                {key: "Shift-Enter", run: () => this.doRun() || true },
            ]));
        }
        const preText = this.preText.trimEnd();
        let doc = preText;
        const editorId = this.editorId;
        if (editorId) {
            this.editorStore = new Stored(editorPrefix + editorId, doc);
            doc = this.editorStore.get();
            this.editorStorer = new RateLimited(5000);
            extensions.push(
                cmview.EditorView.domEventObservers({
                    'blur': () => this.editorStorer.flush(),
                }),
            );
        }
        const view = newEditor({
            extensions, doc,
            language: this.config?.highlight,
            parent: qs(this.node, 'div.highlight'),
        });
        this.origText = view.state.toText(preText);
        view.dom.setAttribute('style',
                              qs(this.node, 'pre').getAttribute('style'));

        const reset = this.reset;
        if (reset === 'show' || (reset === undefined && (preText !== ''))) {
            this.resetEditor = elmt`\
<button class="fa-rotate-left tdoc-reset-editor"\
 title="Reset editor content"></button>`;
            this.resetEditor.disabled = view.state.doc.eq(this.origText);
            on(this.resetEditor).click(() => {
                this.setEditorText(this.origText);
                if (this.editorStorer) this.editorStorer.flush();
            });
        }
    }

    // Handle editor updates.
    onEditorUpdate(update) {
        if (!update.docChanged) return;
        const doc = update.state.doc;
        let isOrig;  // Compute isOrig only if necessary
        if (this.resetEditor) {
            isOrig = doc.eq(this.origText);
            this.resetEditor.disabled = isOrig;
        }
        if (!this.editorStorer) return;
        for (const tr of update.transactions) {
            if (tr.annotation(storeUpdate)) return;
        }
        this.editorStorer.schedule(() => {
            this.editorStore.set(isOrig ?? doc.eq(this.origText) ? undefined
                                 : doc.toString());
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
        if (this.resetEditor) {
            this.resetEditor.disabled = view.state.doc.eq(this.origText);
        }
    }

    // Add controls to the {exec} block.
    addControls(controls) {
        if (this.resetEditor) controls.appendChild(this.resetEditor);
    }

    // Create a "Run" control.
    runControl() {
        const ctrl = elmt`\
<button class="fa-play tdoc-run"\
 title="Run${this.editable ? ' (Shift+Enter)' : ''}">\
</button>`;
        on(ctrl).click(() => this.doRun());
        return ctrl;
    }

    // Create a "Stop" control.
    stopControl() {
        const ctrl =
            elmt`<button class="fa-stop tdoc-stop" title="Stop"></button>`;
        on(ctrl).click(() => this.doStop());
        return ctrl;
    }

    // Called after init() terminates.
    onReady() {}

    // Called just before run().
    preRun() {}

    // Called just after run().
    postRun() {}

    // Return the text content of the <pre> tag.
    get preText() { return qs(this.node, 'pre').textContent; }

    // Return the text content of the editor if an editor was added, or the
    // content of the <pre> tag.
    get text() {
        const view = findEditor(this.node);
        return view ? view.state.doc.toString() : this.preText;
    }

    // Yield the code from the nodes in the :after: and :then: chain of the
    // {exec} block.
    *codeBlocks() {
        for (const node of walkNodes(this.node)) {
            yield {code: node.runner.text, node};
        }
    }

    // Run the code in the {exec} block.
    async run(run_id) { throw new Error("not implemented"); }

    // Stop the running code.
    async stop(run_id) {}

    // Run the code in the {exec} block.
    async doRun() {
        await this.node.ready;
        while (this.running) await this.doStop();
        const {promise, resolve} = Promise.withResolvers();
        this.running = promise;
        const run_id = this.run_id = Runner.next_run_id;
        Runner.next_run_id = run_id < Number.MAX_SAFE_INTEGER ? run_id + 1 : 0;
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

    // Return the block wrapper if there is one, or the node itself if not.
    get wrapper() {
        const parent = this.node.parentNode;
        return parent.classList.contains('literal-block-wrapper') ? parent
                                                                  : this.node;
    }

    // Append output nodes associated with the {exec} block.
    appendOutputs(...outputs) {
        let prev = this.wrapper;
        for (;;) {
            const next = prev.nextElementSibling;
            if (!next || !next.classList.contains('tdoc-exec-output')) break;
            prev = next;
        }
        prev.after(...outputs);
    }

    // Replace the output nodes associated with the {exec} block.
    replaceOutputs(...outputs) {
        let prev = this.wrapper, i = 0;
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
        const output = elmt`\
<div class="tdoc-exec-output tdoc-error"><strong>Error:</strong></div>`;
        this.appendOutputs(output);
        return output;
    }

    setOutputStyle(el) {
        const style = this.outputStyle;
        if (style) el.setAttribute('style', style);
    }

    sectionedOutput() { return new SectionedOutput(this); }
}

class SectionedOutput {
    constructor(runner) { this.runner = runner; }

    remove() {
        if (this.output) this.output.remove();
    }

    render(name, el) {
        el.tdocName = name;
        if (!this.output?.parentNode) {
            this.output =
                elmt`<div class="tdoc-exec-output tdoc-sectioned"></div>`;
            this.runner.appendOutputs(this.output);
        }
        for (const c of this.output.children) {
            if (c.tdocName > name) {
                c.before(el);
                return el;
            }
            if (c.tdocName === name) {
                c.replaceWith(el);
                return el;
            }
        }
        this.output.appendChild(el);
        return el;
    }

    consoleOut(name) { return new ConsoleOut(this, name); }

    input(name, prompt) {
        const div = this.render(name, elmt`<div class="tdoc-input"></div>`);
        if (prompt) {
            div.appendChild(elmt`<div class="prompt">${prompt}</div>`);
        }
        return div;
    }

    lineInput(name, prompt, onSend) {
        const div = this.input(name, prompt);
        const input = div.appendChild(elmt`\
<input type="text" class="input" autocapitalize="off" autocomplete="off"\
 autocorrect="off" spellcheck="false">`);
        const btn = div.appendChild(elmt`\
<button class="tdoc-send" title="Send input (Enter)">Send</button>`);
        on(btn).click(() => onSend(input));
        on(input).keydown(e => {
            if (e.key === 'Enter' && !e.altKey && !e.ctrlKey && !e.metaKey) {
                e.preventDefault();
                btn.click();
            }
        });
        return {div, input};
    }

    multilineInput(name, prompt, onSend) {
        const div = this.input(name, prompt);
        const input = qs(div.appendChild(elmt`\
<div class="input tdoc-autosize">\
<textarea rows="1" autocapitalize="off" autocomplete="off"\
 autocorrect="off" spellcheck="false"\
 oninput="this.parentNode.dataset.text = this.value"></textarea>\
</div>`), 'textarea');
        const btn = div.appendChild(elmt`\
<button class="tdoc-send" title="Send input (Shift+Enter)">Send</button>`);
        on(btn).click(() => onSend(input));
        on(input).keydown(e => {
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
    constructor(output, name) {
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
                    qs(this.out, 'pre').replaceChildren();
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
                this.name,
                elmt`<div class="tdoc-console highlight"><pre></pre></div>`);
            on(div.appendChild(elmt`\
<button class="fa-xmark tdoc-remove" title="Remove"></button>`))
                .click(() => div.remove());
            const style = this.output.runner.consoleStyle;
            if (style) qs(div, 'pre').setAttribute('style', style);
        }
        const out = qs(this.out, 'pre');

        // Append the text and scroll if at the bottom.
        let node = text(data);
        if (stream) {
            const el = elmt`<span class="${stream}"></span>`;
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
on(window).beforeunload(() => {
    for (const node of qsa(document, 'tdoc-exec[editor]')) {
        const storer = node.runner.editorStorer;
        if (storer) storer.flush();
    }
});

// Update the text of editors when their stored content changes.
on(window).storage(e => {
    if (e.storageArea !== localStorage) return;
    if (!e.key.startsWith(editorPrefix)) return;
    const name = e.key.slice(editorPrefix.length);
    const node = qs(document, `tdoc-exec[editor="${CSS.escape(name)}"]`);
    if (!node) return;
    node.runner.setEditorText(e.newValue, [storeUpdate.of(true)]);
});
