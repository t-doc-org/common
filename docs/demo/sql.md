<!-- Copyright 2024 Caroline Blank <caro@c-space.org> -->
<!-- Copyright 2024 Remy Blank <remy@c-space.org> -->
<!-- SPDX-License-Identifier: MIT -->

# SQL

```{admonition} Do not use yet
:class: warning
The functionality described on this page is still in development and its API is
unstable.
```

## Query

```{exec} sql
:name: sql-table-def
create table countries (
    country text not null,
    country_code text not null,
    dial_code text not null,
    capital text not null,
    population int not null,
    comment text
);
insert into countries values
    ('Switzerland', 'CH', '+41', 'Bern', 8776000, 'Fondue!'),
    ('France', 'FR', '+33', 'Paris', 67970000, null),
    ('Germany', 'DE', '+49', 'Berlin', 83800000, null),
    ('Italy', 'IT', '+39', 'Rome', 58940000, null),
    ('Austria', 'AT', '+43', 'Vienna', 9042000, null),
    ('Lichtenstein', 'LI', '+423', 'Vaduz', 39327, null);
select * from countries;
```

## Empty query result

```{exec} sql
create table countries (
    country text not null,
    country_code text not null,
    dial_code text not null,
    capital text not null,
    population int not null,
    comment text
);
select * from countries;
```

## SQL error

```{exec} sql
select * from unknown_table;
```
