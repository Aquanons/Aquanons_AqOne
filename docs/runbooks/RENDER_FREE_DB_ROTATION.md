# Runbook: Render free-tier database rotation and keep-awake

**Owner:** Lenard.
**Plan:** `docs/62_EDGE_CASE_REMEDIATION_IMPLEMENTATION_PLAN.md` Phase 0a (EC-C5, EC-M14, EC-M11).
**Why this exists:** AqOne runs on Render's free tier with no budget.
The free database is deleted on a fixed schedule, and losing it means losing every SOS record, vessel profile, operator account and audit trail.
**Facts checked:** Render free-tier docs, https://render.com/docs/free, read 2026-09-24.
Re-check them before each rotation, because free-tier terms change.

Never write a database URL, password or API key into this file, the repository, chat or a ticket.
Commands read them from shell variables that exist only for the length of your terminal session.

---

## 1. The rules we are working around

| Rule (Render docs) | What it means for AqOne |
| --- | --- |
| A free database expires 30 days after it is created. | `aqone-db` was created 2026-09-15, so it **expires 2026-10-15**. |
| After expiry there is a 14-day grace period to upgrade; then Render deletes the database and all its data. | If nothing is done, all data is **deleted after 2026-10-29**. From expiry on, every SOS write fails. |
| Only one free database can be active per workspace. | The old database must be deleted before the new one can be created, so the rotation has a short outage. |
| Free databases have no backups. | The dump in step 3 is the only copy. Keep two copies of it (step 4). |
| A free web service spins down after 15 minutes without inbound traffic and takes about 1 minute to wake. | The first SOS after a quiet period can time out; the phone retries. The keep-awake ping (Section 5) prevents this. |
| Each workspace gets 750 free instance hours per calendar month. Going over **suspends every free web service until next month**. | One always-awake service uses up to 744 hours (31 days). **No other free web service, preview environment or background worker may run in this workspace** while the keep-awake ping is on. |

### Rotation calendar

- Rotate **by 2026-10-08**, a one-week margin before the 2026-10-15 expiry.
- After each rotation, the next expiry is 30 days after the new database's creation.
- Put a calendar reminder at **creation + 23 days** for the next rotation.

---

## 2. Before you start

- **Tools:** PostgreSQL 18 client tools on your PATH (`pg_dump`, `pg_restore`, `psql`).
  The `pg_dump` version must be the same as or newer than the Render server's version; check the server version on the database's Render page.
- **Window:** choose a weekday midday.
  Most boats are ashore or within phone signal, and the dispatch desk is staffed.
  The outage lasts about 15 minutes.
- **Tell MDRRMO before you start:** "The AqOne dashboard will be offline for about 15 minutes. Any SOS sent in that time is held and retried by the phone or the pod, and it will appear once the dashboard is back."
- **Where the dump goes:** a folder outside the repository, for example `$env:USERPROFILE\aqone-backups\`.
  The dump contains personal data (names and phone numbers).
  Never upload it to GitHub, a chat, or a shared drive.
  Delete dumps older than the previous rotation.

### Row-count query

It is used in steps 2 and 8, so the before and after numbers can be compared exactly:

```sql
SELECT 'sos_events' AS t, count(*) FROM sos_events
UNION ALL SELECT 'vessels', count(*) FROM vessels
UNION ALL SELECT 'users', count(*) FROM users
UNION ALL SELECT 'operations_audit_events', count(*) FROM operations_audit_events
UNION ALL SELECT 'schema_migrations', count(*) FROM schema_migrations
ORDER BY 1;
```

Create the backups folder and save the query once:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\aqone-backups" | Out-Null
@'
SELECT 'sos_events' AS t, count(*) FROM sos_events
UNION ALL SELECT 'vessels', count(*) FROM vessels
UNION ALL SELECT 'users', count(*) FROM users
UNION ALL SELECT 'operations_audit_events', count(*) FROM operations_audit_events
UNION ALL SELECT 'schema_migrations', count(*) FROM schema_migrations
ORDER BY 1;
'@ | Set-Content -Encoding utf8 "$env:USERPROFILE\aqone-backups\counts.sql"
```

---

## 3. Rotation steps

