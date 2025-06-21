% Copyright 2024 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Quiz

````{rst:directive} .. quiz:: [type [arg ...]]
This directive adds an interactive quiz. The quiz questions are laid out with
markup, and user input fields are placed with {rst:role}`quiz-input` and
{rst:role}`quiz-select` roles. The following [quiz types](#types) are supported:

- [`static`](#static) (default): A quiz with static answers.
- [`table`](#table): A table-based quiz with dynamically generated questions.

The <button class="tdoc fa-check"></button> button checks the provided answers.
It turns green when all the answers are correct, and all the quiz is locked.

{.rubric}
Options
```{rst:directive:option} class: name [name...]
:type: IDs
A space-separated list of CSS classes to add to the outer container.
```
```{rst:directive:option} style: property: value; [property: value; ...]
CSS styles to apply to the outer container, e.g. `max-width: 30rem;`.
```
````

## Types

### Static

Static quizzes have a fixed set of questions. They can contain arbitrary markup,
interspersed with {rst:role}`quiz-input` and {rst:role}`quiz-select` roles to
indicate where the input fields should be placed and what the answers should be.

### Table

Table quizzes (`{quiz} table`) dynamically generate questions: when a question
is answered correctly, a new question is generated below. The {rst:dir}`quiz` argument after the type is the name of a [generator function](#generator)
registered with `quiz.generator()`.

The directive must contain a table consisting of one or more template rows
containing {rst:role}`quiz-ph` placeholders for the variable parts of the
question, and {rst:role}`quiz-input` and {rst:role}`quiz-select` roles for the
input fields. The text of the placeholder and field roles is an identifier to be
looked up in the object returned by the [generator function](#generator).

````{code-block}
```{role} input(quiz-input)
:style: width: 3rem; text-align: center;
```

```{quiz} table sumProduct
| $a$          | $b$          | $a + b$      | $a \cdot b$      |
| :----------: | :----------: | :----------: | :--------------: |
| {quiz-ph}`a` | {quiz-ph}`b` | {input}`sum` | {input}`product` |
```
````

## Placeholder

`````{rst:role} quiz-ph
This role defines a placeholder for a variable part of a question in a
dynamically generated quiz. The text of the role is an identifier to be looked
up in the object returned by the [question generator]
`````

## Field

`````{rst:role} quiz-input
This role defines an `<input type="text">`{l=html} field. The role normally
isn't used as-is; instead, custom roles are derived from it with the
[`role`](https://docutils.sourceforge.io/docs/ref/rst/directives.html#role)
directive, which allows controlling the appearance and behavior of the fields.

For example, the following block defines an `input` role that places quiz inputs
having a width of `3rem` and aligning their text centered. The `input` role can
then be used in {rst:dir}`quiz` directives that follow its definition.

````{code-block}
```{role} input(quiz-input)
:style: width: 3rem; text-align: center;
```

```{quiz}
| $a$ | $b$ | $a + b$    |
| :-: | :-: | :--------: |
|  1  |  2  | {input}`3` |
```
````

Note that custom roles only apply to the document in which they are defined, and
can be redefined multiple times in the same document.

{.rubric}
Options

See the [common field options](#common) below.
`````

`````{rst:role} quiz-select
This role defines a `<select>`{l=html} field. The role cannot be used as-is;
custom roles must be derived from it with the
[`role`](https://docutils.sourceforge.io/docs/ref/rst/directives.html#role)
directive, to set the selectable options wih `:options:`, and optionally to
control the appearance and behavior of the field.

For example, the following block defines a `select` role that provides two
options `false` and `true`. The `select` role can then be used in
{rst:dir}`quiz` directives that follow its definition.

````{code-block}
```{role} select(quiz-select)
:options: |
: false
: true
```

```{quiz}
| a    | b     | a or b         | a and b         |
| :--: | :---: | :------------: | :-------------: |
| true | false | {select}`true` | {select}`false` |
```
````

Note that custom roles only apply to the document in which they are defined, and
can be redefined multiple times in the same document.

{.rubric}
Options

See the [common field options](#common) below.

````{rst:directive:option} options: option [option ...]
:type: one line per option
Defines the selectable options, one option per line. This requires using
[multi-line options](https://myst-parser.readthedocs.io/en/latest/syntax/roles-and-directives.html#parameterizing-directives-options), by starting the
value with `|` to preserve newlines.
````
`````

{#common}
### Common field options

```{rst:directive:option} check: name [name ...]
:type: IDs
A list of [check functions](#check) to apply when checking the answer for the
field. The functions are applied in order.
```
```{rst:directive:option} right: [property: value; ...]
Moves the field to the right of the question text, by applying a `float: right;`
style. When using this option, **the role must be placed before the question
text**, otherwise it may be vertically misaligned.

Additional styles can optionally be provided as the value of the option, e.g.
`width: 10rem;`.
```
```{rst:directive:option} style: property: value; [property: value; ...]
CSS styles to apply to the field, e.g. `width: 10rem;`.
```

{#generator}
## Generator function

A generator function generates a new question for a dynamically generated quiz.
It must be given a name with `quiz.generator()`, so that it can be referenced
from {rst:dir}`quiz` directives. It takes no arguments and returns a question
object with the following attributes:

- One function per {rst:role}`quiz-ph`, named after the text of the role. The
  function receives the empty
  [`HTMLSpanElement`](https://developer.mozilla.org/en-US/docs/Web/API/HTMLSpanElement)
  corresponding to the placeholder as an argument, and must modify it to set the
  variable part (e.g. set its `textContent`).

- One [check function](#check) per {rst:role}`quiz-input` and
  {rst:role}`quiz-select` role, named after the text of the role.

- An optional `equal()` function taking a previous question object and returning
  `true` iff they are equal. If this attribute is present, new questions are
  compared to previous ones and rejected if they compare equal. This avoids
  generating duplicates.

- An optional `history` value specifying how far back to check for duplicates
  when generating a new question.

```{code-block} html
<script type="module">
const [core, quiz] = await tdoc.imports('tdoc/core.js', 'tdoc/quiz.js');

function sumProduct(max) {
    return () => {
        const va = core.randomInt(1, max), vb = core.randomInt(1, max);
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
        };
    };
}

quiz.generator('sumProduct', sumProduct(12));
</script>
```

{#check}
## Check function

A check function checks the user-provided answer for one field. It takes a
single argument, an object that contains the following attributes:

- `role` (string): The name of the role that created the field.
- `text` (string): The text of the role that created the field.
- `field`: The DOM object of the field.
- `answer` (string): Initially populated with the answer provided by the user.
- `solution` (string): Initially populated with the text of the role.

The check function can modify the existing attributes above, for use by the next
check function. It can also set the following attributes:

- `ok` (boolean): Whether the answer matches the solution. Checking terminates
  once this field is set.
- `hint` (string): A hint to display to the user if the answer isn't correct.
- `invalid` (string): An error message to display, indicating an error in the
  check.

Check functions referenced by {rst:role}`quiz-input` and {rst:role}`quiz-select`
roles must be given a name with `quiz.check()`. They take a second argument
containing the optional parameter from the reference. The following built-in
checks are pre-defined:

- `default`: The default check. Equivalent to `trim`.
- `split()`: Split the solution at instances of the parameter (`,` by default).
  This changes the solution to an `Array` of strings.
- `trim`: Trim whitespace at the beginning and end of the answer and solution.
- `remove()`: Remove all instances of the
  [regexp](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Regular_expressions)
  specified as a parameter (`\s+` by default, i.e. remove all whitespace) from
  the answer and solution.
- `lowercase`: Convert the answer and solution to lowercase.
- `uppercase`: Convert the answer and solution to uppercase.
- `json`: Parse the solution as JSON, and set the result as the new solution.
- `equal`: Compare the answer to the solution. This check is evaluated after all
  other checks if none of them has set the `ok` or `invalid` attributes, so it
  usually doesn't need to be specified.
  - If the solution is a string, `ok` is set to `true` iff the answer and
    solution compare equal.
  - If the solution is an `Array`, `ok` is set to `true` iff the array includes
    the answer.
  - If the solution is an object, the answer is looked up in the object, and
    `ok` is set to `true` iff the result is `true`. If the result is a string,
    it is assigned to `hint`.


The following example re-implements the built-in `split` check.

```{code-block} html
<script type="module">
const [quiz] = await tdoc.imports('tdoc/quiz.js');

quiz.check('split', (args, param = ',') => {
    args.solution = args.solution.split(param);
});
</script>
```

## Field hint

`````{rst:role} quiz-hint
This role defines a hint to display when the answer for a field is wrong. It
must be placed **immediately after** the field for which it provides a hint,
with only whitespace between them.

````{code-block}
```{role} input(quiz-input)
:right: width: 5rem;
```

```{quiz}
1.  {input}`42`{quiz-hint}`It's a number between 40 and 50.`
    What is the answer to the ultimate question of life, the universe, and
    everything?
```
````
`````
