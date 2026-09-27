import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / 'data' / 'library.sqlite3'

SCHEMA = '''
CREATE TABLE IF NOT EXISTS books (
 id INTEGER PRIMARY KEY, title TEXT NOT NULL, author TEXT NOT NULL,
 source TEXT NOT NULL, words INTEGER NOT NULL CHECK(words > 0),
 digest TEXT NOT NULL UNIQUE, excerpt TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS terms (id INTEGER PRIMARY KEY, word TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS postings (
 term_id INTEGER REFERENCES terms(id), book_id INTEGER REFERENCES books(id),
 count INTEGER NOT NULL CHECK(count > 0), PRIMARY KEY(term_id, book_id)
) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS postings_book ON postings(book_id);
CREATE TABLE IF NOT EXISTS edges (
 a INTEGER REFERENCES books(id), b INTEGER REFERENCES books(id),
 similarity REAL NOT NULL, PRIMARY KEY(a,b), CHECK(a < b)
) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS edges_b ON edges(b);
CREATE TABLE IF NOT EXISTS scores (book_id INTEGER PRIMARY KEY REFERENCES books(id), score REAL NOT NULL);
CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
'''


def connect(path=DEFAULT_DB):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys=ON')
    connection.execute('PRAGMA journal_mode=WAL')
    connection.executescript(SCHEMA)
    return connection
