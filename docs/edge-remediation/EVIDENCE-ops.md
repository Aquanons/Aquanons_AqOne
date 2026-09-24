# Evidence: Operations (Phase 0a)

Plan: `docs/62_EDGE_CASE_REMEDIATION_IMPLEMENTATION_PLAN.md` Phase 0a.
Runbook: `docs/runbooks/RENDER_FREE_DB_ROTATION.md`.
Row counts only; never data, URLs or credentials.

## 2026-09-24 - Runbook written

- Render free-tier facts re-read from https://render.com/docs/free:
  - 30-day expiry, then a 14-day grace period before deletion
  - one free database per workspace, with no backups
  - 15-minute idle spin-down
  - 750 free hours a month; going over suspends all free web services
- Local tools present: PostgreSQL 18.4 client (`pg_dump`, `pg_restore`, `psql`), and a local PostgreSQL 18 server on port 5432 (service running).
- Rehearsal: **not yet run.**
  No local admin credential is configured on this machine (`AQONE_PROBE_PG_ADMIN_URL` is unset), and Claude does not guess passwords.
  Waiting for Len to run runbook Section 4.

## 2026-09-24 - Expiry confirmed, rehearsal run

- Len confirmed in chat that `aqone-db` expires around 2026-10-15, matching the runbook.
  Len will do the first real rotation when it is due.
- Claude ran runbook Section 4 against a throwaway PostgreSQL 18.4 cluster (`initdb`, port 55432, trust auth, deleted afterwards) instead of the machine's password-protected server.
  The commands were otherwise the runbook's: `migrate.py` (migrations up to 031), `python -m app.simulation.generator`, `pg_dump --format=custom --no-owner --no-privileges`, `pg_restore --no-owner --no-privileges --exit-on-error`.
- The dump listed 25 `TABLE DATA` entries.
- Before and after counts were byte-identical (`diff` printed nothing).
- The simulation generator seeds no `users` or `operations_audit_events` rows, so those two tables were proven empty-to-empty only.
  They restore through the same `TABLE DATA` path as the others; the first real rotation's step 8 comparison covers them with real rows.

## Rehearsal results

| Table | Before | After |
| --- | --- | --- |
| operations_audit_events | 0 | 0 |
| schema_migrations | 34 | 34 |
| sos_events | 8 | 8 |
| users | 0 | 0 |
| vessels | 36 | 36 |

**Result: pass** (`sos_events` and `vessels` above zero, no differences).

## Rotations

| Date | Outage | sos_events | vessels | users | New `DB_EXPIRES_AT` |
| --- | --- | --- | --- | --- | --- |
