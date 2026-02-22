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

import {apl} from '@codemirror/legacy-modes/mode/apl';
import {asciiArmor} from '@codemirror/legacy-modes/mode/asciiarmor';
import {asn1} from '@codemirror/legacy-modes/mode/asn1';
import {brainfuck} from '@codemirror/legacy-modes/mode/brainfuck';
import {csharp, dart, kotlin, objectiveC, objectiveCpp, scala}
    from '@codemirror/legacy-modes/mode/clike';
import {clojure} from '@codemirror/legacy-modes/mode/clojure';
import {cmake} from '@codemirror/legacy-modes/mode/cmake';
import {cobol} from '@codemirror/legacy-modes/mode/cobol';
import {coffeeScript} from '@codemirror/legacy-modes/mode/coffeescript';
import {commonLisp} from '@codemirror/legacy-modes/mode/commonlisp';
import {cypher} from '@codemirror/legacy-modes/mode/cypher';
import {crystal} from '@codemirror/legacy-modes/mode/crystal';
import {d} from '@codemirror/legacy-modes/mode/d';
import {diff} from '@codemirror/legacy-modes/mode/diff';
import {dockerFile} from '@codemirror/legacy-modes/mode/dockerfile';
import {dtd} from '@codemirror/legacy-modes/mode/dtd';
import {dylan} from '@codemirror/legacy-modes/mode/dylan';
import {ebnf} from '@codemirror/legacy-modes/mode/ebnf';
import {ecl} from '@codemirror/legacy-modes/mode/ecl';
import {eiffel} from '@codemirror/legacy-modes/mode/eiffel';
import {elm} from '@codemirror/legacy-modes/mode/elm';
import {erlang} from '@codemirror/legacy-modes/mode/erlang';
import {factor} from '@codemirror/legacy-modes/mode/factor';
import {forth} from '@codemirror/legacy-modes/mode/forth';
import {fortran} from '@codemirror/legacy-modes/mode/fortran';
import {gas} from '@codemirror/legacy-modes/mode/gas';
import {gherkin} from '@codemirror/legacy-modes/mode/gherkin';
import {groovy} from '@codemirror/legacy-modes/mode/groovy';
import {haskell} from '@codemirror/legacy-modes/mode/haskell';
import {haxe, hxml} from '@codemirror/legacy-modes/mode/haxe';
import {http} from '@codemirror/legacy-modes/mode/http';
import {idl} from '@codemirror/legacy-modes/mode/idl';
import {jsonld} from '@codemirror/legacy-modes/mode/javascript';
import {julia} from '@codemirror/legacy-modes/mode/julia';
import {liveScript} from '@codemirror/legacy-modes/mode/livescript';
import {lua} from '@codemirror/legacy-modes/mode/lua';
import {mathematica} from '@codemirror/legacy-modes/mode/mathematica';
import {fSharp, oCaml, sml} from '@codemirror/legacy-modes/mode/mllike';
import {modelica} from '@codemirror/legacy-modes/mode/modelica';
import {mscgen} from '@codemirror/legacy-modes/mode/mscgen';
import {nginx} from '@codemirror/legacy-modes/mode/nginx';
import {nsis} from '@codemirror/legacy-modes/mode/nsis';
import {octave} from '@codemirror/legacy-modes/mode/octave';
import {pascal} from '@codemirror/legacy-modes/mode/pascal';
import {perl} from '@codemirror/legacy-modes/mode/perl';
import {pig} from '@codemirror/legacy-modes/mode/pig';
import {powerShell} from '@codemirror/legacy-modes/mode/powershell';
import {properties} from '@codemirror/legacy-modes/mode/properties';
import {protobuf} from '@codemirror/legacy-modes/mode/protobuf';
import {pug} from '@codemirror/legacy-modes/mode/pug';
import {puppet} from '@codemirror/legacy-modes/mode/puppet';
import {cython} from '@codemirror/legacy-modes/mode/python';
import {q} from '@codemirror/legacy-modes/mode/q';
import {r} from '@codemirror/legacy-modes/mode/r';
import {rpmSpec} from '@codemirror/legacy-modes/mode/rpm';
import {ruby} from '@codemirror/legacy-modes/mode/ruby';
import {sas} from '@codemirror/legacy-modes/mode/sas';
import {scheme} from '@codemirror/legacy-modes/mode/scheme';
import {shell} from '@codemirror/legacy-modes/mode/shell';
import {sieve} from '@codemirror/legacy-modes/mode/sieve';
import {smalltalk} from '@codemirror/legacy-modes/mode/smalltalk';
import {sparql} from '@codemirror/legacy-modes/mode/sparql';
import {stex} from '@codemirror/legacy-modes/mode/stex';
import {swift} from '@codemirror/legacy-modes/mode/swift';
import {tcl} from '@codemirror/legacy-modes/mode/tcl';
import {tiddlyWiki} from '@codemirror/legacy-modes/mode/tiddlywiki';
import {toml} from '@codemirror/legacy-modes/mode/toml';
import {troff} from '@codemirror/legacy-modes/mode/troff';
import {turtle} from '@codemirror/legacy-modes/mode/turtle';
import {vb} from '@codemirror/legacy-modes/mode/vb';
import {vbScript} from '@codemirror/legacy-modes/mode/vbscript';
import {velocity} from '@codemirror/legacy-modes/mode/velocity';
import {verilog} from '@codemirror/legacy-modes/mode/verilog';
import {vhdl} from '@codemirror/legacy-modes/mode/vhdl';
import {webIDL} from '@codemirror/legacy-modes/mode/webidl';
import {xQuery} from '@codemirror/legacy-modes/mode/xquery';

