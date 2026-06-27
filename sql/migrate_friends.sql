-- migrate_friends.sql
--
-- Adds the friendships table for friend requests and accepted friendships.
-- Run ONCE on the existing database:
--   psql -U bookshelf_user -d bookshelf_db -h localhost -f deploy/migrate_friends.sql

BEGIN;

CREATE TABLE IF NOT EXISTS friendships (
    id          SERIAL PRIMARY KEY,
    requester_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    addressee_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status      VARCHAR(10) NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'accepted')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Prevent duplicate requests in either direction
    CONSTRAINT no_duplicate_requests UNIQUE (requester_id, addressee_id),
    -- Prevent self-friending
    CONSTRAINT no_self_friendship    CHECK  (requester_id <> addressee_id)
);

-- Fast lookups for "show me all my pending/accepted friendships"
CREATE INDEX IF NOT EXISTS idx_friends_requester ON friendships(requester_id, status);
CREATE INDEX IF NOT EXISTS idx_friends_addressee ON friendships(addressee_id, status);

COMMIT;
