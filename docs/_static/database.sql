create table kv (key text primary key, value any) strict;
insert into kv values ('foo', 'bar');
insert into kv values ('baz', 'quux');