import {angular} from '@codemirror/lang-angular';
import {cpp} from '@codemirror/lang-cpp';
import {css} from '@codemirror/lang-css';
import {go} from '@codemirror/lang-go';
import {html} from '@codemirror/lang-html';
import {java} from '@codemirror/lang-java';
import {javascript} from '@codemirror/lang-javascript';
import {jinja} from '@codemirror/lang-jinja';
import {json} from '@codemirror/lang-json';
import {less} from '@codemirror/lang-less';
import {lezer} from '@codemirror/lang-lezer';
import {liquid} from '@codemirror/lang-liquid';
import {markdown} from '@codemirror/lang-markdown';
import {php} from '@codemirror/lang-php';
import {python} from '@codemirror/lang-python';
import {rust} from '@codemirror/lang-rust';
import {sass} from '@codemirror/lang-sass';
import * as sql from '@codemirror/lang-sql';
import {vue} from '@codemirror/lang-vue';
import {wast} from '@codemirror/lang-wast';
import {xml} from '@codemirror/lang-xml';
import {yaml} from '@codemirror/lang-yaml';

export {cmstate, cmview};

// Map pygments lexers to CodeMirror language support. Based on
// <https://pygments.org/docs/lexers/> and
// <https://github.com/codemirror/language-data/blob/main/src/language-data.ts>
const cm5_langs = [
    // @codemirror/legacy-modes/mode/*
    ['apl', apl],
    ['asc', 'pem', asciiArmor],
    ['asn1', asn1],
    ['brainfuck', 'bf', brainfuck],
    ['clojure', 'clj', 'clojurescript', 'cljs', clojure],
    ['cmake', cmake],
    ['cobol', cobol],
    ['coffeescript', 'coffee-script', 'coffee', coffeeScript],
    ['common-lisp', 'cl', 'lisp', commonLisp],
    ['crystal', 'cr', crystal],
    ['csharp', 'c#', 'cs', csharp],
    ['cypher', cypher],
    ['cython', 'pyx', 'pyrex', cython],
    ['d', d],
    ['dart', dart],
    ['diff', 'udiff', diff],
    ['dockerfile', 'docker', dockerFile],
    ['dtd', dtd],
    ['dylan', dylan],
    ['ebnf', ebnf],
    ['ecl', ecl],
    ['eiffel', eiffel],
    ['elm', elm],
    ['erlang', erlang],
    ['factor', factor],
    ['forth', forth],
    ['fortran', 'f90', fortran],
    ['fsharp', 'f#', fSharp],
    ['gas', 'asm', gas],
    ['gherkin', 'cucumber', gherkin],
    ['groff', 'nroff', 'man', troff],
    ['groovy', groovy],
    ['haskell', 'hs', haskell],
    ['haxe', 'hxsl', 'hx', haxe],
    ['hxml', 'haxeml', hxml],
    ['http', http],
    ['idl', idl],
    ['jsonld', 'json-ld', jsonld],
    ['julia', 'jl', julia],
    ['kotlin', kotlin],
    ['livescript', 'live-script', liveScript],
    ['lua', lua],
    ['mathematica', 'mma', 'nb', 'wl', 'wolfram', mathematica],
    ['modelica', modelica],
    ['mscgen', 'msc', mscgen],
    ['nginx', nginx],
    ['nsis', 'nsi', 'nsh', nsis],
    ['objective-c', 'objectivec', 'obj-c', 'objc', objectiveC],
    ['objective-c++', 'objectivec++', 'obj-c++', 'objc++', objectiveCpp],
    ['ocaml', oCaml],
    ['octave', octave],
    ['pascal', 'pas', 'objectpascal', 'delphi', pascal],
    ['perl', 'pl', 'perl6', 'pl6', 'raku', perl],
    ['pig', pig],
    ['powershell', 'pwsh', 'posh', 'ps1', 'psm1', powerShell],
    ['properties', 'jproperties', 'ini', 'cfg', 'dosini', properties],
    ['protobuf', 'proto', protobuf],
    ['pug', 'jade', pug],
    ['puppet', puppet],
    ['q', q],
    ['r', 'splus', 's', r],
    ['ruby', 'rb', 'duby', ruby],
    ['sas', sas],
    ['scala', scala],
    ['scheme', 'scm', scheme],
    ['shell', 'bash', 'sh', 'ksh', 'zsh', 'openrc', shell],
    ['sieve', sieve],
    ['smalltalk', 'squeak', 'st', smalltalk],
    ['sml', sml],
    ['sparql', sparql],
    ['spec', rpmSpec],
    ['swift', swift],
    ['tcl', tcl],
    ['tex', 'latex', stex],
    ['tid', tiddlyWiki],
    ['toml', toml],
    ['turtle', turtle],
    ['vb.net', 'vbnet', 'lobas', 'oobas', 'sobas', 'visual-basic',
     'visualbasic', vb],
    ['vbscript', vbScript],
    ['velocity', velocity],
    ['verilog', 'v', 'systemverilog', 'sv', verilog],
    ['vhdl', vhdl],
    ['webidl', webIDL],
    ['xquery', 'xqy', 'xq', 'xql', 'xqm', xQuery],
];
const cm6_langs = [
    // @codemirror/lang-*
    ['ng2', 'html+ng2', angular],
    ['c', 'c++', 'cpp', cpp],
    ['css', css],
    ['go', 'golang', go],
    ['html', html],
    ['java', java],
    ['javascript', 'js', javascript],
    ['typescript', 'ts', () => javascript({typescript: true})],
    ['jsx', 'react', () => javascript({jsx: true})],
    ['tsx', () => javascript({jsx: true, typescript: true})],
    ['jinja', 'django', 'html+jinja', 'html+django', 'htmldjango', jinja],
    ['css+jinja', 'css+django', () => jinja({base: css()})],
    ['javascript+jinja', 'javascript+django', 'js+jinja', 'js+django',
     () => jinja({base: javascript()})],
    ['sql+jinja', () => jinja({base: sql.sql()})],
    ['xml+jinja', 'xml+django', () => jinja({base: xml()})],
    ['yaml+jinja', 'salt', 'sls', () => jinja({base: yaml()})],
    ['json', 'json-object', 'json5', json],
    ['less', less],
    ['lezer', lezer],
    ['liquid', liquid],
    ['markdown', 'md', markdown],
    ['php', 'php3', 'php4', 'php5', () => php({baseLanguage: null})],
    ['css+php', () => php({baseLanguage: css()})],
    ['html+php', php],
    ['javascript+php', 'js+php', () => php({baseLanguage: javascript()})],
    ['xml+php', () => php({baseLanguage: xml()})],
    ['python', 'py', 'python3', 'py3', 'sage', 'bazel', 'starlark', 'pyi',
     python],
    ['rust', 'rs', rust],
    ['sass', () => sass({indented: true})],
    ['scss', sass],
    ['sql', 'googlesql', 'zetasql', sql.sql],
    ['mysql', () => sql.sql({dialect: sql.MySQL})],
    ['postgresql', 'postgres', () => sql.sql({dialect: sql.PostgreSQL})],
    ['vue', vue],
    ['wast', 'wat', wast],
    ['xml', 'xslt', 'genshi', 'kid', 'xml+genshi', 'xml+kid', xml],
    ['yaml', yaml],
];
const languages = {};
for (const entries of cm5_langs) {
    const lang = new language.LanguageSupport(
        language.StreamLanguage.define(entries.pop()));
    for (const e of entries) languages[e] = lang;
}
for (const entries of cm6_langs) {
    const lang = entries.pop();
    for (const e of entries) languages[e] = lang;
}

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
