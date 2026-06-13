-- schema.sql  —  Bookshelf Service with user accounts
-- Run with: psql -U <user> -d <dbname> -f schema.sql

-- ── Drop in reverse FK order ─────────────────────────────────────────────────
DROP TABLE IF EXISTS books;
DROP TABLE IF EXISTS users;

-- ── Users ────────────────────────────────────────────────────────────────────
CREATE TABLE users (
    id            SERIAL PRIMARY KEY,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,           -- bcrypt hash
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ── Books (each row belongs to one user) ─────────────────────────────────────
CREATE TABLE books (
    id        SERIAL PRIMARY KEY,
    user_id   INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title     VARCHAR(255) NOT NULL,
    author    VARCHAR(255) NOT NULL,
    year      INTEGER      NOT NULL,
    rating    NUMERIC(3,1) CHECK (rating >= 0.0 AND rating <= 5.0),
    added_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Index so "SELECT * FROM books WHERE user_id = ?" is fast
CREATE INDEX idx_books_user_id ON books(user_id);
