-- DISPOSABLE DATABASE ONLY. NEVER RUN AGAINST A REAL DATABASE.
--
-- Relabels the generator's most recent synthetic current observations as
-- live, qualified buoy readings ending 15 minutes ago, so a responder-opened
-- drift case can pass the environmental quality gate and the render check can
-- show an `ok` run. It fabricates field data, which is exactly why it refuses
-- to run on any database not named aqone_render*.

DO $$
BEGIN
  IF current_database() NOT LIKE 'aqone_render%' THEN
    RAISE EXCEPTION 'seed_live_currents.sql only runs on a disposable aqone_render* database, not %', current_database();
  END IF;
END $$;

UPDATE current_observations
SET observed_at = observed_at + ((NOW() - INTERVAL '15 minutes') - (SELECT MAX(observed_at) FROM current_observations));

UPDATE current_observations
SET is_synthetic = FALSE,
    source = 'live',
    calibration_status = 'qualified',
    created_at = observed_at
WHERE observed_at > NOW() - INTERVAL '3 hours';
