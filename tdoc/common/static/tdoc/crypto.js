// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {dec, enc, fromBase64, toBase64} from './core.js';

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

// Return the decryption key for the password contained in the given query
// parameter and the given salt.
export async function pageKey(name, salt) {
    const params = new URLSearchParams(document.location.search);
    const value = params.get(name);
    if (value === null) throw new Error(`Missing page key: ${name}`);
    return await deriveKey(value, salt);
}

// Encrypt a string secret.
export async function encryptSecret(key, secret) {
    const {data, iv} = await encrypt(key, enc.encode(secret));
    return {data: await toBase64(data), iv: await toBase64(iv)};
}

// Decrypt a string secret.
export async function decryptSecret(key, msg) {
    return dec.decode(await decrypt(key, await fromBase64(msg.iv),
                                    await fromBase64(msg.data)));
}
