ALTER TABLE vessels
  ADD COLUMN phone_set_by TEXT,
  ADD COLUMN license_set_by TEXT,
  ADD COLUMN shore_contact_name TEXT,
  ADD COLUMN shore_contact_phone TEXT,
  ADD COLUMN confirmed_at TIMESTAMPTZ,
  ADD COLUMN confirmed_by TEXT;
