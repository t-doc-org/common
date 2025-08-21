// Copyright 2025 Remy Blank <remy@c-space.org>
// SPDX-License-Identifier: MIT

import {domLoaded, qsa} from './core.js';

if (tdoc.diagram.mermaid) {
    (async () => {
        const {default: mermaid} =
            await import(`${tdoc.versions.mermaid}/mermaid.esm.min.mjs`);
        // TODO: Add support for the elk layout
        await domLoaded;
        // TODO: Set theme if not already set, based on current theme
        // TODO: Re-render all diagrams on theme change
        mermaid.initialize({
            ...tdoc.diagram.mermaid,
            startOnLoad: false,
        });
        // TODO: Render all concurrently using render()
        await mermaid.run({
            nodes: qsa(document, '.tdoc-diagram[data-type=mermaid'),
        });
    })();
}
