% Copyright 2024 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Quizzes

This page demonstrates interactive quizzes with the {rst:dir}`quiz` directive
and the {rst:role}`quiz-ph`, {rst:role}`quiz-input`, {rst:role}`quiz-select` and
{rst:role}`quiz-hint` roles.

## Static

<script type="module">
const [core, quiz] = await tdoc.import('tdoc/core.js', 'tdoc/quiz.js');

quiz.checks.sum = args => {
  const tds = core.qsa(args.field.closest('tr'), 'td');
  const solution = +tds[0].textContent + (+tds[1].textContent)
  args.ok = args.answer === solution.toString();
  args.hint = `The answer is probably ${solution}.`;
};
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

`````{quiz}
{.lower-alpha-paren}
1.  {input}`42`{quiz-hint}`It's a positive integer.`
    Calculate $6 \cdot 7 $.
2.  {input}`42`{quiz-hint}`It's composed of digits from 0 to 9.`
    {input}`2a`{quiz-hint}`It's composed of digits from 0 to f.`
    Convert $00101010_2$ to decimal and hexadecimal.
3.  {input}`42`{quiz-hint}`It's a number.`
    What is the answer to the ultimate question of life, the
    universe, and everything? Explain your reasoning in full detail, provide
    references, and indicate plausible alternatives.
4.  {yes-no}`yes`{quiz-hint}`Be positive.`
    Are you sure about your previous answer?
5.  This input field uses the whole line. Guess what the answer is.
    {input100}`42`{quiz-hint}`You've seen this before.`
6.  What is the capital of Switzerland?
    ```{quiz-check}
    :class: columns-3
    :hint: The answer might surprise you.
    - Berlin
    - Zürich
    - Paris
    - Bern
    - Geneva
    - :None of the above
    ```
7.  ```{quiz-check}
    :multi:
    :class: columns-2
    :hint: It should have an x squared, and no funny functions.
    :right:
    - $2x + 3$
    - :$5x^2 + 3x - 7$
    - $2sin(x^2) + \frac{5}{x}$
    - :$ax^2 + bx + c$
    ```
    Which of the following are second-order polynoms?
8.  ```{defaults} quiz-check
    :multi:
    :randomize:
    :class: columns-3
    :right: width: 60%;
    ```
    ```{quiz-check}
    - :$x = 30°$
    - $x = 45°$
    - :$x = \frac{\pi}{6}$
    ```
    $sin(x) = \frac{1}{2}$
9.  ```{quiz-check}
    - $x = 45°$
    - :$x = \frac{\sqrt{2}}{2}$
    - :$x = sin(\frac{\pi}{4})$
    ```
    $cos(\frac{\pi}{4}) = x$
10. ```{quiz-check}
    - $x = 30°$
    - :$x = 60°$
    - :$x = 240°$
    ```
    $tan(x) = \sqrt{3}$
11. ```{defaults} quiz-check
    ```
    Which program prints the numbers from 1 to 5?
    ````{quiz-check}
    :randomize:
    :style: display: grid; grid-template-columns: 1fr 1fr;
    - ```{exec} python
      :linenos:
      for i in range(5):
        print(i)
      ```
    - :
      ```{exec} python
      :linenos:
      i = 0
      while i < 5:
        i += 1
        print(i)
      ```
    ````
`````

## Table

<script type="module">
const [core, quiz] = await tdoc.import('tdoc/core.js', 'tdoc/quiz.js');

quiz.generators.sumProduct = () => {
  const max = 12, va = core.randomInt(1, max), vb = core.randomInt(1, max);
  const div = Number.isInteger(vb / va) ? "divides" : "doesn't divide";
  return {
    va, vb,
    equal(other) { return this.va === other.va && this.vb === other.vb; },
    history: max ** 2 / 2,

    a(ph) { ph.textContent = `${va}`; },
    b(ph) { ph.textContent = `${vb}`; },
    sum(args) { args.ok = args.answer.trim() === (va + vb).toString(); },
    product(args) { args.ok = args.answer.trim() === (va * vb).toString(); },
    div(args) { args.ok = args.answer === div; }
  };
};

quiz.generators.numbers = () => {
  const max = 99, vn = core.randomInt(0, 99);
  const multiple = m => args => { args.ok = +args.answer === +(vn % m === 0); };
  const interval = (l, u) => args => {
    args.ok = +args.answer === +(l <= vn && vn < u);
  };
  return {
    vn,
    equal(other) { return this.vn === other.vn; },
    history: max / 2,

    n(ph) { ph.textContent = `${vn}`; },
    multiple_0: multiple(2), multiple_1: multiple(3),
    multiple_2: multiple(5), multiple_3: multiple(9),
    interval_0: interval(0, 25), interval_2: interval(50, 75),
    interval_1: interval(25, 50), interval_3: interval(75, 100),
  };
};
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

Table-based quizzes that use {rst:dir}`quiz-check` must be created with
`{list-table}`, as Markdown tables cannot contain directives.

<style>
.numbers-quiz :is(th, td) {
  text-align: center;
}
</style>

```{defaults} quiz-check
```

`````{quiz} table numbers
````{list-table}
:header-rows: 1
:class: numbers-quiz
- - $n$
  - Multiple of
  - In interval
- - {quiz-ph}`n`
  - ```{quiz-check} multiple
    :multi:
    :class: columns-4
    - 2
    - 3
    - 5
    - 9
    ```
  - ```{quiz-check} interval
    :class: columns-2
    - $n \in \left[0; 25\right[$
    - $n \in \left[25; 50\right[$
    - $n \in \left[50; 75\right[$
    - $n \in \left[75; 100\right[$
    ```
````
`````
