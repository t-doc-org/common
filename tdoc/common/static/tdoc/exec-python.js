// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {dec, elmt, focusIfVisible, on, text} from './core.js';
import {Runner} from './exec.js';

class Interpreter {
    files = {}
    runners = {}

    constructor(config) {
        this.config = config;

        // Extract files and resolve their URLs.
        const base = import.meta.resolve('../');
        for (const [k, v] of Object.entries(this.config.files ?? {})) {
            this.files[(new URL(k, base)).toString()] = v;
        }
        this.files[import.meta.resolve('./exec-python.zip')] = '/lib/tdoc.zip';
    }

    setHooks(ns) {
        const p = Interpreter.prototype;
        for (const k of Object.getOwnPropertyNames(p)) {
            if (k.startsWith('js_')) ns[k] = p[k].bind(this);
        }
    }

    js_write(run_id, ...args) {
        const runner = this.runners[run_id];
        if (runner) return runner.onWrite(...this.toJs(args));
    }

    js_input(run_id, ...args) {
        const runner = this.runners[run_id];
        if (runner) return runner.onInput(...this.toJs(args));
    }

    js_render(run_id, ...args) {
        const runner = this.runners[run_id];
        if (runner) return runner.onRender(...this.toJs(args));
    }

    js_setup_canvas(run_id, ...args) {
        const runner = this.runners[run_id];
        if (runner) return runner.onSetupCanvas(...this.toJs(args));
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
                ...this.config,
                files: this.files,
                packages_cache: 'passthrough',
            },
        });
        const {promise, resolve} = Promise.withResolvers();
        this.worker.sync.ready = msg => {
            console.info(`[t-doc] ${msg}`);
            resolve();
        };
        this.setHooks(this.worker.sync);
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
        this.interp.setDebug(this.config.debug ?? false);
        this.canvas = document.body.appendChild(elmt`\
<canvas id="canvas" class="hidden" width="0" height="0"></canvas>`);
        this.interp.canvas.setCanvas2D(this.canvas);
        const tasks = [];
        if (this.config.packages && this.config.packages.length > 0) {
            tasks.push(this.interp.loadPackage(this.config.packages));
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
        this.setHooks(this.core);
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

async function create(cls, config) {
    const inst = new cls(config);
    await inst.init();
    return inst;
}

let interps;

class PythonRunner extends Runner {
    static name = 'python';

    static async init(config) {
        if (config._envs === undefined) return;
        interps = Object.fromEntries(await Promise.all(config._envs.map(
            async env => [
                env,
                env === 'main' ? await create(MainInterpreter, config)
                               : await create(WorkerInterpreter, config),
            ])));
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
        this.interp.runners[run_id] = this;
    }

    postRun(run_id) {
        delete this.interp.runners[run_id];
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

Runner.apply(PythonRunner);  // Background
