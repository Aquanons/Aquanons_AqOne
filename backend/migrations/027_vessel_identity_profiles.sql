-- Sender identity for SOS incidents: the phone pushes its declared owner
-- profile (docs/05_PUBLIC_API.md "vessel identity profile") so the dashboard
-- can identify who raised a distress call without blocking the call itself.
ALTER TABLE vessels
  ADD COLUMN IF NOT EXISTS skipper_name TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS license_type TEXT NOT NULL DEFAULT 'none',
  ADD COLUMN IF NOT EXISTS license_number TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS phone TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS profile_updated_at TIMESTAMPTZ;