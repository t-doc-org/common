// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {dec, elmt, focusIfVisible, on, text} from './core.js';
import {Executor} from './exec.js';

const executors = {};
const hooks = {
    log: (...args) => { console.log(...exec.interp.toJs(args)); },
    write: (run_id, ...args) => {
        const exec = executors[run_id];
        if (exec) return exec.onWrite(...exec.interp.toJs(args));
    },
    input: (run_id, ...args) => {
        const exec = executors[run_id];
        if (exec) return exec.onInput(...exec.interp.toJs(args));
    },
    render: (run_id, ...args) => {
        const exec = executors[run_id];
        if (exec) return exec.onRender(...exec.interp.toJs(args));
    },
    setup_canvas: (run_id, ...args) => {
        const exec = executors[run_id];
        if (exec) return exec.onSetupCanvas(...exec.interp.toJs(args));
    },
};

class Interpreter {
    constructor() {
        this.md = tdoc.exec?.metadata?.python ?? {};

        // Extract files and resolve their URLs.
        const base = import.meta.resolve('../');
        this.files = {}
        for (const [k, v] of Object.entries(this.md.files ?? {})) {
            this.files[(new URL(k, base)).toString()] = v;
        }
        this.files[import.meta.resolve('./exec-python.zip')] = '/lib/tdoc.zip';
    }
}

class WorkerInterpreter extends Interpreter {
    async init() {
        const {XWorker} = await import(`${tdoc.versions.polyscript}/index.js`);
        this.worker = XWorker(import.meta.resolve('./exec-python.py'), {
            type: 'pyodide',
            version: import.meta.resolve(
                `${tdoc.versions.pyodide}/pyodide.mjs`),
            async: true,
            // https://docs.pyscript.net/latest/user-guide/configuration/
            config: {
                ...this.md,
                files: this.files,
                packages_cache: 'passthrough',
            },
        });
        const {promise, resolve} = Promise.withResolvers();
        this.worker.sync.ready = msg => {
            console.info(`[t-doc] ${msg}`);
            resolve();
        };
        for (const [k, v] of Object.entries(hooks)) this.worker.sync[k] = v;
        await promise;
    }

    toJs(args) { return args; }

    async run(run_id, blocks) {
        await this.worker.sync.run(run_id, blocks);
    }

    async stop(run_id) {
        await this.worker.sync.stop(run_id);
    }

    claimCanvas(parent) {}
}

class MainInterpreter extends Interpreter {
    async init() {
        const pyodide = await import(`${tdoc.versions.pyodide}/pyodide.mjs`);
        this.interp = await pyodide.loadPyodide();
        this.interp.setDebug(this.md.debug ?? false);
        this.canvas = document.body.appendChild(elmt`\
<canvas id="canvas" class="hidden" width="0" height="0"></canvas>`);
        this.interp.canvas.setCanvas2D(this.canvas);
        const tasks = [];
        if (this.md.packages && this.md.packages.length > 0) {
            tasks.push(this.interp.loadPackage(this.md.packages));
        }
        tasks.push(this.writeFiles(this.files));
        await Promise.all(tasks);
        const [core, msg] = this.interp.runPython(`\
import platform
import sys

from pyodide_js import version

sys.path.append('/lib/tdoc.zip')
from tdoc import core

msg = (f"{platform.python_implementation()}"
       f" {'.'.join(platform.python_version_tuple())}"
       f" on {platform.platform()},"
       f" using Pyodide {version}")
core, msg
`);
        this.core = core;
        for (const [k, v] of Object.entries(hooks)) this.core[`js_${k}`] = v;
        console.info(`[t-doc] ${msg}`);
    }

    writeFiles() {
        return Promise.all(Object.entries(this.files)
                           .map(async ([src, dst]) => {
            const res = await fetch(src);
            const data = await res.arrayBuffer();
            dst ||= './';
            if (dst.endsWith('/')) dst = `${dst}${src.split('/').pop()}`;
            if (dst.endsWith('/*')) {
                const m = /\.(zip|whl|tgz|tar(?:\.gz)?)$/.exec(src);
                if (!m) throw new Error(`Unsupported archive format: ${src}`);
                this.interp.unpackArchive(data, m[1],
                                          {extractDir: dst.slice(0, -1)});
                return;
            }
            const {FS, PATH, _module: {PATH_FS}} = this.interp;
            const abs = PATH_FS.resolve(dst);
            const dir = PATH.dirname(abs);
            FS.mkdirTree(dir);
            FS.writeFile(abs, new Uint8Array(data), {canOwn: true});
        }));
    }

    toJs(args) { return args.map(a => a.toJs ? a.toJs() : a); }

    async run(run_id, blocks) {
        await this.core.run(run_id, blocks);
    }

    async stop(run_id) {
        await this.core.stop(run_id);
    }

    claimCanvas(parent) {
        this.canvas.classList.toggle('hidden', !parent);
        (parent ?? document.body).appendChild(this.canvas);
    }
}

async function create(cls) {
    const inst = new cls();
    await inst.init();
    return inst;
}

let interps;

class PythonExecutor extends Executor {
    static runner = 'python';
    static highlight = 'python';

    static async init(envs) {
        if (envs.length === 0) return;
        interps = Object.fromEntries(await Promise.all(envs.map(
            async e => [e, e === 'main'? await create(MainInterpreter)
                                       : await create(WorkerInterpreter)])));
    }

    constructor(node) {
        super(node);
        this.output = this.sectionedOutput();
        this.console = this.output.consoleOut('990');
    }

    get interp() { return interps[this.env]; }

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
            this.replaceOutputs();
            const blocks = [];
            for (const {code, node} of this.codeBlocks()) {
                blocks.push([code, node.id]);
            }
            await this.interp.run(run_id, blocks);
        } finally {
            await this.interp.stop(run_id);
            if (this.canvas) {
                this.interp.claimCanvas();
                this.canvas.remove();
                delete this.canvas;
            }
        }
    }

    async stop(run_id) {
        await this.interp.stop(run_id);
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

    onSetupCanvas() {
        if (this.canvas) return;
        this.canvas = this.output.render('', `<div class="canvas"></div>`);
        this.interp.claimCanvas(this.canvas);
    }
}

Executor.apply(PythonExecutor);  // Background
