// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import * as api from './api.js';
import * as cm from './codemirror.js';
import * as core from './core.js';
const {on} = core;

// React to theme changes and update all editor themes as well.
const theme = new cm.state.Compartment();
const lightTheme = cm.view.EditorView.theme({}, {dark: false});
const darkTheme = cm.oneDark;

function currentTheme() {
    return document.documentElement.dataset.theme === 'dark' ?
           darkTheme : lightTheme;
}

document.addEventListener('themechange', e => {
    const curTheme = currentTheme();
    for (const div of document.querySelectorAll('div.cm-editor')) {
        cm.view.EditorView.findFromDOM(div).dispatch(
            {effects: theme.reconfigure(curTheme)});
    }
});

// The default extensions appended to the user-provided ones.
const defaultExtensions = [
    cm.autocomplete.autocompletion({defaultKeymap: false}),
    cm.autocomplete.closeBrackets(),
    cm.commands.history(),
    cm.language.bracketMatching(),
    cm.language.foldGutter(),
    cm.language.indentOnInput(),
    cm.language.indentUnit.of('  '),
    cm.language.syntaxHighlighting(cm.language.defaultHighlightStyle,
                                   {fallback: true}),
    cm.search.highlightSelectionMatches(),
    cm.state.EditorState.allowMultipleSelections.of(true),
    cm.state.EditorState.tabSize.of(2),
    cm.view.crosshairCursor(),
    cm.view.drawSelection(),
    cm.view.dropCursor(),
    cm.view.highlightActiveLine(),
    cm.view.highlightActiveLineGutter(),
    cm.view.highlightSpecialChars(),
    cm.view.keymap.of([
        {key: 'Mod-e', run: cm.commands.deleteLine},
        ...cm.autocomplete.closeBracketsKeymap,
        ...cm.autocomplete.completionKeymap.map(
            k => k.key === 'Enter' ? {...k, key: 'Tab'} : k),
        ...cm.commands.defaultKeymap.map(
            k => k.key === 'Home' ? {
                ...k,
                run: cm.commands.cursorLineStart,
                shift: cm.commands.selectLineStart,
            } : k
        ),
        ...cm.commands.historyKeymap,
        cm.commands.indentWithTab,
        ...cm.language.foldKeymap,
        ...cm.lint.lintKeymap,
        ...cm.search.searchKeymap,
    ]),
    cm.view.lineNumbers(),
    cm.view.rectangularSelection(),
    cm.view.EditorView.lineWrapping,
];

// Create a new editor.
export function create(config) {
    if (!config.extensions) config.extensions = [];
    config.extensions.push(
        theme.of(currentTheme()),
        ...defaultExtensions,
    );
    if (config.language) {
        const lang = cm.languages[config.language];
        if (lang) config.extensions.push(lang());
        delete config.language;
    }
    return new cm.view.EditorView(config);
}

