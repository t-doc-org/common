// Copyright 2025 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import * as api from './api.js';
import {clientId, domLoaded, htmlData, on, qs, qsa} from './core.js';

class Poll {
    constructor(node) {
        this.node = node;
        const ds = node.dataset;
        this.mode = ds.mode;
        this.closeAfter = ds.closeAfter !== undefined ? +ds.closeAfter
                                                      : undefined;
        this.header = qs(node, '.tdoc-poll-header');
        this.answers = [...qsa(node, '.tdoc-poll-answers > tbody > tr')];
        this.watch = new api.Watch({name: 'poll', id: this.id},
                                   data => this.onUpdate(data));
        this.open = false;
        this.results = false;
        this.solutions = false;
        for (const el of this.answers) on(el).click(() => this.onVote(el));
        on(qs(this.header, '.tdoc-open')).click(e => this.onOpen(e));
        on(qs(this.header, '.tdoc-results')).click(e => this.onResults(e));
        on(qs(this.header, '.tdoc-solutions')).click(e => this.onSolutions(e));
        on(qs(this.header, '.tdoc-clear')).click(e => this.onClear(e));
    }

    get id() { return this.node.dataset.id; }
    ids(all) { return all ? polls.map(p => p.id) : [this.id]; }

    get open() { return this._open; }

    set open(value) {
        if (value === this._open) return;
        this._open = value;
        this.node.classList.toggle('open', value);
        const btn = qs(this.node, '.tdoc-open');
        btn.classList.toggle('fa-play', !value);
        btn.classList.toggle('fa-stop', value);
        btn.setAttribute('title',
                         value ? "Close poll (Ctrl+click to close all)"
                               : "Open poll (Ctrl+click to open all)");
    }

    get results() { return this._results; }

    set results(value) {
        if (value === this._results) return;
        this._results = value;
        const btn = qs(this.node, '.tdoc-results');
        btn.classList.toggle('fa-eye', !value);
        btn.classList.toggle('fa-eye-slash', value);
        btn.setAttribute('title',
                         value ? "Hide results (Ctrl+click to hide all)"
                               : "Show results (Ctrl+click to show all)");
    }

    get solutions() { return this._solutions; }

    set solutions(value) {
        if (value === this._solutions) return;
        this._solutions = value;
        this.node.classList.toggle('solutions', value);
        const btn = qs(this.node, '.tdoc-solutions');
        btn.classList.toggle('fa-check', !value);
        btn.classList.toggle('fa-xmark', value);
        btn.setAttribute('title',
                         value ? "Hide solutions (Ctrl+click to hide all)"
                               : "Show solutions (Ctrl+click to show all)");
    }

    async onOpen(e) {
        if (!this.open) {
            const ps = e.ctrlKey ? polls : [this];
            await api.poll({open: ps.map(p => ({
                id: p.id, mode: p.mode, answers: p.answers.length,
                exp: p.closeAfter,
            }))});
        } else {
            await api.poll({close: this.ids(e.ctrlKey)});
        }
    }

    async onResults(e) {
        await api.poll({results: this.ids(e.ctrlKey), value: !this.results});
    }

    async onSolutions(e) {
        await api.poll({solutions: this.ids(e.ctrlKey),
                        value: !this.solutions});
    }

    async onClear(e) {
        await api.poll({clear: this.ids(e.ctrlKey)});
    }

    async onVote(tr) {
        if (!this.open) return;
        const answer = this.answers.indexOf(tr);
        if (answer < 0) return;
        await api.poll({id: this.id, voter: clientId, answer,
                        vote: !tr.classList.contains('selected')});
    }

    onUpdate(data) {
        this.open = data.open;
        this.results = data.results;
        this.solutions = data.solutions;
        qs(this.header, '.voters').lastChild.textContent = `${data.voters}`;
        qs(this.header, '.votes').lastChild.textContent = `${data.votes}`;
        let max = 0;
        for (const v of Object.values(data.answers ?? {})) {
            if (v > max) max = v;
        }
        for (const [i, tr] of this.answers.entries()) {
            const votes = data.answers?.[i] ?? 0;
            const percent = Math.round(100 * votes / data.votes);
            qs(tr, '.tdoc-poll-cnt').textContent = votes === 0 ? ''
                                                   : `${votes}`;
            qs(tr, '.tdoc-poll-pct').textContent = votes === 0 ? ''
                                                   : `${percent} %`;
            if (votes !== 0) {
                const value = Math.round(100 * votes / max);
                tr.setAttribute('style', `--tdoc-value: ${value}%;`);
            } else {
                tr.removeAttribute('style');
            }
        }
    }

    onVotesUpdate(votes) {
        for (const [i, tr] of this.answers.entries()) {
            tr.classList.toggle('selected', votes.includes(i));
        }
    }
}

const polls = [];
domLoaded.then(() => {
    for (const el of qsa(document, '.tdoc-poll')) polls.push(new Poll(el));
    if (polls.length === 0) return;
    const watch = new api.Watch(
        {name: 'poll/votes', voter: clientId, ids: polls.map(p => p.id)},
        data => {
            for (const poll of polls) {
                poll.onVotesUpdate(data.votes[poll.id] ?? []);
            }
        });
    api.events.sub({add: [...polls.map(p => p.watch), watch]});  // Background
    api.user.onChange(async () => {
        if (await api.user.member_of('polls:control')) {
            htmlData.tdocPollControl = '';
        } else {
            delete htmlData.tdocPollControl;
        }
    });
});
