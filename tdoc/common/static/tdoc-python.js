// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {XWorker} from 'https://cdn.jsdelivr.net/npm/polyscript';
import {Executor, element, signal, text} from './tdoc-exec.js';

// TODO: Add a button to each {exec} output to remove it
// TODO: Make terminal output configurable. If ":output: always", then create
//       the terminal output right away to avoid flickering.
// TODO: Make micropython work, and allow selecting the interpreter type

const worker = XWorker(import.meta.resolve('./tdoc-python.py'), {
    type: 'pyodide',
    config: {},
});
const {promise: ready, resolve: resolve_ready} = signal();
worker.sync.ready = (msg) => {
    console.info(`[t-doc] ${msg}`);
    resolve_ready();
};

const writers = {};
worker.sync.write = (run_id, stream, data) => {
    const fn = writers[run_id];
    if (fn) {
        fn(stream, data);
    } else {
        console.log(`${run_id}:${stream}: ${data}`);
    }
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
        let pre;
        writers[run_id] = (stream, data) => {
            if (!pre) {
                const output = this.terminalOutput();
                this.appendOutputs([output]);
                pre = output.querySelector('pre');
            }
            const i = data.lastIndexOf(form_feed);
            if (i >= 0) {
                pre.replaceChildren();
                data = data.subarray(i + 1);
            }
            let node = text(utf8.decode(data));
            if (stream === 2) {
                const el = element(`<span class="err"></span>`);
                el.appendChild(node);
                node = el;
            }
            pre.appendChild(node);
        };
    }

    postRun(run_id) {
        delete writers[run_id];
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

    terminalOutput() {
        return element(`\
<div class="tdoc-exec-output tdoc-captioned">\
<div class="tdoc-caption">Terminal output</div>\
<div class="highlight"><pre></pre></div>\
</div>`);
    }
}

Executor.apply(PythonExecutor);
