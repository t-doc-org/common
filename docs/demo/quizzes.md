% Copyright 2024 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Quizzes

This page demonstrates interactive quizzes with the {rst:dir}`quiz` directive
and the {rst:role}`quiz-ph`, {rst:role}`quiz-input`, {rst:role}`quiz-select` and
{rst:role}`quiz-hint` roles.

## Static

<script type="module">
const [core, quiz] = await tdoc.imports('tdoc/core.js', 'tdoc/quiz.js');

quiz.check('sum', args => {
    const tds = core.qsa(args.field.closest('tr'), 'td');
    const solution = +tds[0].textContent + (+tds[1].textContent)
    args.ok = args.answer === solution.toString();
    args.hint = `The answer is probably ${solution}.`;
});
</script>

Static quizzes can be laid out in various formats, for example as tables.

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

They can also be laid out as lists, usually with right-aligned fields.

```{role} input(quiz-input)
:right: width: 8rem;
:check: trim lowercase
```
```{role} yes-no(quiz-select)
:right:
:options: |
: yes
: no
```
```{role} input100(quiz-input)
:style: width: 100%; margin-top: 0.25rem;
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
5.  {yes-no}`yes`{quiz-hint}`Be positive.`
    Are you sure about your previous answer?
4.  This input field uses the whole line. Guess what the answer is.
    {input100}`42`{quiz-hint}`You've seen this before.`
```

## Table

<script type="module">
const [core, quiz] = await tdoc.imports('tdoc/core.js', 'tdoc/quiz.js');

function sumProduct(max) {
    return () => {
        const va = core.randomInt(1, max), vb = core.randomInt(1, max);
        const div = Number.isInteger(vb / va) ? "divides" : "doesn't divide";
        return {
            va, vb,
            equal(other) { return va === other.va && vb === other.vb; },
            history: max ** 2 / 2,

            a(ph) { ph.textContent = `${va}`; },
            b(ph) { ph.textContent = `${vb}`; },
            sum(args) {
                args.ok = args.answer.trim() === (va + vb).toString();
            },
            product(args) {
                args.ok = args.answer.trim() === (va * vb).toString();
            },
            div(args) { args.ok = args.answer === div; }
        };
    };
}

quiz.generator('sumProduct', sumProduct(12));
</script>

Table-based quizzes can be generated dynamically, for drill exercises.

```{role} input(quiz-input)
:style: width: 3rem; text-align: center;
```
```{role} divides(quiz-select)
:options: |
: divides
: doesn't divide
```

```{quiz} table sumProduct
| $a$          | $b$          | $a + b$      | $a \cdot b$      | $a \| b$       |
| :----------: | :----------: | :----------: | :--------------: | :------------: |
| {quiz-ph}`a` | {quiz-ph}`b` | {input}`sum` | {input}`product` | {divides}`div` |
```