// Find an editor in or below the given element. Returns null if no editor is
// found.
export function find(el) {
    const dom = el.querySelector('div.cm-editor');
    return dom ? cm.view.EditorView.findFromDOM(dom) : null;
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
    static ro = new cm.state.Compartment();

    static extensions(plugin) {
        return [this.ro.of(cm.state.EditorState.readOnly.of(true))];
    }

    static define(config) {
        const cls = this;
        return cm.view.ViewPlugin.fromClass(class extends cls {
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
        this.storer = new core.RateLimited({min: 1000, max: 5000});
        Store.instances.set(this.config.id, this);
    }

    destroy() {
        this.flush();
        Store.instances.delete(this.config.id);
    }

    update(update) {
        if (!update.docChanged) return;
        for (const tr of update.transactions) {
            if (tr.annotation(cm.state.Transaction.remote)) return;
        }
        this.onLocalChange(update.state.doc);
    }

    schedule(fn) { this.storer.schedule(fn); }
    flush() { this.storer.flush(); }
    status(status, msg) { this.config.onStatus?.(status, msg); }

    setText(text, history = false) {
        return {
            changes: {from: 0, to: this.view.state.doc.length, insert: text},
            annotations: [cm.state.Transaction.remote.of(true),
                          cm.state.Transaction.addToHistory.of(history)],
        };
    }

    readOnly(value) {
        return {
            effects: this.constructor.ro.reconfigure(
                cm.state.EditorState.readOnly.of(value)),
        };
    }
}

// Ensure that the text of editors is stored before navigating away.
// TODO: Flush in visibilitychange, block in beforeunload
// TODO: Use "keepalive: true" for push request when flushing
on(window).beforeunload(() => {
    for (const store of Store.instances.values()) store.flush();
    // TODO: Ask for confirmation if there are unsaved changes
});

// A backend store using localStorage.
class LocalStore extends Store {
    static prefix = 'tdoc:editor:';

    constructor(view) {
        super(view);
        this.store = new core.Stored(LocalStore.prefix + this.config.id);
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

const backoffCfg = {min: 1000, max: 10000};

// A collaborative backend store using the API.
class CollabStore extends Store {
    static collab = new cm.state.Compartment();

    static extensions(plugin) {
        return [super.extensions(plugin), this.collab.of([])];
    }

    constructor(view) {
        super(view);
        this.poke = new core.CondVar();
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
        const version = await core.withBackoff(
            backoffCfg, () => this.init(),
            e => { this.status('error', e.toString()); });
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
        // if requested. Pulling is prioritized because pushes fail if there are
        // remote updates.
        try {
            const wakeup = () => this._stop || this._pull || this._push;
            const wakeupErr = () => this._stop;
            let wargs = [wakeup], pushing = false;
            for (let retries = 0;;) {
                await this.poke.wait(...wargs);
                if (this._stop) break;
                wargs = [wakeup];
                try {
                    // Keep pulling as long as there are remote updates.
                    this._pull = false;
                    let pulled = false;
                    for (;;) {
                        const v = cm.collab.getSyncedVersion(this.view.state);
                        if (v === remoteVersion) break;
                        if (core.debug('editor')) {
                            console.log(`Pulling ${v} => ${remoteVersion}`);
                        }
                        await this.pull();
                        pulled = true;
                    }

                    // Push local updates if there are any.
                    const push = this._push;
                    this._push = false;
                    if (cm.collab.sendableUpdates(this.view.state).length > 0) {
                        if (pulled || push || pushing) {
                            if (core.debug('editor')) {
                                const st = this.view.state;
                                const v = cm.collab.getSyncedVersion(st);
                                const u = cm.collab.sendableUpdates(st).length;
                                console.log(`Pushing ${v} => ${v + u}`);
                            }
                            pushing = true;
                            await this.push();
                            pushing = false;
                        }
                    } else {
                        this.saved();
                    }
                    retries = 0;
                } catch (e) {
                    if (core.debug('editor')) console.error(e)
                    wargs = [wakeupErr, core.backoff(backoffCfg, retries++)];
                    this.status('error', e.toString());
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
        if (text !== null) trs.add(this.setText(cm.state.Text.of(text)));
        trs.add({
            effects: this.constructor.collab.reconfigure(cm.collab.collab({
                startVersion: version, clientID: await core.randomId(6),
            })),
        }, this.readOnly(false));
        this.view.dispatch(trs);
        return version;
    }

    async pull() {
        const {updates} = await api.editor({
            pull: this.config.id,
            version: cm.collab.getSyncedVersion(this.view.state),
        });
        if (this._stop) return;
        const up = [];
        for (const [c, us] of updates) {
            for (const u of us) {
                up.push({clientID: c, changes: cm.state.ChangeSet.fromJSON(u)});
            }
        }
        this.view.dispatch(cm.collab.receiveUpdates(this.view.state, up));
    }

    async push() {
        const st = this.view.state;
        const {success} = await api.editor({
            push: this.config.id, version: cm.collab.getSyncedVersion(st),
            client: cm.collab.getClientID(st),
            updates: cm.collab.sendableUpdates(st).map(u => u.changes.toJSON()),
            text: st.doc.toJSON(),
        });
        return success;
    }
}

export function collabStore(config) { return CollabStore.define(config); }
