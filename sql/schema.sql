-- schema.sql  —  Bookshelf Service with user accounts
-- Run with: psql -U <user> -d <dbname> -f schema.sql

-- ── Drop in reverse FK order ─────────────────────────────────────────────────
DROP TABLE IF EXISTS books;
DROP TABLE IF EXISTS users;

-- ── Users ────────────────────────────────────────────────────────────────────
CREATE TABLE users (
    id            SERIAL PRIMARY KEY,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    password_hash VARCHAR(255),                        -- NULL for Google-only accounts
    email         VARCHAR(255) UNIQUE,                 -- from Google profile; NULL until set
    google_id     VARCHAR(255) UNIQUE,                 -- Google's stable user sub identifier
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_google_id ON users(google_id);
CREATE INDEX idx_users_email     ON users(email);

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

CREATE INDEX idx_books_user_id ON books(user_id);

-- ── Friendships ───────────────────────────────────────────────────────────────
CREATE TABLE friendships (
    id           SERIAL PRIMARY KEY,
    requester_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    addressee_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status       VARCHAR(10) NOT NULL DEFAULT 'pending'
                 CHECK (status IN ('pending', 'accepted')),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT no_duplicate_requests UNIQUE (requester_id, addressee_id),
    CONSTRAINT no_self_friendship    CHECK  (requester_id <> addressee_id)
);

CREATE INDEX idx_friends_requester ON friendships(requester_id, status);
CREATE INDEX idx_friends_addressee ON friendships(addressee_id, status);
