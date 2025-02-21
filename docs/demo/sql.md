% Copyright 2024 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# SQL

The [`{exec} sql`](../reference/exec.md#sql) directive allows executing SQL
in the browser. Each block is executed in a new, empty database.

```{exec} sql
:when: load
:class: hidden
select concat('SQLite ', sqlite_version()) as Database;
```

## Database definition

A database can be defined as a named [`{exec} sql`](../reference/exec.md#sql)
block, to be referenced in the {rst:dir}`:after: <exec:after>` option of other
blocks.

```{exec} sql
:name: sql_countries
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

```{defaults} exec
:after: sql_countries
:when: load
```

## Queries

The results of the **first** `select` statement in each
[`{exec} sql`](../reference/exec.md#sql) block of the
{rst:dir}`:after: <exec:after>` and {rst:dir}`:then: <exec:then>`
[sequence](../reference/exec.md#sequencing) are displayed as tables.

```{exec} sql
:editor:
select * from countries;
```

The SQL code can be hidden by adding `:class: hidden`.

```{exec} sql
:class: hidden
select * from countries where country_code = 'CH';
```

### Empty results

```{exec} sql
select * from countries where false;
```

### Wide results

```{exec} sql
:name: sql-wide
:when: never
:class: hidden
create table wide (
  column0 text,
  column1 text,
  column2 text,
  column3 text,
  column4 text,
  column5 text,
  column6 text,
  column7 text,
  column8 text,
  column9 text,
  column10 text,
  column11 text,
  column12 text,
  column13 text,
  column14 text,
  column15 text
);
```
```{exec} sql
:after: sql-wide
:when: click
select * from wide;
```

### Tall results

The height of large results tables can be limited with `:output-style:`.

```{exec} sql
:name: sql-tall
:when: never
:class: hidden
create table tall (value integer);
insert into tall values (0), (1), (2), (3), (4), (5), (6), (7);
```
```{exec} sql
:after: sql-tall
:when: click
:output-style: max-height: 10rem
select t1.value, t2.value from tall as t1, tall as t2;
```

## Mutations

```{exec} sql
:editor:
update countries set food = 'baguette' where country_code = 'FR';
select * from countries where country_code = 'FR';
```

## SQL errors

```{exec} sql
select * from unknown_table;
```
