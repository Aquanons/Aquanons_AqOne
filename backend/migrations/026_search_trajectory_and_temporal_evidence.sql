-- Phase 3 of docs/AI_SAFETY_REMEDIATION_IMPLEMENTATION_PLAN_GEMINI_3_8.md:
-- Time-aligned negative search evidence assimilation and trajectory persistence.

-- 1. Drift run trajectory persistence
ALTER TABLE drift_runs ADD COLUMN IF NOT EXISTS trajectory_data JSONB;

-- 2. Search sector geodetic footprint, interval timing, and assimilation audit
ALTER TABLE search_sectors ADD COLUMN IF NOT EXISTS south DOUBLE PRECISION;
ALTER TABLE search_sectors ADD COLUMN IF NOT EXISTS west DOUBLE PRECISION;
ALTER TABLE search_sectors ADD COLUMN IF NOT EXISTS north DOUBLE PRECISION;
ALTER TABLE search_sectors ADD COLUMN IF NOT EXISTS east DOUBLE PRECISION;
ALTER TABLE search_sectors ADD COLUMN IF NOT EXISTS search_start_at TIMESTAMPTZ;
ALTER TABLE search_sectors ADD COLUMN IF NOT EXISTS search_end_at TIMESTAMPTZ;
ALTER TABLE search_sectors ADD COLUMN IF NOT EXISTS dependent BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE search_sectors ADD COLUMN IF NOT EXISTS is_unassimilated BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE search_sectors ADD COLUMN IF NOT EXISTS unassimilated_reason TEXT;
