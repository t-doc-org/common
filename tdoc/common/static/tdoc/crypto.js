// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {enc} from './core.js';

// Return an Uint8Array of the given size, filled with random data.
export function random(size) {
    return crypto.getRandomValues(new Uint8Array(size));
}

// Derive a symmetric encryption and decryption key from a password and a salt.
export async function deriveKey(password, salt) {
    const pwdKey = await crypto.subtle.importKey(
        'raw', enc.encode(password), 'PBKDF2', false,
        ['deriveBits', 'deriveKey']);
    return await crypto.subtle.deriveKey(
        {name: 'PBKDF2', salt: enc.encode(salt), iterations: 600000,
         hash: 'SHA-256'},
        pwdKey, {name: 'AES-GCM', length: 256}, false, ['encrypt', 'decrypt']);
}

// Encrypt data using AES-GCM.
export async function encrypt(key, data) {
    const iv = random(12);
    return {data: await crypto.subtle.encrypt({name: 'AES-GCM', iv}, key, data),
            iv};
}

// Decrypt data using AES-GCM.
export async function decrypt(key, iv, data) {
    return await crypto.subtle.decrypt({name: 'AES-GCM', iv}, key, data);
}
