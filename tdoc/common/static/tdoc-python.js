// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {XWorker} from './polyscript/index.js';
import {Executor, element, signal, text} from './tdoc-exec.js';

// TODO: Add a button to each {exec} output to remove it

const worker = XWorker(import.meta.resolve('./tdoc-python.py'), {
    type: 'pyodide',
    version: import.meta.resolve('./pyodide/pyodide.mjs'),
    // https://docs.pyscript.net/latest/user-guide/configuration/
    config: {},
});
const {promise: ready, resolve: resolve_ready} = signal();
worker.sync.ready = (msg) => {
    console.info(`[t-doc] ${msg}`);
    resolve_ready();
};

const executors = {};
worker.sync.write = (run_id, ...args) => {
    const exec = executors[run_id];
    if (exec) return exec.onWrite(...args);
};
worker.sync.input = (run_id, ...args) => {
    const exec = executors[run_id];
    if (exec) return exec.onInput(...args);
};

const utf8 = new TextDecoder();
const form_feed = 0x0c;

class PythonExecutor extends Executor {
    static lang = 'python';

    static async init() {
        await ready;
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
        delete this.out
        if (this.input) {
            this.input.remove()
            delete this.input
        }
        delete this.output
        this.runCtrl.classList.remove('hidden');
        this.stopCtrl.classList.add('hidden');
    }

    async run(run_id) {
        try {
            this.replaceOutputs([]);
            const blocks = [];
            for (const [code, node] of this.codeBlocks()) {
                blocks.push([code, node.id]);
            }
            await worker.sync.run(run_id, blocks)
        } finally {
            await worker.sync.stop(run_id);
        }
    }

    async stop(run_id) {
        await worker.sync.stop(run_id);
    }

    onWrite(stream, data) {
        this.ensureOutput();
        if (!this.out) {
            const div = element(`<div class="highlight"><pre></pre></div>`);
            this.output.prepend(div);
            this.out = div.querySelector('pre');
        }
        const i = data.lastIndexOf(form_feed);
        if (i >= 0) {
            this.out.replaceChildren();
            data = data.subarray(i + 1);
        }
        let node = text(utf8.decode(data));
        if (stream === 2) {
            const el = element(`<span class="err"></span>`);
            el.appendChild(node);
            node = el;
        }
        this.out.appendChild(node);
    }

    async onInput(type, prompt, ...args) {
        this.ensureOutput();
        const div = this.input = this.output.appendChild(element(
            `<div class="tdoc-input"></div>`));
        try {
            if (prompt && prompt !== '') {
                div.appendChild(element(`<div class="prompt"></div>`))
                    .appendChild(text(prompt));
            }
            const {promise, resolve} = Promise.withResolvers();
            switch (type) {
            case 'line': {
                const input = div.appendChild(element(`\
<input class="input" autocapitalize="off" autocomplete="off"\
 autocorrect="off" spellcheck="false"></input>`));
                const btn = div.appendChild(element(
                    `<button title="Send input (Enter)">Send</button>`));
                btn.addEventListener('click', () => { resolve(input.value); });
                input.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' && !e.altKey && !e.ctrlKey &&
                            !e.metaKey) {
                        e.preventDefault();
                        btn.click();
                    }
                });
                break;
            }
            case 'text': {
                const input = div.appendChild(element(`\
<div class="input autosize">\
<textarea rows="1" autocapitalize="off" autocomplete="off"\
 autocorrect="off" spellcheck="false"\
 oninput="this.parentNode.dataset.text = this.value"></textarea>\
</div>`))
                    .querySelector('textarea');
                const btn = div.appendChild(element(
                    `<button title="Send input (Shift+Enter)">Send</button>`));
                btn.addEventListener('click', () => { resolve(input.value); });
                input.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' && e.shiftKey && !e.altKey &&
                            !e.ctrlKey && !e.metaKey) {
                        e.preventDefault();
                        btn.click();
                    }
                });
                break;
            }
            case 'buttons-right':
                div.appendChild(element(`<div class="input"></div>`));
            case 'buttons': {
                for (const [index, label] of args[0].entries()) {
                    const btn = div.appendChild(element(`<button></button>`));
                    const icon = /^@icon\{([^}]+)\}$/.exec(label);
                    if (icon) {
                        btn.classList.add('icon', `fa-${icon[1]}`);
                    } else {
                        btn.appendChild(text(label));
                    }
                    btn.addEventListener('click', () => { resolve(index); });
                }
                break;
            }
            default:
                return;
            }
            return await promise;
        } finally {
            div.remove();
            delete this.input
        }
    }

    ensureOutput() {
        if (!this.output) {
            this.output = element(
                `<div class="tdoc-exec-output tdoc-sectioned"></div>`);
            this.appendOutputs([this.output]);
        }
    }
}

Executor.apply(PythonExecutor);
