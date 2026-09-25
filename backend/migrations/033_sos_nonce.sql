ALTER TABLE sos_events
  ADD COLUMN nonce BIGINT,
  ADD COLUMN alt_latitude DOUBLE PRECISION,
  ADD COLUMN alt_longitude DOUBLE PRECISION;

DROP INDEX IF EXISTS uq_sos_events_vessel_client_ts;

CREATE UNIQUE INDEX uq_sos_events_vessel_nonce
  ON sos_events (vessel_id, nonce)
  WHERE nonce IS NOT NULL;

CREATE UNIQUE INDEX uq_sos_events_vessel_client_ts
  ON sos_events (vessel_id, client_ts)
  WHERE nonce IS NULL;
