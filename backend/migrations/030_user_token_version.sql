-- Track token version on operator accounts to support server-side session revocation (SEC-12).
--
-- Incrementing token_version invalidates all tokens previously issued for the user.
ALTER TABLE users ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 0;
