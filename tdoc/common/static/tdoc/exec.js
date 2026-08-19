// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import * as api from './api.js';
import {
    asyncProps, elmt, isVisible, Mutex, on, qs, qsa, RateLimited, showAlert,
    Stored, TdocElement, text, toBase64,
} from './core.js';
import {
    collab as cmcollab, state as cmstate, view as cmview, findEditor, newEditor,
} from './editor.js';

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

const editorPrefix = 'tdoc:editor:';

// TODO: Make stores ViewPlugins, so that they get reset when setting the state?

class Store {
    constructor(id, initial) {
        this.id = id;
        this.initial = initial;
        // TODO: Add an idle duration (=> min & max intervals)
        this.storer = new RateLimited(this.constructor.interval);
    }

    async init(config) {
        config.extensions.push(
            cmview.EditorView.updateListener.of(u => this.onUpdate(u)),
            cmview.EditorView.domEventObservers({
                blur: () => this.storer.flush(),
            }),
        );
    }

    start(view) {}
    schedule(fn) { this.storer.schedule(fn); }
    flush() { this.storer.flush(); }
    onUpdate(update) {}
}

// Ensure that the text of editors is stored before navigating away.
on(window).beforeunload(() => {
    for (const node of qsa(document, 'tdoc-exec[editor]')) {
        const store = node.runner.store;
        if (store) store.flush();
    }
    // TODO: Ask for confirmation if there are unsaved changes
});

class LocalStore extends Store {
    static interval = 5000;

    async init(config) {
        await super.init(config);
        this.store = new Stored(editorPrefix + this.id);
        const text = this.store.get();
        if (text !== undefined) config.doc = text;
    }

    onUpdate(update) {
        if (!update.docChanged) return;
        for (const tr of update.transactions) {
            if (tr.annotation(cmstate.Transaction.remote)) return;
        }
        const doc = update.state.doc;
        this.schedule(() => {
            this.store.set(doc.eq(this.initial) ? undefined : doc.toString());
        });
    }

    onStorageUpdate(text, view) {
        const state = view.state;
        view.dispatch(state.update({
            changes: {from: 0, to: state.doc.length, insert: text},
            annotations: cmstate.Transaction.remote.of(true),
        }));
    }
}

// Update the text of editors when their stored content changes.
on(window).storage(e => {
    if (e.storageArea !== localStorage) return;
    if (!e.key.startsWith(editorPrefix)) return;
    const name = e.key.slice(editorPrefix.length);
    const node = qs(document, `tdoc-exec[editor="${CSS.escape(name)}"]`);
    const runner = node?.runner;
    if (!runner) return;
    const store = runner.store;
    if (store instanceof LocalStore) {
        store.onStorageUpdate(e.newValue, runner.editorView);
    }
});

class CollabStore extends Store {
    static interval = 1000;
    static clientId;

    async init(config) {
        await super.init(config);
        if (!this.constructor.clientId) {
            this.constructor.clientId = await toBase64(
                crypto.getRandomValues(new Uint8Array(6)));
        }
        const {version, text} = await api.editor({init: this.id});
        // TODO: Set readonly with message if request fails, and retry
        // TODO: Fix inconsistency if two clients have different origText and
        // the store has no text (version = 0)
        if (text !== null) config.doc = cmstate.Text.of(text);
        this.mu = new Mutex();
        config.extensions.push(
            cmcollab.collab({
                startVersion: version,
                clientID: this.constructor.clientId,
            }),
        );
    }

    start(view) {
        this.watch = new api.Watch({name: 'editor', editor: this.id},
                                   data => this.onRemoteUpdate(data, view));
        api.events.sub({add: [this.watch]});  // Background
    }

    onUpdate(update) {
        if (!update.docChanged) return;
        this.schedulePush(update.view);
    }

    async onRemoteUpdate(data, view) {
        const version = cmcollab.getSyncedVersion(view.state);
        if (data.version === version) return;
        console.log(`Remote update: ${version} => ${data.version}`);
        if (data.version < version) {
            // TODO: Show message, recommend copying text and reloading
            console.warn(`\
Remote version (${data.version}) < synced version (${version})`);
            return;
        }
        // TODO: Pull in the background
        const {updates} = await api.editor({pull: this.id, version});
        view.dispatch(cmcollab.receiveUpdates(view.state, updates.map(u => ({
            clientID: u.i, changes: cmstate.ChangeSet.fromJSON(u.c),
        }))));
        if (cmcollab.sendableUpdates(view.state).length > 0) {
            this.schedulePush();
        }
    }

    schedulePush(view) { this.schedule(() => this.push(view)); }

