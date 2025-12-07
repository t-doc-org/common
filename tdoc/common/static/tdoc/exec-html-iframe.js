// Copyright 2025 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

// TODO: Capture JavaScript errors (Window.onerror)

'use strict';
(() => {
    // Set up channel back to the parent.
    let connected = true;
    function send(data, disconnect = false) {
        if (connected) parent.postMessage(data, '*');
        if (disconnect) connected = false;
    }
    addEventListener('beforeunload', () => { send({unload: true}, true); });

    // Notify the parent on page title changes.
    let title;
    function updateTitle() {
        if (document.title !== title) {
            title = document.title;
            send({title});
        }
    }
    updateTitle();
    const obs = new MutationObserver(updateTitle);
    addEventListener('beforeunload', () => { obs.disconnect(); });
    obs.observe(document.head,
                {subtree: true, childList: true, characterData: true});

    // Hook into console methods.
    function formatArgs(args) {
        return args.map(formatArg).join(" ");
    }

    function formatArg(arg) {
        try {
            if (arg === undefined) return 'undefined';
            if (arg instanceof Element) return arg.outerHTML;
            if (typeof arg === 'object') return JSON.stringify(arg);
        } catch (e) {}
        return arg.toString();
    }

    class Console {
        #c
        #counts

        constructor(c) {
            this.#c = c;
            this.#counts = {};
        }

        #log(args, stream) {
            const msg = formatArgs(args);
            if (msg) send({consoleLog: {msg, stream}});
        }

        assert(cond, ...args) {
            this.#c.assert(cond, ...args);
            if (!cond) {
                if (args.length === 0) args = ['console.assert'];
                this.#log(args, 'err');
            }
        }

        clear() { send({consoleClear: true}); }

        count(label) {
            this.#c.count(label);
            label ??= 'default';
            const v = this.#counts[label] = (this.#counts[label] ?? 0) + 1;
            this.#log(`${label}: ${v}`);
        }

        countReset(label) {
            this.#c.countReset(label);
            delete this.#counts[label ?? 'default'];
        }

        debug(...args) {
            this.#c.debug(...args);
            this.#log(args, 'debug');
        }

        error(...args) {
            this.#c.error(...args);
            this.#log(args, 'err');
        }

        info(...args) {
            this.#c.info(...args);
            this.#log(args, 'info');
        }

        log(...args) {
            this.#c.log(...args);
            this.#log(args);
        }

        warn(...args) {
            this.#c.warn(...args);
            this.#log(args, 'warn');
        }

        // Unimplemented methods.
        dir(...args) { this.#c.dir(...args); }
        dirxml(...args) { this.#c.dirxml(...args); }
        group(...args) { this.#c.group(...args); }
        groupCollapsed(...args) { this.#c.groupCollapsed(...args); }
        groupEnd(...args) { this.#c.groupEnd(...args); }
        table(...args) { this.#c.table(...args); }
        time(...args) { this.#c.time(...args); }
        timeEnd(...args) { this.#c.timeEnd(...args); }
        timeLog(...args) { this.#c.timeLog(...args); }
        trace(...args) { this.#c.trace(...args); }
    }

    globalThis.console = new Console(globalThis.console);
})();
