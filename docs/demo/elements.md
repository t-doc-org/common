% Copyright 2024 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Elements

## Document metadata

This section configures page metadata with a {rst:dir}`metadata` directive to
hide solutions by default.

```{metadata}
solutions: hide
```

## Solutions

This section has several {rst:dir}`solution` blocks, and the page is
configured to hide solutions by default. Click the "Toggle solutions"
(<span class="tdoc-icon fa-eye"></span> /
<span class="tdoc-icon fa-eye-slash"></span>) button in the navbar to show or
hide them.

```{solution}
This solution follows the per-page setting.
```

```{solution} *Complete* solution
This solution has a custom title.
```

```{solution} Solution (show)
:show:
This solution is always visible.
```

```{solution} Solution (expand)
:expand:
This solution is expanded by default.
```

```{solution}
:class: warning
This solution has a different color, and no drop-down.
```

## Quizzes

The helpers in the
[`quizz.js`](https://github.com/t-doc-org/common/blob/main/tdoc/common/static/tdoc/quizz.js)
module enable the creation of quizzes as dynamic page elements.

<script>
'use strict';
(() => {
    let core = tdoc.import('tdoc/core.js').then(m => { core = m; });
    let quizz = tdoc.import('tdoc/quizz.js').then(m => { quizz = m; });

    tdoc.question = tdoc.when(core, quizz, (script, prompt, want) => {
        return quizz.question(script, prompt, resp => {
            if (resp === want) return true;
            return core.html`\
The solution is <em>probably</em> "${want}". Maybe. I'm not sure.`;
      });
    });

    tdoc.tableQuizz = tdoc.when(core, quizz, (script, max) => {
        quizz.genTable(script, (table, row, button) => {
            // Generate a new random question.
            const value = Math.floor(Math.random() * (max + 1));

            // Add the row cells.
            row.appendChild(core.elmt`<td class="text-center">${value}</td>`);
            const sel = core.qs(row.appendChild(core.elmt`\
<td class="text-center">\
<select><option></option><option>odd</option><option>even</option></select>\
</td>`), 'select');
            const input = core.qs(row.appendChild(core.elmt`\
<td>\
<input type="text" autocapitalize="off" autocomplete="off" autocorrect="off"\
 spellcheck="false">\
</td>`), 'input');
            core.on(input).keydown(e => {
                if (e.key === 'Enter' && !e.altKey && !e.ctrlKey
                        && !e.metaKey) {
                    e.preventDefault();
                    button.click();
                }
            });

            function verify() {
                const v = sel.value === 'odd' ? true :
                          sel.value === 'even' ? false : null;
                let res = v === (value % 2 === 1);
                sel.classList.toggle('tdoc-bg-bad', !res);
                const ok = input.value.trim() === (-value).toString();
                input.classList.toggle('tdoc-bg-bad', !ok);
                res = res & ok;
                if (res) core.enable(false, sel, input);
                return res;
            }

            return {verify, focus: sel};
        });
    });
})();
</script>

1.  <script>
    const value = Math.floor(256 * Math.random());
    tdoc.question(
      `Convert \\(${value.toString(2).padStart(8, '0')}_2\\) to decimal.`,
      value.toString());
    </script>
2.  <script>
    tdoc.question(`\
    What is the answer to the ultimate question of life, the universe, and \
    everything? Explain your reasoning in full detail, provide references, and \
    indicate plausible alternatives.`, '42');
    </script>
3.  The input field of quizz questions without a prompt uses the whole line.
    <script>tdoc.question(undefined, "cool");</script>

They also enable creating randomized drill exercises.

| Value | Odd / even | Opposite |
| :---: | :--------: | :------: |

<script>tdoc.tableQuizz(99);</script>

## IFrames

The [YouTube](https://youtube.com/) video below is embedded with the
{rst:dir}`youtube` directive.

```{youtube} aVwxzDHniEw
```

The [GeoGebra](https://geogebra.org/) sheet below is embedded with the
{rst:dir}`iframe` directive.

```{iframe} https://www.geogebra.org/classic/esdhdhzd
```

## Numbering

This sections uses the {rst:role}`num` role to create numbered sub-sections that
reference each other with the {rst:role}`numref` role, and separately numbered
unreferenced quotes.

### Exercise {num}`ex:first`

Read these quotes, then move on to exercises {numref}`ex:second` &
{numref}`ex:third`.

{attribution="Terry Pratchett, Mort"}
> **Quote {num}`quote`:** "It would seem that you have no useful skill or talent
> whatsoever," he said. "Have you thought of going into teaching?""

{attribution="Terry Pratchett, Hogfather"}
> **Quote {num}`quote`:** Real stupidity beats artificial intelligence every
> time.

### Exercise {num}`ex:second`

You've already read the quotes from {numref}`exercise %s<ex:first>`. Read this
one as well, the move to {numref}`exercise %s<ex:third>`.

{attribution="Douglas Adams, The Hitchhiker’s Guide to the Galaxy"}
> **Quote {num}`quote`:** For a moment, nothing happened. Then, after a second
> or so, nothing continued to happen.

### Exercise {num}`ex:third`

This is the last quote.

{attribution="Iain M. Banks, Consider Phlebas"}
> **Quote {num}`quote`:** I had nightmares I thought were really horrible until
> I woke up and remembered what reality was at the moment.
