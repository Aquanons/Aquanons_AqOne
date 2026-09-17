-- Profile photo for the sender identity.
--
-- The handset crops its profile picture to a 512px PNG and pushes it with the
-- vessel profile (POST /api/vessel-profile) so a dispatcher can put a face to
-- a distress call. Stored inline as BYTEA rather than as a file: the Render
-- web service has an ephemeral filesystem, so a file written at runtime would
-- vanish on every deploy and restart.
ALTER TABLE vessels
  ADD COLUMN IF NOT EXISTS avatar_png BYTEA,
  ADD COLUMN IF NOT EXISTS avatar_updated_at TIMESTAMPTZ;
