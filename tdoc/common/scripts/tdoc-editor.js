// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import * as autocomplete from '@codemirror/autocomplete';
import * as commands from '@codemirror/commands';
import * as language from '@codemirror/language';
import * as lint from '@codemirror/lint';
import * as search from '@codemirror/search';
import * as state from '@codemirror/state';
import * as view from '@codemirror/view';

import {oneDark} from '@codemirror/theme-one-dark';

import {css} from '@codemirror/lang-css';
import {html} from '@codemirror/lang-html';
import {javascript} from '@codemirror/lang-javascript';
import {python} from '@codemirror/lang-python';
import {sql} from '@codemirror/lang-sql';

const languages = {css, html, javascript, python, sql};

// React to theme changes and update all editor themes as well.
const theme = new state.Compartment();
const lightTheme = view.EditorView.theme({}, {dark: false});
const darkTheme = oneDark;

function currentTheme() {
    return document.querySelector('html').dataset.theme === 'dark' ?
           darkTheme : lightTheme;
}

let curTheme = currentTheme();

const obs = new MutationObserver((mutations) => {
    const newTheme = currentTheme();
    if (newTheme === curTheme) return;
    curTheme = newTheme;
    for (const div of document.querySelectorAll('div.cm-editor')) {
        const editor = div.tdocEditor;
        editor.dispatch({effects: theme.reconfigure(curTheme)});
    }
});
obs.observe(document.documentElement,
            {attributes: true, attributeFilter: ['data-theme']});

// Return the editor extensions for the given config.
function extensions(config) {
    return [
        theme.of(currentTheme()),
        autocomplete.autocompletion(),
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
            ...(config.onRun ? [{key: "Shift-Enter", run: config.onRun}] : []),
            ...autocomplete.closeBracketsKeymap,
            ...autocomplete.completionKeymap,
            ...commands.defaultKeymap,
            ...commands.historyKeymap,
            commands.indentWithTab,
            ...language.foldKeymap,
            ...lint.lintKeymap,
            ...search.searchKeymap,
        ]),
        view.lineNumbers(),
        view.rectangularSelection(),
        view.EditorView.lineWrapping,
        (languages[config.language] || (() => []))(),
    ];
}

// Add an editor to the given element.
export function addEditor(parent, config) {
    const editor = new view.EditorView({
        doc: config.text || '',
        extensions: extensions(config),
        parent,
    });
    const node = parent.querySelector('div.cm-editor');
    node.tdocEditor = editor;
    return [editor, node];
}

// Find an editor in or below the given element.
export function findEditor(el) {
    const node = el.querySelector('div.cm-editor');
    return [node?.tdocEditor, node];
}
