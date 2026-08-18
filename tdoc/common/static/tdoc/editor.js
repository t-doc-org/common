// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {
    autocomplete, collab, commands, language, languages, lint, oneDark, search,
    state, view,
} from './codemirror.js';

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