Do these in order.
Steps 1 to 4 lose nothing if you stop; step 5 is the point of no return.

1. **Suspend the web service** (Render dashboard, `aqone-backend`, Settings, Suspend Web Service).
   This stops new writes landing in the old database after the dump.
2. **Take row counts from the old database.**
   Copy its **External Database URL** from the Render dashboard (the database, then Connections) and set it for this session only:

   ```powershell
   $env:AQONE_OLD_DB_URL = Read-Host 'Old external DB URL'
   psql $env:AQONE_OLD_DB_URL -f "$env:USERPROFILE\aqone-backups\counts.sql" | Tee-Object "$env:USERPROFILE\aqone-backups\counts-before.txt"
   ```

3. **Dump it:**

   ```powershell
   $stamp = Get-Date -Format yyyyMMdd
   $dump  = "$env:USERPROFILE\aqone-backups\aqone-$stamp.dump"
   pg_dump --format=custom --no-owner --no-privileges --file $dump $env:AQONE_OLD_DB_URL
   pg_restore --list $dump | Select-String 'TABLE DATA' | Measure-Object | Select-Object Count
   ```

   The last line must report a non-zero count of table data entries.
   If `pg_dump` errors, stop, resume the web service, and investigate.
   Nothing has been lost yet.
4. **Make a second copy** of the dump on a different disk or USB drive.
5. **Delete the old database** (Render dashboard, the database, Settings, Delete Database).
   **Point of no return:** from here the dump is the only copy.
6. **Create the new free database** with the same settings as before:
   - name `aqone-db`
   - database `aqone`
   - user `aqone`
   - region Singapore
   - the same PostgreSQL major version as the old one

   If you use the Blueprint (`render.yaml`), a Blueprint sync recreates it and re-links `DATABASE_URL` automatically.
   If you create it by hand, copy the new **Internal Database URL** into the `aqone-backend` environment variable `DATABASE_URL`.
7. **Restore into it:**

   ```powershell
   $env:AQONE_NEW_DB_URL = Read-Host 'New external DB URL'
   pg_restore --no-owner --no-privileges --exit-on-error --dbname $env:AQONE_NEW_DB_URL $dump
   ```

   `schema_migrations` comes back with the data, so `migrate.py` will not re-run old migrations on deploy.
8. **Compare row counts:**

   ```powershell
   psql $env:AQONE_NEW_DB_URL -f "$env:USERPROFILE\aqone-backups\counts.sql" | Tee-Object "$env:USERPROFILE\aqone-backups\counts-after.txt"
   Compare-Object (Get-Content "$env:USERPROFILE\aqone-backups\counts-before.txt") (Get-Content "$env:USERPROFILE\aqone-backups\counts-after.txt")
   ```

   `Compare-Object` must print nothing.
9. **Record the new expiry.**
   Set the `aqone-backend` environment variable `DB_EXPIRES_AT` to the new creation time plus 30 days, in ISO 8601 (for example `2026-11-07T12:00:00+08:00`).
   After Phase B6, the dashboard warns 7 days before this date.
10. **Resume the web service**, and wait until `https://aqone-backend.onrender.com/health/ready` returns `{"status":"ok"}`.
11. **Smoke test:**
    - Log in to the dashboard, and check that the incident history and vessel list look as they did before.
    - Post one test SOS with vessel ID `ROTATION-TEST-<yyyyMMdd>`.
    - Check it appears on the dashboard, then resolve it.
12. **Clear the session variables**, then record the rotation:

    ```powershell
    Remove-Item Env:AQONE_OLD_DB_URL, Env:AQONE_NEW_DB_URL
    ```

    Add a dated line to `docs/edge-remediation/EVIDENCE-ops.md` with the date, row counts (numbers only), outage length and the new `DB_EXPIRES_AT`.
    Set the calendar reminder for creation + 23 days.

### If something goes wrong after step 5

- **The restore fails:** delete the new database, create it again (step 6), and restore again from the second copy of the dump.
- **Counts differ:** do not resume the web service.
  Find which table differs (compare the two counts files), and restore again into a freshly created database.
- **You cannot finish within the window:** leave the web service suspended.
  Phones and pods keep retrying, and a suspended service is better than one writing into a half-restored database.

