ALTER TABLE sos_events
  ADD COLUMN version INT NOT NULL DEFAULT 0,
  ADD COLUMN resolution_code TEXT CHECK (
    resolution_code IS NULL OR resolution_code IN (
      'rescued', 'safe_confirmed', 'stood_down_by_fisher', 'duplicate',
      'closed_unconfirmed', 'unspecified'
    )
  ),
  ADD COLUMN reopened_at TIMESTAMPTZ,
  ADD COLUMN reopened_by TEXT;
