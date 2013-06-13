PRAGMA foreign_keys=ON;

CREATE TABLE tags(
    id INTEGER primary key AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE bookmark(
    id INTEGER primary key AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    title TEXT UNIQUE NOT NULL
);

CREATE TABLE bookmark_tags(
    id INTEGER primary key AUTOINCREMENT,
    tag_id INT, 
    bookmark_id INT,
    date_added INT,
    FOREIGN KEY(bookmark_id) REFERENCES bookmark(id) ON DELETE CASCADE,
    UNIQUE (tag_id,bookmark_id)
);