---

## 4. Rehearsal on your own machine (do this once before the first real rotation)

This proves the dump and restore commands against a throwaway local copy.
It uses the same local-admin variable as the security probes, and needs a local PostgreSQL 18 server on port 5432.

```powershell
$env:AQONE_PROBE_PG_ADMIN_URL = Read-Host 'Local admin URL (postgresql://postgres:<pw>@localhost:5432/postgres)'
$base = $env:AQONE_PROBE_PG_ADMIN_URL -replace '/postgres$', ''
psql $env:AQONE_PROBE_PG_ADMIN_URL -c 'CREATE DATABASE aqone_rehearsal_src' -c 'CREATE DATABASE aqone_rehearsal_dst'

cd backend
$env:DATABASE_URL = "$base/aqone_rehearsal_src"
python migrate.py
python -m app.simulation.generator
cd ..

psql "$base/aqone_rehearsal_src" -f "$env:USERPROFILE\aqone-backups\counts.sql" | Tee-Object "$env:TEMP\rehearsal-before.txt"
pg_dump --format=custom --no-owner --no-privileges --file "$env:TEMP\rehearsal.dump" "$base/aqone_rehearsal_src"
pg_restore --no-owner --no-privileges --exit-on-error --dbname "$base/aqone_rehearsal_dst" "$env:TEMP\rehearsal.dump"
psql "$base/aqone_rehearsal_dst" -f "$env:USERPROFILE\aqone-backups\counts.sql" | Tee-Object "$env:TEMP\rehearsal-after.txt"
Compare-Object (Get-Content "$env:TEMP\rehearsal-before.txt") (Get-Content "$env:TEMP\rehearsal-after.txt")

psql $env:AQONE_PROBE_PG_ADMIN_URL -c 'DROP DATABASE aqone_rehearsal_src' -c 'DROP DATABASE aqone_rehearsal_dst'
Remove-Item "$env:TEMP\rehearsal.dump", Env:DATABASE_URL, Env:AQONE_PROBE_PG_ADMIN_URL
```

**Pass:** `Compare-Object` prints nothing, and `sos_events` and `vessels` counts are above zero.
Record the counts (numbers only) in `docs/edge-remediation/EVIDENCE-ops.md`.

---

## 5. Keep the web service awake (free)

1. Create a free UptimeRobot account, then add an **HTTP(s)** monitor:
   - URL `https://aqone-backend.onrender.com/healthz`
   - interval 5 minutes
   - alert contact: your email
2. This keeps the service inside the 15-minute idle limit.
   It also emails you when the backend is down, which is the only outage alert we have for free.
3. **Hours budget.**
   One always-awake service uses up to 744 of the 750 free hours a month.
   Before creating *any* other free web service, preview environment or worker in this Render workspace, pause this monitor first.
   Otherwise Render suspends **all** free web services, including the SOS backend, until the next month.
4. When a shore gateway is online it polls every 20 to 45 s, which keeps the service awake anyway.
   The monitor matters for the times the gateway is down, which is exactly when the direct path is carrying SOS calls.

---

## 6. Len actions (Phase 0a)

- [x] Open `aqone-db` on the Render dashboard and confirm its creation and expiry dates match Section 1 (created 2026-09-15, expiry 2026-10-15).
  If they differ, correct this file.
- [x] Run the rehearsal (Section 4) and record the counts (passed 2026-09-24, see `docs/edge-remediation/EVIDENCE-ops.md`).
- [ ] Set up the UptimeRobot monitor (Section 5).
- [ ] Do the first real rotation by 2026-10-08 (Section 3).
- [ ] Send the NTC inquiry (EC-M11):
  - Which band and power limits apply to low-power LoRa radios in the Philippines: 915 MHz, or 920 to 925 MHz (AS923)?
  - What is the maximum EIRP?
  - Do the devices need type approval?

  Record the answer in `docs/08_DEMO_AND_STATUS.md`.

## 7. Retire this runbook when

The project is funded.
Move `aqone-db` to a paid instance with backups and the web service to a paid instance that does not sleep.
Then delete this runbook and the `DB_EXPIRES_AT` banner (docs/62 Section 8).
