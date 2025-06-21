% Copyright 2024 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Poll

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
