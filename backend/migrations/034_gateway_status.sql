CREATE TABLE gateway_status (
  gateway_key TEXT PRIMARY KEY,
  last_poll_at TIMESTAMPTZ NOT NULL
);
