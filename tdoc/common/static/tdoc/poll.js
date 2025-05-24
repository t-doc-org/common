// Copyright 2025 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import * as api from './api.js';
import {clientId, domLoaded, htmlData, on, qs, qsa} from './core.js';

// TODO: Ctrl+click to open/close or show/hide all polls

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
        this.show = false;
        for (const el of this.answers) on(el).click(() => this.onVote(el));
        on(qs(this.header, '.tdoc-open')).click(() => this.onOpen());
        on(qs(this.header, '.tdoc-show')).click(() => this.onShow());
        on(qs(this.header, '.tdoc-clear')).click(() => this.onClear());
    }

    get id() { return this.node.dataset.id; }

    get open() { return this._open; }

    set open(value) {
        if (value === this._open) return;
        this._open = value;
        this.node.classList.toggle('open', value);
        const btn = qs(this.node, '.tdoc-open');
        btn.classList.toggle('fa-play', !value);
        btn.classList.toggle('fa-stop', value);
        btn.setAttribute('title', value ? "Close poll" : "Open poll");
    }

    get show() { return this._show; }

    set show(value) {
        if (value === this._show) return;
        this._show = value;
        const btn = qs(this.node, '.tdoc-show');
        btn.classList.toggle('fa-eye', !value);
        btn.classList.toggle('fa-eye-slash', value);
        btn.setAttribute('title', value ? "Hide results" : "Show results");
    }

    async onOpen() {
        await api.poll(this.open ? {id: this.id, open: null} : {
            id: this.id, open: this.mode, exp: this.closeAfter,
            answers: this.answers.length,
        });
    }

    async onShow() { await api.poll({id: this.id, show: !this.show}); }
    async onClear() { await api.poll({id: this.id, clear: true}); }

    async onVote(tr) {
        if (!this.open) return;
        const answer = this.answers.indexOf(tr);
        if (answer < 0) return;
        await api.poll({
            id: this.id, voter: clientId, answer,
            vote: !tr.classList.contains('selected'),
        });
    }

    onUpdate(data) {
        this.open = data.open;
        this.show = data.show;
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

await domLoaded;
const polls = [];
for (const el of qsa(document, '.tdoc-poll')) polls.push(new Poll(el));
if (polls.length > 0) {
    const watch = new api.Watch(
        {name: 'poll/votes', voter: clientId, ids: polls.map(p => p.id)},
        data => {
            for (const poll of polls) poll.onVotesUpdate(data.votes[poll.id]);
        });
    api.events.sub({add: [...polls.map(p => p.watch), watch]});  // Background
    api.user.onChange(async () => {
        if (await api.user.member_of('polls:control')) {
            htmlData.tdocPollControl = '';
        } else {
            delete htmlData.tdocPollControl;
        }
    });
}

