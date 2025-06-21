% Copyright 2024 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Quiz

````{rst:directive} .. quiz::
This directive adds an interactive quiz. It can contain arbitrary text and
markup, as well as {rst:role}`quiz-input` and {rst:role}`quiz-select` roles to
indicate where input fields should be placed and what the solutions are. The
toolbar on the right allows controlling the quiz.

- <button class="tdoc fa-check"></button>: Check the provided answers. When all
  the answers are correct, the button turns green and the quiz is locked.

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

## Fields

`````{rst:role} quiz-input
This role defines an `<input type="text">`{l=html} field. The text of the role
is the solution for the field. The role normally isn't used as-is; instead,
custom roles are derived from it with the
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

Note that such custom roles only apply to the document in which they are
defined, and can be redefined multiple times in the same document.

{.rubric}
Options

See the [common field options](#quiz-common) below.
`````

`````{rst:role} quiz-select
This role defines a `<select>`{l=html} field. The text of the role is the
solution for the field. The role cannot be used as-is; custom roles must be
derived from it with the
[`role`](https://docutils.sourceforge.io/docs/ref/rst/directives.html#role)
directive, to set the selectable options wih `:options:`, and optionally to
control the appearance and behavior of the fields.

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

Note that such custom roles only apply to the document in which they are
defined, and can be redefined multiple times in the same document.

{.rubric}
Options

See the [common field options](#quiz-common) below.

````{rst:directive:option} options: option [option ...]
:type: one line per option
Defines the selectable options, one option per line. This requires using
[multi-line options](https://myst-parser.readthedocs.io/en/latest/syntax/roles-and-directives.html#parameterizing-directives-options), by starting the
value with `|` to preserve newlines.
````
`````

{#quiz-common}
### Common field options

````{rst:directive:option} check: name [name ...]
:type: IDs
A list of checks to apply to answers and / or solutions to check if they match.
The following built-in checks are available:

- `default`: The default check. Equivalent to `trim`.
- `split`: Split the solution at commas (`,`). This changes the solution to an
  `Array` of strings.
- `trim`: Trim whitespace at the beginning and end of the answer and solution.
- `remove-whitespace`: Remove all whitespace from the answer and solution.
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
    `ok` is set to `true` iff the result is `true`. Moreover, if the result is a
    string, it is assigned to `hint`.

Custom checks can be implemented by importing the `tdoc/quiz.js` module and
extending the `checks` object. Check functions take a single argument, an object
that they can inspect and modify as necessary. The following attributes are set
and / or evaluated:

- `answer` (string): Pre-populated with the answer provided by the user.
- `solution` (string): Pre-populated with the solution for the field.
- `field`: The DOM object of the field.
- `role` (string): The name of the role that created the field.
- `ok` (boolean): Whether the answer matches the solution. Checking terminates
  once this field is set.
- `hint` (string): A hint to display to the user if the answer isn't correct.
- `invalid` (string): An error message to display, indicating an error in the
  check.

The example below defines a check named `no-whitespace` that removes whitespace
from the answer.

```{code-block} html
<script type="module">
const quiz = await tdoc.import('tdoc/quiz.js');
quiz.checks['no-whitespace'] = args => {
    args.answer = args.answer.replace(/\s+/g, '');
};
</script>
```
````
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
