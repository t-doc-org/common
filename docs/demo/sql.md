<!-- Copyright 2024 Remy Blank <remy@c-space.org> -->
<!-- SPDX-License-Identifier: MIT -->

# SQL

The `{exec} sql` block allows executing SQL directly in the browser. Each block
is executed in a new, empty database.

```{exec} sql
:when: load
:class: hidden
select concat('SQLite ', sqlite_version()) as Database;
```

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
:editable:
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
:editable:
update countries set food = 'baguette' where country_code = 'FR';
select * from countries where country_code = 'FR';
```

## SQL errors

```{exec} sql
:when: load
select * from unknown_table;
```
