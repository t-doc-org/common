% Copyright 2024 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Elements

## Document metadata

````{rst:directive} .. metadata::
This directive allows adding document metadata to a page. The content of the
directive is a [YAML](https://yaml.org/) document which is converted to a Python
{py:class}`dict` and merged into the document metadata.

In addition to Sphinx-specific
[metadata fields](https://www.sphinx-doc.org/en/master/usage/restructuredtext/field-lists.html#special-metadata-fields), the following top-level keys are
interpreted.

`exec`
: A mapping of per-language configuration for client-side code execution.

  ```{code-block} yaml
  exec:
    python:
      packages: [sqlite3]
  ```

`scripts`
: A list of scripts to reference from the page header through `<script>`{l=html}
  elements. The list items can be either strings (the URL of the script) or
  maps. For maps, the `src` key specifies the URL of the script, and other keys
  are added to the `<script>`{l=html} element. Relative URLs are resolved
  relative to the `_static` directory.

  ```{code-block} yaml
  scripts:
    - classic-script.js
    - src: module-script.js
      type: module
    - https://code.jquery.com/jquery-3.7.1.min.js
  ```

`styles`
: A list of CSS stylesheets to reference from the page header through
  `<link>`{l=html} elements. The list items can be either strings (the URL of
  the stylesheet) or maps. For maps, the `src` key specifies the URL of the
  stylesheet, and other keys are added to the `<link>`{l=html} element. Relative
  URLs are resolved relative to the `_static` directory.

  ```{code-block} yaml
  styles:
    - custom-styles.css
    - src: print-styles.css
      media: print
    - https://example.com/styles.css
  ```
````

## Default directive options

`````{rst:directive} .. defaults:: directive
This directive sets default options for a directive type for the current
document, starting from the current location. All directives of the given type
that follow the {rst:dir}`defaults` block take their default option values from
that block. Options that are specified in the directive itself override the
default.

A document can contain multiple {rst:dir}`defaults` blocks for the same
directive type. Each occurrence replaces the previous one, i.e. they don't
combine.

````{code-block}
```{exec} python
# Use the directive's default options
```

```{defaults} exec
:when: load
:class: hidden
```

```{exec} python
# Use ':when: load' and ':class: hidden'
```

```{exec} python
:when: click
# Use ':when: click' and ':class: hidden'
```

```{defaults} exec
:when: never
```

```{exec} python
# Use ':when: never' and no :class:
```
````
`````

## Solution

````{rst:directive} .. solution:: [title]
This directive adds an admonition of type `solution`. The title defaults to
"Solution", and the body is collapsed by default.

The `solutions:` key in the [document metadata](#document-metadata) controls how
solutions are displayed.

- `show` (default): Solutions are shown on the page.
- `hide`: Solutions are hidden when the page loads. They can be shown or hidden
  with the <button class="tdoc fa-eye"></button> /
  <button class="tdoc fa-eye-slash"></button> button in the navbar.
- `dynamic`: Solutions are hidden by default, but can be made visible to
  everyone in real-time by members of the group `solutions:show` using the
  <button class="tdoc fa-eye"></button> /
  <button class="tdoc fa-eye-slash"></button> button.

{.rubric}
Options
```{rst:directive:option} class: name [name...]
:type: IDs
A space-separated list of CSS classes to add to the admonition. The default is
`note dropdown`.
```
```{rst:directive:option} name: name
:type: ID
A reference target for the admonition.
```
```{rst:directive:option} expand
When set, the admonition is expanded by default.
```
```{rst:directive:option} show
When set, the admonition is always shown, even if solutions are hidden or
removed.
```
````

## IFrame

````{rst:directive} .. youtube:: id
This directive adds an
[`<iframe>`](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/iframe)
element loading a YouTube video. The argument is the ID of the video, e.g.
`aVwxzDHniEw`. All the options of {rst:dir}`iframe` are supported.
````

`````{rst:directive} .. iframe:: url
This directive adds an
[`<iframe>`](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/iframe)
element loading the given URL.

{.rubric}
Options
````{rst:directive:option} allow: directive; [directive; ...]
The
[permission policy](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/iframe#allow)
for the `<iframe>`{l=html}
([supported directives](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Permissions-Policy#directives)).
The default is:

```
autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture;
  screen-wake-lock; web-share
```
````

```{rst:directive:option} class: name [name...]
:type: IDs
A space-separated list of CSS classes to add to the `<iframe>`{l=html}.
```
```{rst:directive:option} credentialful
Indicate that the `<iframe>`{l=html} should **not** be loaded in
[credentialless](https://developer.mozilla.org/en-US/docs/Web/Security/IFrame_credentialless) mode. The default is credentialless mode.
```
```{rst:directive:option} referrerpolicy: value
Indicate the referrer to send when fetching the `<iframe>`{l=html} source
([supported values](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/iframe#referrerpolicy)).
```
```{rst:directive:option} sandbox: token [token ...]
Control the restrictions applied to the content embedded in the
`<iframe>`{l=html}
([supported tokens](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/iframe#sandbox)).
```
```{rst:directive:option} style: property: value; [property: value; ...]
CSS styles to apply to the `<iframe>`{l=html}, e.g. `width: 80%;`.
```
```{rst:directive:option} title: text
A concise description of the content of the `<iframe>`{l=html}, typically used
by assistive technologies.
```
`````

## Code execution

See "[](exec.md)".

## Numbering

````{rst:role} num
This role performs automatic numbering, optionally creating reference targets.
The role content is either a label (e.g. `` {num}`label` ``) or an explicit
title and a label (e.g. `` {num}`Exercise %s<label>` ``). In the latter case,
the title must contain the string `%s`, which gets substituted with the number.

The label is composed of a counter identifier and an optional target name,
separated by `:`. Distinct identifiers are numbered separately, and the counters
persist across pages. Instances with a target (e.g. `` {num}`ex:target` ``) can
be referenced with the {rst:role}`numref` role (e.g. `` {numref}`ex:target` ``).

```{code-block}
## Exercise {num}`ex:intro`

As an introduction to ...

## Exercise {num}`ex`

After completing {numref}`exercise %s<ex:intro>`, ...
```
````

## Quiz

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

### Field roles

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
#### Common field options

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

## Poll

````{rst:directive} .. poll:: id
This directive adds a live audience poll. The poll identifier `id` is required
and its value must be unique across the site. The content of the directive is
composed of the question, followed by a bullet list, where each list item
becomes an answer. Both the question and the answers can contain arbitrary
markup. Answers can optionally be marked as solutions by prefixing them with `:`
(the prefix is removed).

Polls can be controlled by members of the group `polls:control`, using the
buttons in the toolbar.

- <button class="tdoc fa-play"></button> /
  <button class="tdoc fa-stop"></button>: Open or close the poll. Closed polls
  don't accept votes.
- <button class="tdoc fa-eye"></button> /
  <button class="tdoc fa-eye-slash"></button>: Show or hide the poll results.
- <button class="tdoc fa-check"></button> /
  <button class="tdoc fa-xmark"></button>: Show or hide the solutions.
- <button class="tdoc fa-trash"></button>: Clear the poll results.

Voting on polls doesn't require any permissions. Polls are single-choice by
default ({rst:dir}`:mode: single <poll:mode>`): selecting a different answer
de-select a previously selected one, and re-selecting the selected answer
un-selects it. Setting {rst:dir}`:mode: multi <poll:mode>` enables voters to
select multiple answers.

{.rubric}
Options
```{rst:directive:option} mode: value
:type: single | multi
The poll mode: single answer (`single`, the default) or allow multiple answers
(`multi`).
```
```{rst:directive:option} number: value
:type: none | decimal | lower-alpha | upper-alpha
The answer numbering: no numbering (`none`), using decimal numbers (`decimal`),
using lowercase letters (`lower-alpha`) or using uppercase letters
(`upper-alpha`, the default).
```
```{rst:directive:option} close-after: value
:type: duration | never
The duration after opening when the poll should be closed automatically. The
value is of the form `2h35m42s` or `never`. The default is 15 minutes.
```
```{rst:directive:option} class: name [name...]
:type: IDs
A space-separated list of CSS classes to add to the outer container.
```
````
