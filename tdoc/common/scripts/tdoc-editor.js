// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {EditorView, basicSetup} from 'codemirror'
import {css} from '@codemirror/lang-css'
import {html} from '@codemirror/lang-html'
import {javascript} from '@codemirror/lang-javascript'
import {python} from '@codemirror/lang-python'
import {sql} from '@codemirror/lang-sql'

export async function newEditor(lang, parent) {
  const extensions = [basicSetup]
  if (lang === 'css') {
    extensions.push(css());
  } else if (lang === 'html') {
    extensions.push(html());
  } else if (lang === 'javascript') {
    extensions.push(javascript());
  } else if (lang === 'python') {
    extensions.push(python());
  } else if (lang === 'sql') {
    extensions.push(sql());
  } else if (lang !== '') {
    console.error(`Unsupported language: ${lang}`);
  }
  return new EditorView({extensions, parent});
}
