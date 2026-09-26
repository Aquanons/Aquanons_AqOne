# What needs to be done

**Snapshot:** 2026-09-26 12:30 +08:00, source checkout `master` at `897e8de`, before this report was published.

This is the fast handoff for teammates and coding agents.
Use `AGENTS.md` for repository rules, `HANDOFF.md` for the current baton, the latest dated entry in `docs/08_DEMO_AND_STATUS.md` for observed results, and each active plan for exact acceptance criteria.
This snapshot does not approve work or replace product scope and shared contracts.

To get oriented, ask: "Read `WHAT_NEEDS_TO_BE_DONE.md` and tell me the next action for my workstream."

## Current checkout and caveats

- At scan start, `master` and `origin/master` were at `897e8de`; this report was later published on `master` as a documentation-only change.
- Tracked files were clean before this report was added.
- Worktree `../AqOne-fisher-ux` is also at `897e8de`.
- Worktree `../AqOne-fleet-watch` was on `feat/fleet-watch` at `10f320a` when scanned; its Phase 2 work is complete, but use current `master` when starting new work.
- `AqOne_Story_and_Data_Flow.md` is an existing untracked file and is not part of this task; do not stage it.
- The prior `HANDOFF.md` checkout evidence was stale when this report was created; it has now been refreshed to match the scan baseline (`897e8de`) while keeping the Plan 66 shore test as the baton.
- Deployment revision claims disagree: the root README says `2528f30`, while the handoff records `/health/ready` at `a0f8284`. Check `/health/ready` before claiming which commit is deployed or using it for a demo.
- `docs/README.md` lists four plans as ACTIVE while also saying only one implementation plan may be ACTIVE. Follow the phase gates below and the plan documents, not that rule as a scheduling decision.

## Immediate baton: Plan 66, Phase 1 shore test

The software and browser checks for C3, C6 and C7 are mostly evidenced; the deployed backend half of C9 is evidenced.
The remaining critical check is to reflash the shore gateway from current `master` and verify the authenticated, TLS-checked backend connection and dashboard-to-phone mesh chat.

- **Daniel:** use [`docs/edge-remediation/HANDOFF-daniel-shore-reflash.md`](docs/edge-remediation/HANDOFF-daniel-shore-reflash.md) to flash the shore board and matching pod, then return sanitized serial logs, phone screenshot and run time.
- **Len:** send `UPLINK_SSID`, `UPLINK_PASS`, `GATEWAY_API_KEY` and fleet `LOAM_KEY` privately; never put their values in Git, reports or logs.
- **Claude or the current evidence owner:** add the C9/C13 result to [`docs/edge-remediation/EVIDENCE-critical.md`](docs/edge-remediation/EVIDENCE-critical.md), update the Plan 66 checkboxes and `docs/08`, review for secrets and personal data, then make the plan's evidence checkpoint commit and stop for Len.

Known limits in this phase: SMS escalation is not configured on Render (`SEMAPHORE_API_KEY` and `ONCALL_SMS_NUMBERS` were reported unset on 2026-09-25), so C6 is only verified for the browser alarm.
C7 resolve and undo were exercised, but the reopened vessel feed was checked through `/api/sos/active`, not fully through the phone UI.
A countdown freeze happened once after registration and was not reproduced in two retries; Jade owns that follow-up.

## Active and queued workflows

### [Plan 66: critical edge cases](docs/66_CRITICAL_EDGE_CASES_IMPLEMENTATION_PLAN.md)

Phase 1 emulator, browser and deployed-backend evidence is mostly in.
Finish the shore reflash evidence above.
Then Daniel needs two boards for Phase 2's current-firmware radio bench and dated logs.
Phases 3 to 5 depend on that bench.
Phase 6 needs Len's approval.
Phase 7 needs D5 (vessel identity), Phase 4 and the H23 thermal check.

### [Plan 65: fisher friction](docs/65_FISHER_FRICTION_REDUCTION_IMPLEMENTATION_PLAN.md)

Phase 1, countdown fix and Phase 3 are merged to `master`; the handoff records 379 Flutter tests passing.
The latest `897e8de` adds D8's visible Silence-button requirement to Phase 4, not the app implementation.
Doreen Kay and Jade complete the team term study in `docs/fisher-ux/TERM_STUDY.md`; Len signs off.
Phase 2 starts after the term study and after Plan 66 reaches its Phase 5 gate.
Then follow Phases 4, 4b, 5 and 6 in order.
Phase 4b tests are on `ux/p4b-tests` (`f454e24`) and must be brought in when that phase starts.

### [Plan 69: weather-tiered check-ins](docs/69_WEATHER_TIERED_CHECKINS_IMPLEMENTATION_PLAN.md)

Phases 1 (contracts) and 2 (pure backend policy) are complete.
Phase 3 (migration, storage, tier/slot endpoints and DB-backed tests) is awaiting Len's approval.
Phases 4 and 5 follow; firmware Phases 6 and 7 have Plan 66 gates, and Phase 8 is bench evidence.

### [Plan 62: edge-case remediation](docs/62_EDGE_CASE_REMEDIATION_IMPLEMENTATION_PLAN.md)

Tracks B, M and W and review fixes are merged; several critical checks are now tracked in Plan 66.
The parent plan still lists Phase I integration, Phase 0a UptimeRobot/NTC work, and gated B8, M7 and Track F.
Reconcile overlaps with Plan 66 before duplicating its C3/C6/C7/C9 checks.
Phase I still calls out M8, M9, H15 and H18, database-backed gates, release APK/foreground-service verification and dated integration evidence.

Plan 67, stagnant mode, is a draft and is not approved for implementation.
Coordinate any button gesture with Plan 66 Phase 7, where a three-second hold remains SOS-only.

## Whole-demo work still open

- Demonstrate the complete airplane-mode phone to boat pod to shore gateway to backend to dashboard flow on current hardware and current firmware.
- Verify that responder acknowledgement persists after dashboard reload and reaches the handset over the return path.
- Run the outdoor range test and record measured metres in `docs/08_DEMO_AND_STATUS.md`; current range figures are estimates, not measurements.
- Complete physical-device checks, including the release APK, foreground-service/retry behavior, countdown double tap and silent SOS behavior.
- Keep `docs/08_DEMO_AND_STATUS.md` honest, rehearse the full demo three times, and record the screencast.
- Respect the RSTW dates, 2026-10-01 to 03, and Enactus dates, 2026-10-09 to 10; the plans prohibit merges that change the demo APK, firmware or backend during those events.

## Decisions and coordination still needed

- Len: provide Daniel the shore secrets privately; approve or defer Plan 69 Phase 3; decide Plan 66 D5 and whether to approve Phase 6; decide SMS provider setup; schedule the post-RSTW field session.
- Doreen Kay and Jade: complete and source the team term study before Plan 65 Phase 2.
- Daniel: provide two-board bench evidence for Plan 66 Phase 2 and complete the shore reflash.
- Len: resolve the deployment revision mismatch and refresh the root README's status check after verifying the deployed health endpoint.

## Current source documents

- Project rules and build order: [`AGENTS.md`](AGENTS.md) and [`docs/00_START_HERE.md`](docs/00_START_HERE.md).
- Current field and demo evidence: [`docs/08_DEMO_AND_STATUS.md`](docs/08_DEMO_AND_STATUS.md), newest dated entry first.
- Active workflow register: [`docs/README.md`](docs/README.md).
- Product priorities and stated limitations: [`README.md`](README.md), noting its “Last status check” currently predates this snapshot.