    async push(view) {
        await this.mu.locked(async () => {
            const state = view.state;
            const updates = cmcollab.sendableUpdates(state);
            if (updates.length === 0) return;
            console.log(`Pushing ${updates.length} updates`);
            // TODO: Handle request failures => retry with backoff
            const {success} = await api.editor({
                push: this.id, version: cmcollab.getSyncedVersion(state),
                updates: updates.map(u => ({
                    i: u.clientID, c: u.changes.toJSON(),
                })),
                text: state.doc.toJSON(),
            });
            console.log(`Push result: ${success}`);
        });
    }
}

const runners = asyncProps({}, {name: 'exec.runners'});

export class ExecElement extends TdocElement {
    async onInit() {
        try {
            const cls = await runners[this.getAttribute('runner')];
            this.runner = new cls(this);
            await this.runner.init();
            await this._ready();

            // Execute immediately if requested.
            if (this.runner.when.includes('load')) this.runner.doRun();  // BG
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
        if (this.editable) await this.addEditor();
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

    get when() {
        const v = this.attr('when');
        return v ? v.split(' ') : [];
    }

    // The configuration for the runner.
    get config() { return tdoc.exec?.[this.constructor.name] ?? {}; }

    // True iff the {exec} block has an editor.
    get editable() { return this.editor !== undefined; }

    // The ID of the editor.
    get editorId() { return this.editor || undefined; }

    // Add an editor to the {exec} block.
    async addEditor() {
        this.origText = cmstate.Text.of(
            this.preText.trimEnd().split(/\r\n?|\n/));
        const runner = this;
        const config = {
            extensions: [],
            doc: this.origText,
            language: this.config?.highlight,
            parent: qs(this.node, 'div.highlight'),
        };
        if (this.when.includes('click')) {
            config.extensions.push(cmview.keymap.of([
                {key: "Shift-Enter", run: () => this.doRun() || true },
            ]));
        }

        // Set up the editor store.
        if (this.editorId) {
            if (await api.auth.name() === undefined
                    || !this.node.classList.contains('collab')) {
                this.store = new LocalStore(this.editorId, this.origText);
            } else {
                this.store = new CollabStore(this.editorId, this.origText);
            }
            await this.store.init(config);
        }

        // Set up the reset button.
        const reset = this.reset;
        if (reset === 'show' ||
                (reset === 'auto' && !this.origText.eq(cmstate.Text.empty))) {
            const btn = this.resetEditor = elmt`\
<button class="fa-rotate-left tdoc-reset-editor"\
 title="Reset editor content"></button>`;
            on(btn).click(() => {
                this.setEditorText(this.origText);
                if (this.store) this.store.flush();
            });
            config.extensions.push(cmview.EditorView.updateListener.of(u => {
                if (!u.docChanged) return;
                btn.disabled = u.state.doc.eq(this.origText);
            }));
        }

        // Create the editor.
        config.extensions.push(...this.editorExtensions);
        const view = newEditor(config);
        view.dom.setAttribute('style',
                              qs(this.node, 'pre').getAttribute('style'));
        if (this.resetEditor) {
            this.resetEditor.disabled = view.state.doc.eq(this.origText);
        }
        if (this.store) this.store.start(view);
    }

    get editorExtensions() { return []; }

    // Return the EditorView object.
    get editorView() { return findEditor(this.node); }

    // Dispatch a transaction that updates the editor state.
    updateEditorState(fn) {
        const view = this.editorView, state = view.state;
        let specs = fn(state);
        if (!Array.isArray(specs)) specs = [specs];
        view.dispatch(state.update(...specs));
    }

    // Replace the text of the editor, attaching the given annotations to the
    // transaction.
    setEditorText(text, annotations) {
        this.updateEditorState(state => {
            return {changes: {from: 0, to: state.doc.length, insert: text},
                    annotations};
        });
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

    // Return true iff a run control is available to the user.
    hasRunControl() {
        const el = qs(this.node, '.tdoc-run');
        // Check visibility of the parent, as the run control itself may be
        // temporarily hidden (e.g. replaced by the stop control).
        return el && isVisible(el.parentNode);
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
        const view = this.editorView;
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
        this.addOutputRemove(output);
        this.appendOutputs(output);
        return output;
    }

    setOutputStyle(el) {
        const style = this.outputStyle;
        if (style) el.setAttribute('style', style);
    }

    sectionedOutput() { return new SectionedOutput(this); }

    // Add a "Remove" control to allow the user to remove generated output.
    addOutputRemove(output, parent = output) {
        if (this.hasRunControl()) {
            on(parent.appendChild(elmt`\
<button class="fa-xmark tdoc-remove" title="Remove"></button>`))
                .click(() => output.remove());
        }
    }
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
            this.output.runner.addOutputRemove(div);
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
