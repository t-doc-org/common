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
configured to hide solutions by default. Click the
<span class="tdoc fa-eye"></span> / <span class="tdoc fa-eye-slash"></span>
button in the navbar to show or hide them.

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

## IFrames

The [YouTube](https://youtube.com/) video below is embedded with the
{rst:dir}`youtube` directive.

```{youtube} aVwxzDHniEw
```

The presentation below is embedded with the {rst:dir}`iframe` directive.

```{iframe} https://docs.google.com/presentation/d/e/2PACX-1vQEemAMuCYvYvdxAJVRJBFD5NU8NQzasRyRpNau10iIVNGCpZSRgw_5dYTUd8EDhE8YyB_6v8b_2F37/embed?start=false&loop=false&delayms=3000
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
one as well, then go to {numref}`exercise %s<ex:third>`.

{attribution="Douglas Adams, The Hitchhiker’s Guide to the Galaxy"}
> **Quote {num}`quote`:** For a moment, nothing happened. Then, after a second
> or so, nothing continued to happen.

### Exercise {num}`ex:third`

This is the last quote.

{attribution="Iain M. Banks, Consider Phlebas"}
> **Quote {num}`quote`:** I had nightmares I thought were really horrible until
> I woke up and remembered what reality was at the moment.

## Quizzes

This section demonstrates interactive quizzes with the {rst:dir}`quiz`
directive and the {rst:role}`quiz-input` and {rst:role}`quiz-select` roles.

### Table

<script type="module">
const [core, quiz] = await tdoc.imports('tdoc/core.js', 'tdoc/quiz.js');

quiz.checks.sum = args => {
    const tds = core.qsa(args.field.closest('tr'), 'td');
    const solution = +tds[0].textContent + (+tds[1].textContent)
    args.ok = args.answer === solution.toString();
    args.hint = `The answer is probably ${solution}.`;
};
</script>

```{role} input(quiz-input)
:style: width: 3rem; text-align: center;
:check: trim sum
```

```{quiz}
| $a$ | $b$ | $a + b$    |
| :-: | :-: | :--------: |
|   1 |   2 | {input}`?` |
|   7 |  11 | {input}`?` |
|  15 |  27 | {input}`?` |
```

### List

```{role} input(quiz-input)
:right: width: 8rem;
:check: trim lowercase
```
```{role} yes-no(quiz-select)
:right:
:options: |
: Yes
: No
```
```{role} input100(quiz-input)
:style: width: 100%; margin-top: 0.3rem;
```

```{quiz}
1.  {input}`42`{quiz-hint}`It's a positive integer.`
    Calculate $6 \cdot 7 $.
2.  {input}`42`{quiz-hint}`It's composed of digits from 0 to 9.`
    {input}`2a`{quiz-hint}`It's composed of digits from 0 to f.`
    Convert $00101010_2$ to decimal and hexadecimal.
3.  {input}`42`{quiz-hint}`It's a number.`
    What is the answer to the ultimate question of life, the
    universe, and everything? Explain your reasoning in full detail, provide
    references, and indicate plausible alternatives.
5.  {yes-no}`Yes`{quiz-hint}`Be positive.`
    Are you sure about your previous answer?
4.  This input field uses the whole line. Guess what the answer is.
    {input100}`42`{quiz-hint}`You've seen this before.`
```

### Randomized drill

| Value | Odd / even | Opposite |
| :---: | :--------: | :------: |

<script>tdoc.tableQuiz(99);</script>

## Polls

The first {rst:dir}`poll` allows only one answer.

```{poll} aeb57180-a5c8-4532-ad15-94b3dd9f3013
What is the equation of a line in a plane?

- $ax^2 + bx + c = 0$
- $ax + by + cz + d = 0$
- $(x-x_0)^2 + (y-y_0)^2 - r^2 = 0$
- :$ax + by + c = 0$
- $y = at^2 + v_0t + y_0$
- I don't know
```

The next poll allows multiple selections, doesn't number the answers, has no
solutions to show, and auto-closes after 30 seconds.

```{poll} 4a790949-1246-49e8-841e-fb7922b98e45
:mode: multi
:number: none
:close-after: 10s
Which animals do you like?

- Spiders
- Crocodiles
- Dolphins
- Sharks
- Platypuses
- Tasmanian devils
```
