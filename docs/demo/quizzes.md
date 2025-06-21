% Copyright 2024 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Quizzes

This section demonstrates interactive quizzes with the {rst:dir}`quiz`
directive and the {rst:role}`quiz-input` and {rst:role}`quiz-select` roles.

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
: Yes
: No
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
5.  {yes-no}`Yes`{quiz-hint}`Be positive.`
    Are you sure about your previous answer?
4.  This input field uses the whole line. Guess what the answer is.
    {input100}`42`{quiz-hint}`You've seen this before.`
```

## Table

<script type="module">
const [core, quiz] = await tdoc.imports('tdoc/core.js', 'tdoc/quiz.js');

function numbers(max) {
    return () => {
        const v = Math.floor(Math.random() * (max + 1));
        return {
            v,
            equal(other) { return v === other.v; },
            history: (max + 1) / 2,

            value(ph) { ph.textContent = `${v}`; },
            parity(args) {
                args.ok = {'odd': 1, 'even': 0}[args.answer] === v % 2;
                args.hint = "Look at the last digit.";
            },
            opposite(args) {
                args.ok = args.answer.trim() === (-v).toString();
                args.hint = "Put a \"-\" in front.";
            },
        };
    };
}

quiz.generator('numbers', numbers(99));
</script>

Table-based quizzes can be generated dynamically, for drill exercises.

```{role} odd-even(quiz-select)
:options: |
: odd
: even
```
```{role} input(quiz-input)
:style: width: 5rem;
```

```{quiz} table numbers
| Value            | Parity             | Opposite          |
| :--------------: | :----------------: | :---------------: |
| {quiz-ph}`value` | {odd-even}`parity` | {input}`opposite` |
```
