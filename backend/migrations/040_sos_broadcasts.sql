CREATE TABLE IF NOT EXISTS sos_broadcasts (
  id SERIAL PRIMARY KEY,
  sos_event_id INTEGER NOT NULL UNIQUE REFERENCES sos_events(id) ON DELETE CASCADE,
  center_lat DOUBLE PRECISION NOT NULL,
  center_lon DOUBLE PRECISION NOT NULL,
  radius_km INTEGER NOT NULL DEFAULT 10,
  eta_at TIMESTAMPTZ NULL,
  responder_status SMALLINT NULL,
  state TEXT NOT NULL DEFAULT 'active',
  created_by TEXT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expired_at TIMESTAMPTZ NULL
);
CREATE INDEX IF NOT EXISTS idx_sos_broadcasts_state ON sos_broadcasts(state);
