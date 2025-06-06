// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {XWorker} from '../polyscript/index.js';
import {dec, elmt, focusIfVisible, on, text} from './core.js';
import {Executor} from './exec.js';

let worker;
const executors = {};
const hooks = {
    write: (run_id, ...args) => {
        const exec = executors[run_id];
        if (exec) return exec.onWrite(...args);
    },
    input: (run_id, ...args) => {
        const exec = executors[run_id];
        if (exec) return exec.onInput(...args);
    },
    render: (run_id, ...args) => {
        const exec = executors[run_id];
        if (exec) return exec.onRender(...args);
    },
};

class PythonExecutor extends Executor {
    static runner = 'python';
    static highlight = 'python';

    static async init(runable) {
        if (!runable) return;
        const base = import.meta.resolve('../');
        const md = tdoc.exec?.metadata?.python;
        const files = {}
        for (const [k, v] of Object.entries(md?.files ?? {})) {
            files[(new URL(k, base)).toString()] = v;
        }
        files[import.meta.resolve('./exec-python.zip')] = '/lib/tdoc.zip';

        worker = XWorker(import.meta.resolve('./exec-python.py'), {
            type: 'pyodide',
            version: import.meta.resolve('../pyodide/pyodide.mjs'),
            // https://docs.pyscript.net/latest/user-guide/configuration/
            config: {...md, files},
        });
        const {promise, resolve} = Promise.withResolvers();
        worker.sync.ready = msg => {
            console.info(`[t-doc] ${msg}`);
            resolve();
        };
        for (const [k, v] of Object.entries(hooks)) worker.sync[k] = v;
        await promise;
    }

    constructor(node) {
        super(node);
        this.output = this.sectionedOutput();
        this.console = this.output.consoleOut('990');
    }

    addControls(controls) {
        if (this.when !== 'never') {
            this.runCtrl = controls.appendChild(this.runControl());
            this.runCtrl.disabled = true;
            this.stopCtrl = controls.appendChild(this.stopControl());
            this.stopCtrl.disabled = true;
            this.stopCtrl.classList.add('hidden');
        }
        super.addControls(controls);
    }

    onReady() {
        if (this.runCtrl) this.runCtrl.disabled = false;
        if (this.stopCtrl) this.stopCtrl.disabled = false;
    }

    preRun(run_id) {
        this.runCtrl.classList.add('hidden');
        this.stopCtrl.classList.remove('hidden');
        executors[run_id] = this;
    }

    postRun(run_id) {
        delete executors[run_id];
        if (this.input) {
            this.input.remove();
            delete this.input;
        }
        this.runCtrl.classList.remove('hidden');
        this.stopCtrl.classList.add('hidden');
    }

    async run(run_id) {
        try {
            this.output.remove();
            const blocks = [];
            for (const {code, node} of this.codeBlocks()) {
                blocks.push([code, node.id]);
            }
            await worker.sync.run(run_id, blocks);
        } finally {
            await worker.sync.stop(run_id);
        }
    }

    async stop(run_id) {
        await worker.sync.stop(run_id);
    }

    onWrite(stream, data) {
        this.console.write(stream === 2 ? 'err' : '', data);
    }

    async onInput(type, prompt, ...args) {
        try {
            const {promise, resolve} = Promise.withResolvers();
            switch (type) {
            case 'line': {
                const {div, input} = this.output.lineInput(
                    '991', prompt, input => resolve(input.value));
                this.input = div;
                // Set the focus with a delay, as the "play" button is sometimes
                // still active if the input is requested immediately on start.
                setTimeout(() => { focusIfVisible(input); });
                break;
            }
            case 'text': {
                const {div, input} = this.output.multilineInput(
                    '991', prompt, input => resolve(input.value));
                this.input = div;
                // Set the focus with a delay, as the "play" button is sometimes
                // still active if the input is requested immediately on start.
                setTimeout(() => { focusIfVisible(input); });
                break;
            }
            case 'buttons-right':
            case 'buttons': {
                const div = this.input = this.output.input('991', prompt);
                if (type === 'buttons-right') {
                    div.appendChild(elmt`<div class="input"></div>`);
                }
                for (const [index, label] of args[0].entries()) {
                    const btn = div.appendChild(
                        elmt`<button class="tdoc-button"></button>`);
                    const icon = /^@icon\{([^}]+)\}$/.exec(label);
                    if (icon) {
                        btn.classList.add(`fa-${icon[1]}`);
                    } else {
                        btn.appendChild(text(label));
                    }
                    on(btn).click(() => { resolve(index); });
                }
                break;
            }
            default:
                return;
            }
            return await promise;
        } finally {
            if (this.input) {
                this.input.remove();
                delete this.input;
            }
        }
    }

    onRender(html, name) {
        const el = this.output.render(name, html);
        return [el.scrollWidth, el.scrollHeight];
    }
}

Executor.apply(PythonExecutor);  // Background
