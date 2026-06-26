-- migrate_google_oauth.sql
--
-- Run this ONCE on the existing database to add Google OAuth support.
-- It adds email and google_id to the users table without dropping anything.
--
-- Usage:
--   psql -U bookshelf_user -d bookshelf_db -h localhost -f deploy/migrate_google_oauth.sql

BEGIN;

-- email: nullable because existing username/password users have no email on record yet.
-- Google OAuth users will always have one. UNIQUE so one Google account = one shelf.
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS email     VARCHAR(255) UNIQUE,
    ADD COLUMN IF NOT EXISTS google_id VARCHAR(255) UNIQUE;

-- Fast lookup by google_id on every OAuth callback
CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id);

-- Fast lookup by email for account-linking logic
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

COMMIT;
