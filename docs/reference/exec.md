<!-- Copyright 2024 Remy Blank <remy@c-space.org> -->
<!-- SPDX-License-Identifier: MIT -->

# Code excution

The `{exec}` directive allows executing code directly in the browser.

```{exec} sql
:name: sql-countries
:when: never
:class: hidden
create table countries (
  country text not null,
  country_code text not null,
  dial_code text not null,
  capital text not null,
  population int not null,
  food text
);
insert into countries values
  ('Switzerland', 'CH', '+41', 'Bern', 8776000, 'fondue!'),
  ('France', 'FR', '+33', 'Paris', 67970000, null),
  ('Germany', 'DE', '+49', 'Berlin', 83800000, null),
  ('Italy', 'IT', '+39', 'Rome', 58940000, null),
  ('Austria', 'AT', '+43', 'Vienna', 9042000, 'Kaiserschmarrn'),
  ('Lichtenstein', 'LI', '+423', 'Vaduz', 39327, null);
```

## Directive

````{rst:directive} .. {exec}:: language (python | sql)
This directive is a [`{code-block}`](https://mystmd.org/guide/code#code-blocks)
that allows executing the code directly in the browser. It supports most of the
options of `{code-block}`, and a few more described below.

{.rubric}
Options
```{rst:directive:option} after: name [name...]
:type: IDs
Execute one or more `{exec}` blocks before this block, in the same environment.
```
```{rst:directive:option} editable
Make the `{exec}` block editable.
```
```{rst:directive:option} include: path [path...]
:type: relative paths
Prepend the content of one or more files to the block's content.
```
```{rst:directive:option} when: value
:type: click | load | never
Determine when the block's code is executed: on user request (`click`, the
default), when the page loads (`load`) or not at all (`never`).
```
````

## Execution trigger

By default, `{exec}` blocks are executed on click (`:when: click`), with
controls displayed next to the block.

```{exec} sql
:after: sql-countries
select * from countries where country_code = 'LI';
```

They can also be executed immediately on load (`:when: load`) or not at all
(`:when: never`, useful for definitions that are referenced by other blocks).
The controls displayed depend on the type of block.

```{exec} sql
:after: sql-countries
:when: load
select * from countries where country_code = 'LI';
```

## Editable blocks

Blocks can be made editable with the `:editable:` option.

```{exec} sql
:after: sql-countries
:editable:
select * from countries
  where population > 10000000
  order by country_code;
```

## Dependencies

The `:after:` option allows referencing one or more `{exec}` blocks on the same
page to be executed before a block, in the same environment. The referenced
blocks can themselves have an `:after:` option, forming a tree of blocks to
execute in the environment. If a block appears on more than one tree branch,
only the first occurrence is executed.

## Include file content

The `:include:` option allows including the content of one or more external
files. The content of the files is prepended to the block's content.

```{exec} sql
:include: people.sql
select * from people;
```
