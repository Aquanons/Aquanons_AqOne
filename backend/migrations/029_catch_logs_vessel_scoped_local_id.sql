-- Scope catch log local_id uniqueness per vessel rather than globally (SEC-11).
--
-- A global unique index on local_id allowed one vessel to overwrite another vessel's
-- catch log if local_id collided or was chosen deliberately.
DROP INDEX IF EXISTS uq_catch_logs_local_id;

CREATE UNIQUE INDEX IF NOT EXISTS uq_catch_logs_vessel_local_id
  ON catch_logs (vessel_id, local_id)
  WHERE local_id IS NOT NULL;
