// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import * as autocomplete from '@codemirror/autocomplete';
import * as commands from '@codemirror/commands';
import * as language from '@codemirror/language';
import * as lint from '@codemirror/lint';
import * as search from '@codemirror/search';
import * as state from '@codemirror/state';
import * as view from '@codemirror/view';

import {css} from '@codemirror/lang-css';
import {html} from '@codemirror/lang-html';
import {javascript} from '@codemirror/lang-javascript';
import {python} from '@codemirror/lang-python';
import {sql} from '@codemirror/lang-sql';

const languages = {css, html, javascript, python, sql};

function extensions(config) {
  return [
    autocomplete.autocompletion(),
    autocomplete.closeBrackets(),
    commands.history(),
    language.bracketMatching(),
    language.foldGutter(),
    language.indentOnInput(),
    language.indentUnit.of('    '),
    language.syntaxHighlighting(language.defaultHighlightStyle,
                                {fallback: true}),
    search.highlightSelectionMatches(),
    state.EditorState.allowMultipleSelections.of(true),
    state.EditorState.tabSize.of(4),
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

export function newEditor(parent, config) {
  return new view.EditorView({
    doc: config.text || '',
    extensions: extensions(config),
    parent,
  });
}
