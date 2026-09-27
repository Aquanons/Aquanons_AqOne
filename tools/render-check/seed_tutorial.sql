-- DISPOSABLE DATABASE ONLY. NEVER RUN AGAINST A REAL DATABASE.
--
-- Prepares a freshly generated database for record_tutorial.mjs (docs/72).
-- Run it after seed_live_currents.sql:
--   - the generator's historic distress calls are closed, so the tutorial
--     story begins with no open SOS and its own call is the one that arrives;
--   - live, qualified currents reach back six hours, because the story's SOS
--     was pressed three hours before it arrived and its drift case starts there.

DO $$
BEGIN
  IF current_database() NOT LIKE 'aqone_render%' THEN
    RAISE EXCEPTION 'seed_tutorial.sql only runs on a disposable aqone_render* database, not %', current_database();
  END IF;
END $$;

UPDATE sos_events
SET acknowledged_at = created_at + INTERVAL '4 minutes',
    acked_by = 'MDRRMO duty officer',
    responder_status = 1,
    resolved_at = created_at + INTERVAL '3 hours',
    resolved_by = 'MDRRMO duty officer',
    resolution_code = 'rescued',
    version = version + 2
WHERE demo_tag IS NULL AND resolved_at IS NULL;

UPDATE current_observations
SET is_synthetic = FALSE,
    source = 'live',
    calibration_status = 'qualified',
    created_at = observed_at
WHERE observed_at > NOW() - INTERVAL '6 hours';
