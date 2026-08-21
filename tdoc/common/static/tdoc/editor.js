// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import * as api from './api.js';
import {
    autocomplete, collab, commands, language, languages, lint, oneDark, search,
    state, view,
} from './codemirror.js';
import {
    CondVar, Mutex, on, randomId, RateLimited, Stored, toBase64,
} from './core.js';

export {autocomplete, collab, commands, language, lint, search, state, view};

// React to theme changes and update all editor themes as well.
const theme = new state.Compartment();
const lightTheme = view.EditorView.theme({}, {dark: false});
const darkTheme = oneDark;

function currentTheme() {
    return document.documentElement.dataset.theme === 'dark' ?
           darkTheme : lightTheme;
}

document.addEventListener('themechange', e => {
    const curTheme = currentTheme();
    for (const div of document.querySelectorAll('div.cm-editor')) {
        view.EditorView.findFromDOM(div).dispatch(
            {effects: theme.reconfigure(curTheme)});
    }
});

// The default extensions appended to the user-provided ones.
const defaultExtensions = [
    autocomplete.autocompletion({defaultKeymap: false}),
    autocomplete.closeBrackets(),
    commands.history(),
    language.bracketMatching(),
    language.foldGutter(),
    language.indentOnInput(),
    language.indentUnit.of('  '),
    language.syntaxHighlighting(language.defaultHighlightStyle,
                                {fallback: true}),
    search.highlightSelectionMatches(),
    state.EditorState.allowMultipleSelections.of(true),
    state.EditorState.tabSize.of(2),
    view.crosshairCursor(),
    view.drawSelection(),
    view.dropCursor(),
    view.highlightActiveLine(),
    view.highlightActiveLineGutter(),
    view.highlightSpecialChars(),
    view.keymap.of([
        {key: 'Mod-e', run: commands.deleteLine},
        ...autocomplete.closeBracketsKeymap,
        ...autocomplete.completionKeymap.map(
            k => k.key === 'Enter' ? {...k, key: 'Tab'} : k),
        ...commands.defaultKeymap.map(
            k => k.key === 'Home' ? {
                ...k,
                run: commands.cursorLineStart,
                shift: commands.selectLineStart,
            } : k
        ),
        ...commands.historyKeymap,
        commands.indentWithTab,
        ...language.foldKeymap,
        ...lint.lintKeymap,
        ...search.searchKeymap,
    ]),
    view.lineNumbers(),
    view.rectangularSelection(),
    view.EditorView.lineWrapping,
];

// Create a new editor.
export function newEditor(config) {
    if (!config.extensions) config.extensions = [];
    config.extensions.push(
        theme.of(currentTheme()),
        ...defaultExtensions,
    );
    if (config.language) {
        const lang = languages[config.language];
        if (lang) config.extensions.push(lang());
        delete config.language;
    }
    return new view.EditorView(config);
}

// Find an editor in or below the given element. Returns null if no editor is
// found.
export function findEditor(el) {
    const dom = el.querySelector('div.cm-editor');
    return dom ? view.EditorView.findFromDOM(dom) : null;
}

// An array of transactions. Each transaction must be based on the previous
// state; using add() ensures this is the case.
export class Transactions extends Array {
    constructor(state) {
        super();
        this.state = state;
    }

    add(...specs) {
        for (const s of specs) {
            const tr = this.state.update(s);
            this.push(tr);
            this.state = tr.state;
        }
    }
}

// A base class for an editor backend store.
class Store {
    static instances = new Map();
    static ro = new state.Compartment();

    static extensions(plugin) {
        return [this.ro.of(state.EditorState.readOnly.of(true))];
    }

    static define(config) {
        const cls = this;
        return view.ViewPlugin.fromClass(class extends cls {
            static config = config;
        }, {
            eventObservers: {
                blur() { this.storer.flush(); },
            },
            provide(plugin) { return cls.extensions(plugin); },
        });
    }

    get config() { return this.constructor.config; }

    constructor(view) {
        this.view = view;
        this.storer = new RateLimited({min: 1000, max: 5000});
        Store.instances.set(this.config.id, this);
    }

    destroy() {
        this.flush();
        Store.instances.delete(this.config.id);
    }

    update(update) {
        if (!update.docChanged) return;
        for (const tr of update.transactions) {
            if (tr.annotation(state.Transaction.remote)) return;
        }
        this.onLocalChange(update.state.doc);
    }

    schedule(fn) { this.storer.schedule(fn); }
    flush() { this.storer.flush(); }
    status(status, msg) { this.config.onStatus?.(status, msg); }

    setText(text, history = false) {
        return {
            changes: {from: 0, to: this.view.state.doc.length, insert: text},
            annotations: [state.Transaction.remote.of(true),
                          state.Transaction.addToHistory.of(history)],
        };
    }

    readOnly(value) {
        return {
            effects: this.constructor.ro.reconfigure(
                state.EditorState.readOnly.of(value)),
        };
    }
}

