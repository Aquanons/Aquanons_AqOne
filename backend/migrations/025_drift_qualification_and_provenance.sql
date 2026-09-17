-- Phase 2 of docs/AI_SAFETY_REMEDIATION_IMPLEMENTATION_PLAN_GEMINI_3_8.md:
-- Enforce qualified time and spatial support for drift prediction and SOS fix timing.

-- 1. Observation instrument & calibration provenance
ALTER TABLE current_observations ADD COLUMN IF NOT EXISTS instrument_id TEXT;
ALTER TABLE current_observations ADD COLUMN IF NOT EXISTS coordinate_frame TEXT DEFAULT 'enu';
ALTER TABLE current_observations ADD COLUMN IF NOT EXISTS uncertainty_mps DOUBLE PRECISION DEFAULT 0.05;

-- 2. SOS GPS fix acquisition provenance
ALTER TABLE sos_events ADD COLUMN IF NOT EXISTS fix_acquired_at TIMESTAMPTZ;
ALTER TABLE sos_events ADD COLUMN IF NOT EXISTS fix_accuracy_m DOUBLE PRECISION;

-- 3. Drift run decision cutoff, support horizon, and mass accounting
ALTER TABLE drift_runs ADD COLUMN IF NOT EXISTS decision_cutoff_at TIMESTAMPTZ;
ALTER TABLE drift_runs ADD COLUMN IF NOT EXISTS is_retrospective BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE drift_runs ADD COLUMN IF NOT EXISTS supported_horizon_hours DOUBLE PRECISION;
ALTER TABLE drift_runs ADD COLUMN IF NOT EXISTS support_lost_at TIMESTAMPTZ;
ALTER TABLE drift_runs ADD COLUMN IF NOT EXISTS afloat_count INTEGER;
ALTER TABLE drift_runs ADD COLUMN IF NOT EXISTS stranded_count INTEGER;
ALTER TABLE drift_runs ADD COLUMN IF NOT EXISTS outside_domain_count INTEGER;
