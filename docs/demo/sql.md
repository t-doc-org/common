<!-- Copyright 2024 Caroline Blank <caro@c-space.org> -->
<!-- Copyright 2024 Remy Blank <remy@c-space.org> -->
<!-- SPDX-License-Identifier: MIT -->

# SQL

The `{exec} sql` block allows executing SQL directly in the browser. Each block
is executed in a new, empty database.

## Directive

````{rst:directive} .. {exec}:: language (sql)
This directive is a `{code-block}` that allows executing the code directly in
the browser. It supports all the options of `{code-block}`, and a few more
described below.

{.rubric}
Options
```{rst:directive:option} after: name
:type: text
References an `{exec}` block to be executed before this block, in the same
environment. The referenced block can itself have an `:after:` option, forming
a chain of blocks to execute in the environment.
```
```{rst:directive:option} when: value
:type: click | load | never
Determines when the block's code is executed: on a click by the user (`click`),
when the page loads (`load`) or not at all (`never`).
```
````

## Database definition

A database can be defined as a named `{exec} sql` block, to be referenced in the
`:after:` option of other blocks.

```{exec} sql
:name: sql-countries
:when: never
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

## Queries

The results of the first `select` statement in an `{exec} sql` block are
displayed as a table.

```{exec} sql
:after: sql-countries
:when: load
select * from countries;
```

The SQL code can be hidden by adding `:class: hidden`.

```{exec} sql
:after: sql-countries
:when: load
:class: hidden
select * from countries where country_code = 'CH';
```

### Empty results

```{exec} sql
:after: sql-countries
:when: load
select * from countries where false;
```

## Mutations

```{exec} sql
:after: sql-countries
:when: load
update countries set food = 'baguette' where country_code = 'FR';
select * from countries where country_code = 'FR';
```

## SQL errors

```{exec} sql
:when: load
select * from unknown_table;
```

## Execution trigger

By default, `{exec} sql` blocks are executed on click (`:when: click`), with
controls displayed next to the block.

```{exec} sql
:after: sql-countries
select * from countries where country_code = 'LI';
```

They can also be executed immediately on load (`:when: load`) or not at all
(`:when: never`, useful for database definitions that are referenced by other
blocks). In these cases, no controls aren displayed.
