-- Add migration script here
create table images (
    id blob primary key not null,
    data blob not null,
    date INTEGER not null -- unix epoc
)
