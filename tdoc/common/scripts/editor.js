// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import * as autocomplete from '@codemirror/autocomplete';
import * as commands from '@codemirror/commands';
import * as language from '@codemirror/language';
import * as lint from '@codemirror/lint';
import * as search from '@codemirror/search';
import * as cmstate from '@codemirror/state';
import * as cmview from '@codemirror/view';

import {oneDark} from '@codemirror/theme-one-dark';

import {css} from '@codemirror/lang-css';
import {html} from '@codemirror/lang-html';
import {javascript} from '@codemirror/lang-javascript';
import {python} from '@codemirror/lang-python';
import {sql} from '@codemirror/lang-sql';

export {cmstate, cmview};

const languages = {css, html, javascript, python, sql};

// React to theme changes and update all editor themes as well.
const theme = new cmstate.Compartment();
const lightTheme = cmview.EditorView.theme({}, {dark: false});
const darkTheme = oneDark;

function currentTheme() {
    return document.documentElement.dataset.theme === 'dark' ?
           darkTheme : lightTheme;
}

document.addEventListener('theme-change', e => {
    const curTheme = currentTheme();
    for (const div of document.querySelectorAll('div.cm-editor')) {
        const editor = div.tdocEditor;
        editor.dispatch({effects: theme.reconfigure(curTheme)});
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
    cmstate.EditorState.allowMultipleSelections.of(true),
    cmstate.EditorState.tabSize.of(2),
    cmview.crosshairCursor(),
    cmview.drawSelection(),
    cmview.dropCursor(),
    cmview.highlightActiveLine(),
    cmview.highlightActiveLineGutter(),
    cmview.highlightSpecialChars(),
    cmview.keymap.of([
        {key: 'Mod-e', run: commands.deleteLine},
        ...autocomplete.closeBracketsKeymap,
        ...autocomplete.completionKeymap.map(k =>
            k.key === 'Enter' ? {
                ...k, key: 'Tab',
            } : k
        ),
        ...commands.defaultKeymap.map(k =>
            k.key === 'Home' ? {
                ...k,
                run: commands.cursorLineStart, shift: commands.selectLineStart,
            } : k
        ),
        ...commands.historyKeymap,
        commands.indentWithTab,
        ...language.foldKeymap,
        ...lint.lintKeymap,
        ...search.searchKeymap,
    ]),
    cmview.lineNumbers(),
    cmview.rectangularSelection(),
    cmview.EditorView.lineWrapping,
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
    const editor = new cmview.EditorView(config);
    editor.dom.tdocEditor = editor;
    return editor;
}

// Find an editor in or below the given element.
export function findEditor(el) {
    return el.querySelector('div.cm-editor')?.tdocEditor;
}
