// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {XWorker} from 'https://cdn.jsdelivr.net/npm/polyscript';
import {Executor, element, text} from './tdoc-exec.js';

function signal() {
    let resolve, reject;
    const promise = new Promise((res, rej) => { resolve = res; reject = rej; });
    return {promise, resolve, reject};
}

// TODO: Make micropython work, and allow selecting the interpreter type
// TODO: Use hooks to determine readiness

const worker = XWorker(import.meta.resolve('./tdoc-python.py'), {
    type: 'pyodide',
    config: {},
});
const {promise: ready, resolve: resolve_ready} = signal();
worker.sync.ready = (msg) => {
    console.info(`[t-doc] ${msg}`);
    resolve_ready();
};

const stdio = {};
worker.sync.write = (run_id, stream, data) => {
    const fn = stdio[run_id];
    if (fn) {
        fn(stream, data);
    } else {
        console.log(`${run_id}:${stream}: ${data}`);
    }
};

// TODO: Add a button to each {exec} output to remove it
// TODO: Make terminal output configurable. If ":output: always", then create
//       the terminal output right away to avoid flickering.

class PythonExecutor extends Executor {
    static lang = 'python';
    static next_run_id = 0;

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

    async run() {
        this.run_id = PythonExecutor.next_run_id++;
        try {
            this.replaceOutputs([]);
            let pre;
            stdio[this.run_id] = (stream, data) => {
                if (!pre) {
                    const output = element(`\
<div class="tdoc-exec-output tdoc-captioned">\
<div class="tdoc-caption">Terminal output</div>\
<div class="highlight"><pre></pre></div>\
</div>`);
                    this.replaceOutputs([output]);
                    pre = output.querySelector('pre');
                }
                for (;;) {
                    const i = data.indexOf('\u000c');
                    if (i < 0) break;
                    pre.replaceChildren();
                    data = data.slice(i + 1);
                }
                let node = text(data);
                if (stream === 2) {
                    const el = element(`<span class="err"></span>`);
                    el.appendChild(node);
                    node = el;
                }
                pre.appendChild(node);
            };
            await ready;
            this.runCtrl.classList.add('hidden');
            this.stopCtrl.classList.remove('hidden');
            const blocks = [];
            for (const [code, node] of this.codeBlocks()) {
                blocks.push([code, node.id]);
            }
            await worker.sync.run(this.run_id, blocks)
        } catch (e) {
            console.error(e);
            const msg = e.toString();
            const output = element(`\
<div class="tdoc-exec-output tdoc-error"><strong>Error:</strong></div>`);
            output.appendChild(text(` ${msg}`));
            this.appendOutputs([output]);
        } finally {
            delete stdio[this.run_id];
            delete this.run_id;
            this.runCtrl.classList.remove('hidden');
            this.stopCtrl.classList.add('hidden');
        }
    }

    async stop() {
        if (this.run_id) await worker.sync.stop(this.run_id);
    }
}

Executor.apply(PythonExecutor);
await ready;
for (const node of Executor.query(PythonExecutor)) {
    const h = node.tdocHandler;
    if (h.runCtrl) h.runCtrl.disabled = false;
    if (h.stopCtrl) h.stopCtrl.disabled = false;
}
