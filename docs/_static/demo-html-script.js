// Copyright 2024 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {domLoaded} from './tdoc/core.js';

await domLoaded;
const app = document.querySelector('.tdoc-web-app');
app.querySelector('button')
    .addEventListener('click', () => alert('Click!'));