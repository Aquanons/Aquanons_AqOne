ALTER TABLE buoy_contacts ADD COLUMN IF NOT EXISTS contact_via TEXT NOT NULL DEFAULT 'buoy';
ALTER TABLE buoy_contacts DROP CONSTRAINT IF EXISTS chk_buoy_contacts_contact_via;
ALTER TABLE buoy_contacts ADD CONSTRAINT chk_buoy_contacts_contact_via
  CHECK (contact_via IN ('pod', 'handset', 'buoy'));

ALTER TABLE vessel_trips ADD COLUMN IF NOT EXISTS welfare_updated_at TIMESTAMPTZ;