// Ensure that the text of editors is stored before navigating away.
on(window).beforeunload(() => {
    for (const store of Store.instances.values()) store.flush();
    // TODO: Ask for confirmation if there are unsaved changes
});

// A backend store using localStorage.
class LocalStore extends Store {
    static prefix = 'tdoc:editor:';

    constructor(view) {
        super(view);
        this.store = new Stored(LocalStore.prefix + this.config.id);
        this.status('local',
                    "The editor content is saved locally in this browser.");
        queueMicrotask(() => {  // State cannot be changed in constructor
            const text = this.store.get();
            this.view.dispatch(text !== undefined ? this.setText(text) : {},
                               this.readOnly(false));
        });
    }

    onLocalChange(doc) {
        this.schedule(() => {
            this.store.set(doc.eq(this.config.initial) ? undefined
                                                       : doc.toString());
        });
    }
}

export function localStore(config) { return LocalStore.define(config); }

// Update the text of editors when their stored content changes.
on(window).storage(e => {
    if (e.storageArea !== localStorage) return;
    if (!e.key.startsWith(LocalStore.prefix)) return;
    const store = Store.instances.get(e.key.slice(LocalStore.prefix.length));
    if (store instanceof LocalStore) {
        store.view.dispatch(store.setText(e.newValue, true));
    }
});

// A collaborative backend store using the API.
class CollabStore extends Store {
    static collab = new state.Compartment();

    static extensions(plugin) {
        return [super.extensions(plugin), this.collab.of([])];
    }

    constructor(view) {
        super(view);
        this.poke = new CondVar();
        this.status('init', "Loading...");
        this.sync();  // Background
    }

    destroy() {
        this._stop = true;
        this.poke.notify();
        super.destroy();
    }

    saved() {
        this.status('saved', "The editor content is saved in the cloud.");
    }

    onLocalChange(doc) {
        this.status('push', "Saving...");
        this.schedule(() => {
            this._push = true;
            this.poke.notify();
        });
    }

    async sync() {
        // Fetch the initial editor text.
        // TODO: Retry on failure
        const version = await this.init();
        this.saved();

        // TODO: Fix inconsistency if two clients have different origText and
        // the store has no text (version = 0)

        // Start the remote watcher.
        let remoteVersion = version;
        this.watch = new api.Watch(
            {name: 'editor', editor: this.config.id},
            data => {
                remoteVersion = data.version;
                this._pull = true;
                this.poke.notify();
            });
        api.events.sub({add: [this.watch]});  // Background

        // Whenever poked, pull remote updates until synchronized, then push
        // if requested. Pushes fail if there are remote updates, so pulling is
        // prioritized.
        try {
            for (;;) {
                await this.poke.wait(
                    () => this._stop || this._pull || this._push);
                if (this._stop) break;

                // Keep pulling as long as there are remote updates.
                this._pull = false;
                let pulled = false;
                for (;;) {
                    const v = collab.getSyncedVersion(this.view.state);
                    if (v === remoteVersion) break;
                    console.debug(`Pulling ${v} => ${remoteVersion}`);
                    // TODO: Retry on failure
                    await this.pull();
                    pulled = true;
                }

                // Push local updates if there are any.
                if (collab.sendableUpdates(this.view.state).length > 0) {
                    if (pulled || this._push) {
                        this._push = false;
                        const st = this.view.state;
                        const v = collab.getSyncedVersion(st);
                        const u = collab.sendableUpdates(st).length;
                        console.log(`Pushing ${v} => ${v + u}`);
                        // TODO: Retry on failure
                        await this.push();
                    }
                } else {
                    this.saved();
                }
            }
        } finally {
            api.events.sub({remove: [this.watch]});  // Background
        }
    }

    async init() {
        const {version, text} = await api.editor({init: this.config.id});
        const trs = new Transactions(this.view.state);
        // This needs to be a separate transaction, otherwise the change is
        // reported to the collab plugin.
        if (text !== null) trs.add(this.setText(state.Text.of(text)));
        trs.add({
            effects: this.constructor.collab.reconfigure(collab.collab({
                startVersion: version, clientID: await randomId(6),
            })),
        }, this.readOnly(false));
        this.view.dispatch(trs);
        return version;
    }

    async pull() {
        const {updates} = await api.editor({
            pull: this.config.id,
            version: collab.getSyncedVersion(this.view.state),
        });
        if (this._stop) return;
        this.view.dispatch(collab.receiveUpdates(
            this.view.state,
            updates.map(u => ({
                clientID: u.i, changes: state.ChangeSet.fromJSON(u.c),
            }))));
    }

    async push() {
        const st = this.view.state;
        const {success} = await api.editor({
            push: this.config.id, version: collab.getSyncedVersion(st),
            updates: collab.sendableUpdates(st).map(u => ({
                i: u.clientID, c: u.changes.toJSON(),
            })),
            text: st.doc.toJSON(),
        });
        return success;
    }
}

export function collabStore(config) { return CollabStore.define(config); }
