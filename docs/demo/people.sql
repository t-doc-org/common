create table people (
  first_name text not null,
  last_name text not null,
  height real,
  favorite_food text
);
insert into people values
  ('Joe', 'Bar', 1.83, null),
  ('Jack', 'Smith', 1.55, 'burgers'),
  ('Jim', 'Davis', null, 'pizza'),
  ('Anthony', 'Miller', 1.78, null);
