% Copyright 2024 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Cryptography

<style>
.fields {
    display: flex;
    flex-direction: row;
    align-content: stretch;
    align-items: baseline;
    margin: 1rem 0;
    column-gap: 0.3rem;
}
.fields .pad {
    margin-left: 0.7rem;
}
.fields input {
    width: 100%;
}
.input {
    margin: 1rem 0;
}
.input textarea {
    width: 100%;
}
.output {
    margin: 1rem 0;
    width: 100%;
}
.output pre {
    word-break: break-all;
    white-space: pre-wrap;
}
.output pre.error {
    background-color: var(--pst-color-danger-bg);
}
</style>

<script type="module">
import {domLoaded, text, toBase64} from '../_static/tdoc/core.js';
import {decryptSecret, deriveKey, encryptSecret, random} from '../_static/tdoc/crypto.js';

let keyCache = {};

async function getKey(pwd, salt) {
    if (pwd !== keyCache.pwd || salt !== keyCache.salt) {
        keyCache = {pwd, salt, key: await deriveKey(pwd, salt)}
    }
    return keyCache.key;
}

await domLoaded;
const encIv = document.querySelector('#encrypt .iv pre');
const encOutput = document.querySelector('#encrypt .output pre');

async function encryptInput(key, plain) {
    const msg = await encryptSecret(key, plain);
    encIv.replaceChildren(text(msg.iv));
    encOutput.replaceChildren(text(msg.data));
    return msg;
}

const decOutput = document.querySelector('#decrypt .output pre');

async function decryptInput(key, iv, data) {
    try {
        const plain = await decryptSecret(key, {iv, data});
        decOutput.replaceChildren(text(plain !== '' ? plain : " "));
        decOutput.classList.remove('error');
    } catch (e) {
        decOutput.replaceChildren(text(`Decryption failed: ${e.toString()}`));
        decOutput.classList.add('error');
    }
}

const pwd = document.querySelector('.tdoc-password');
pwd.value = await toBase64(random(15));
const salt = document.querySelector('.tdoc-salt');
salt.value = await toBase64(random(9));

const encInput = document.querySelector('#encrypt textarea');

const decIv = document.querySelector('#decrypt .tdoc-iv');
const decInput = document.querySelector('#decrypt textarea');

let encPending = false, decPending = false;
let running;

async function run() {
    try {
        for (;;) {
            const [enc, dec] = [encPending, decPending];
            if (!(enc || dec)) break;
            const [pwdValue, saltValue] = [pwd.value, salt.value];
            const encInputValue = encInput.value;
            let [decIvValue, decInputValue] = [decIv.value, decInput.value];
            const key = await getKey(pwdValue, saltValue);
            if (enc) {
                encPending = false;
                const {iv, data} = await encryptInput(key, encInputValue);
                decIvValue = decIv.value = iv;
                decInputValue = decInput.value =
                    decInput.parentNode.dataset.text = data;
            }
            if (enc || dec) {
                decPending = false;
                await decryptInput(key, decIvValue, decInputValue);
            }
        }
    } finally {
        running = undefined;
    }
}

function update(enc, dec=false) {
    [encPending, decPending] = [encPending || enc, decPending || dec];
    if (running) return;
    running = run();
}

pwd.addEventListener('input', () => update(true));
salt.addEventListener('input', () => update(true));
encInput.addEventListener('input', () => update(true));
decIv.addEventListener('input', () => update(false, true));
decInput.addEventListener('input', () => update(false, true));

update(true);
</script>

## Key

<div class="fields">
<div>Password:</div><input class="tdoc-password">
<div class="pad">Salt:</div><input class="tdoc-salt">
</div>

## Encrypt

<div class="input tdoc-autosize">
<textarea rows="1" autocapitalize="off" autocomplete="off"
 autocorrect="off" spellcheck="false"
 oninput="this.parentNode.dataset.text = this.value"></textarea>
</div>

```{code-block} text
:class: iv
:caption: IV
```

```{code-block} text
:class: output
:caption: Data
```

## Decrypt

<div class="fields">
<div>IV:</div><input class="tdoc-iv">
</div>

<div class="input tdoc-autosize">
<textarea rows="1" autocapitalize="off" autocomplete="off"
 autocorrect="off" spellcheck="false"
 oninput="this.parentNode.dataset.text = this.value"></textarea>
</div>

```{code-block} text
:class: output
:caption: Data
```
