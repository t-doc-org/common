// Copyright 2026 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

export const INTERNAL_SERVER_ERROR = 500;
export const SERVICE_UNAVAILABLE = 503;

export class Error extends globalThis.Error {
    constructor(code, msg) {
        super(msg ?? `Error ${code}`, {cause: {code}});
        this.code = code;
        this.msg = msg;
    }
}
