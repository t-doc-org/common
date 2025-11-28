// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {domLoaded, text} from './tdoc/core.js';

let count = 0;

domLoaded.then(() => {
    const app = document.querySelector('.tdoc-web-app');
    app.querySelector('button').addEventListener('click', async () => {
        ++count;
        app.querySelector('span').replaceChildren(text(`${count}`));
    });
});
