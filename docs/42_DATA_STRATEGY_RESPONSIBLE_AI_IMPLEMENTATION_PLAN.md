# Data Strategy and Responsible AI — Implementation Plan

## Purpose and delivery rule

Create one enforceable data and responsible-AI strategy for AqOne: every data
item has a purpose, owner, provenance, access boundary, retention decision,
and honest model-use status; every model output carries the evidence needed to
decide whether a person may act on it.

This plan strengthens governance around the existing safety, fisheries,
weather, anomaly, squall, drift, hotspot, and audit work.  It does not collect
new personal or demographic data, retrain models, claim live validation,
introduce an external data platform, add automated emergency/fisheries
decisions, or implement deletion before an approved retention policy exists.
No LLM is needed for this work.

Plans 38–41 should supply the live/synthetic source separation, operational
audit helper, and role matrix that this plan builds on.  If any preceding plan
has not passed its own tests, retain the correct status as a documented
dependency rather than writing a policy that claims it is finished.

### Mandatory workflow

Before each phase, inspect the branch and preserve unrelated work.  Update
contracts and governance documents before changing a data field, access rule,
or output.  Stage only that phase's files, inspect the staged diff, run its
checks, and create the stated focused commit.  Never use `git add -A`, amend
another person's commit, add copied production data, commit credentials or
exports, or reformat unrelated feature work.

Do not begin the next phase until the prior phase demonstrably works.  A data
owner decision about purpose, consent, release, or retention is an actual gate;
record it and stop instead of inventing consent or a safe retention period.

## Current findings that the strategy must correct

- Synthetic operational rows usually carry `is_synthetic = TRUE`, and the
  README/disclosures describe the separation.  However, source and freshness
  are not a complete shared provenance contract across contacts, (retired) pressure,
  currents, incidents, model outputs, and evaluation results.
- The squall, anomaly, and drift implementations currently depend heavily on
  synthetic data or fallbacks.  The public squall route can still expose old
  synthetic data, and current evaluation metadata hard-codes every model as
  `calibration: synthetic`, even though the separate marine-hazard model uses
  real public reanalysis/proxy labels.
- `web/ml/model-card.json` provides strong provenance for the hazard model,
  but squall, anomaly, and drift lack equivalent model cards/release records.
  A committed model artifact or number in `eval_results.json` is not by itself
  a release decision.
- Catch hotspots use a per-row `share_for_hotspots` flag and a three-reporter,
  coarse-cell output.  That is a useful privacy start, but there is no durable
  consent receipt/version/withdrawal history or owner-approved retention
  policy.  The protected raw catch read currently relies on broad operator
  authentication rather than the PRD's fisheries-purpose boundary.
- The current disclosures identify important bias risks—coverage, cold start,
  irregular trip patterns, smartphone ownership, and proxy labels—but there is
  no repeatable monitoring/release checklist connecting them to deployment.

## Non-negotiable principles and acceptance boundary

The completed strategy must enforce all of these:

- Safety access and service never depend on fisheries participation, catch
  consent, smartphone-derived profile, or a model score.
- Data is purpose-separated: responders access safety records required for
  rescue; fisheries roles access only approved aggregated fisheries evidence;
  infrastructure roles access equipment health; no shared dashboard bypasses
  those boundaries.
- Synthetic, live, externally sourced, derived, and manually entered data are
  distinguishable in storage and every operational output.  Unknown/stale data
  remains unknown; it is never transformed into calm, clear, or live.
- Consent is explicit, versioned, withdrawable, attributable to the vessel
  device, and honored for future hotspot aggregation.  Withdrawal does not
  break safety or retroactively claim that already exported aggregates vanish.
- Every model has a machine-readable card and human-readable summary covering
  purpose, inputs, source/data window, license, model/build version,
  calibration/evaluation protocol, limits, human authority, and release state.
- A model stays `research`/`demo` until an authorized owner reviews documented
  field evidence against a pre-agreed baseline and false-alarm/harms threshold.
  No model self-promotes, auto-retrains from live events, dispatches rescue,
  publishes a restriction, or presents itself as a PAGASA/MDRRMO decision.
- Privacy, bias, drift, coverage, and model-quality metrics are monitored only
  with consented/approved data.  Do not infer protected characteristics or
  collect demographics merely to produce a fairness chart.

## Phase 1 — Establish the governed data inventory and decisions

### Work

1. Read the canonical PRD, `docs/16_QA_DISCLOSURES.md`,
   `docs/23_INTEGRATED_SYSTEM_DESIGN.md`, `docs/05_PUBLIC_API.md`, migrations,
   model/evaluation code, hotspot/catch code, and the role/audit plan before
   writing the strategy.
2. Create one version-controlled data inventory and decision register in
   `docs/`.  For each actual dataset/table/output, record: purpose; owner;
   data subjects; source/provenance; live/synthetic/external/manual state;
   sensitivity; lawful/consent basis; permitted roles; transformations;
   retention/deletion status; sharing/export rule; and linked code/migration.
   Include SOS, trip contacts, current readings, PAGASA weather data, incidents/search
   grids, advisories, raw catch logs, hotspot cells, authentication/device
   records, audit events, model artifacts, and evaluation artifacts.
3. Create one data-flow map that shows safety and fisheries branches separately.
   Mark every boundary where exact location, vessel identity, contact history,
   or catch information is reduced/aggregated.  Use current facts only; label
   planned integrations and physical sensor feeds as not yet live.
4. Obtain named owner decisions for: the role/purpose matrix from Plan 41;
   consent wording/version; hotspot k-anonymity/cell-size policy; model release
   approvers; data-retention schedules; incident/audit export handling; and
   breach/correction/withdrawal contact.  Do not encode policy values until
   those decisions are recorded.
5. Align README, PRD status, and `docs/16_QA_DISCLOSURES.md` to the inventory
   without deleting historical explanations.  Explicitly correct any statement
   that calls simulation, fallback, or a proxy-labelled model “live” or
   field-validated.

### Tests

- Add a lightweight documentation/registry validation that each declared model
  and data class has all required fields and that every code-referenced source
  is either inventoried or deliberately excluded with a reason.
- Manual review signs off the purpose/access/retention decisions; record the
  reviewer/date, not personal signatures or sensitive values in Git.
- Run the validator and relevant Markdown/link checks.

### Commit

`docs(data): define governed data inventory`

## Phase 2 — Enforce purpose separation and explicit fisheries consent

### Work

1. Apply the approved role/purpose matrix from Plan 41 to raw catch reads,
   hotspot administration, safety records, and infrastructure telemetry.
   Reuse `require_roles`; do not create a bypass role.  MDRRMO/PCG safety work
   must not grant access to identifiable catch records, and fisheries access
   must not grant unrestricted safety trip histories.
2. Replace the bare hotspot-sharing boolean as the sole evidence of consent
   with minimal consent provenance: consent state, policy/version accepted,
   granted/withdrawn times, and the owning vessel-device record.  Preserve the
   per-log sharing choice where needed, but derive future aggregate eligibility
   from both the current valid consent and the row's explicit choice.
3. Add a vessel-device-authenticated consent status/withdrawal path with clear
   plain-language response.  Withdrawal stops future hotspot aggregation and
   logs the decision through Plan 41's audit helper.  It does not block SOS,
   warnings, messaging, check-ins, or a fisher's own catch history.
4. Keep the existing coarse aggregation and contributor threshold until the
   owner approves a change.  Bound returned cells, omit vessel IDs/exact source
   points, cap a single reporter's influence as current code does, and return
   an honest empty response when there are not enough contributors.  Do not add
   decorative “differential privacy” without an actual privacy analysis.
5. Document the retention/deletion-request behavior that is currently possible
   versus deferred.  Do not bulk-delete historical catch data or audit data in
   this phase without the approved policy and a separate, recoverable process.

### Tests

- Role tests prove safety responders cannot list raw catch logs and fisheries
  users cannot access case/SOS trip details outside their approved purpose.
- Consent tests cover grant, repeated request/idempotency, withdrawal,
  unavailable/expired consent, a mismatched device, and safety paths continuing
  regardless of consent state.
- Hotspot tests prove withdrawn/non-consented rows do not contribute; cells
  below the approved threshold expose no contributor identity/location; and a
  duplicate/high-volume reporter cannot dominate beyond the documented cap.
- Audit tests confirm consent changes create redacted events without raw catch
  data.
- Run targeted backend tests and `ruff check .`.

### Commit

`feat(data): enforce consented fisheries use`

## Phase 3 — Make provenance and model cards first-class artifacts

### Work

1. Define one small machine-readable model/data-release registry in the repo,
   validated by a standard-library script or existing tooling.  It must list
   the danger-zone, squall, anomaly, drift, and hotspot approaches—even where
   the correct entry is “aggregation, not a predictive model.”  Reuse the
   existing hazard model card as source material; do not maintain unrelated
   parallel descriptions.
2. For each entry, record: stable name/version/build hash; owner; decision
   category; intended users; prohibited use; input sources and time window;
   synthetic/live/external provenance; licences/attribution; preprocessing;
   output schema; evaluation dataset/split/baseline/metrics; known bias and
   coverage limits; incident/feedback linkage; and `research`, `demo`,
   `shadow`, or `operational` release state.
3. Replace `eval_store.py`'s global synthetic calibration label with explicit
   per-evaluation metadata supplied by each evaluator.  Store dataset/release
   identifier, generated-at, code/model version, evaluation scope, and whether
   metrics are synthetic, proxy-labelled, or field-validated.  Never overwrite
   one model's provenance when another evaluation runs.
4. Add source/provenance metadata to model-serving responses and outputs:
   source type, data age/coverage, model/release version, calibration scope,
   and a limitation/reason.  Reuse the stale-safe squall, anomaly, and drift
   contracts from Plans 38–40; do not create client-only substitutes.
5. Hash and record model artifacts/data snapshots used for each reproducible
   evaluation.  Keep raw restricted data out of Git; store only manifest,
   checksum, access instructions, and approved derived metrics.

### Tests

- Registry validation fails for missing required fields, unknown release state,
  absent limitation/prohibited-use text, or a model artifact checksum mismatch.
- Evaluation tests prove calibration/provenance is per-model, survives another
  section being written, and cannot call a synthetic/proxy result
  field-validated.
- API tests assert model outputs expose required provenance and an unavailable
  input remains unavailable rather than getting default metadata.
- Run evaluation/registry/API tests and `ruff check .`.

### Commit

`feat(ai): publish model provenance`

## Phase 4 — Introduce evidence-based model release and monitoring gates

### Work

1. Write a release checklist for each decision-support capability.  It must
   define the appropriate baseline, time/vessel/geography split, calibration
   metric where applicable, false-alert/miss/workload measures, coverage/data
   quality threshold, human review owner, and rollback condition.  The listed
   metrics must match the model type: no “accuracy” for hotspot aggregation or
   one number for a probability distribution.
2. Use the smallest deployment gate: a version-controlled release record plus
   server configuration that defaults to `research`/`demo`.  Only the named
   approver and recorded evidence may set an allowed operational state.  The
   runtime must fail closed to `unknown`, `watch`, or responder review when the
   gate/source/freshness requirement is absent; it must never silently enable a
   `RETURN NOW`, incident escalation, or fisheries restriction.
3. Prohibit automatic retraining and automatic learning from responder actions,
   SOS outcomes, catches, or raw production telemetry.  Define a human-reviewed
   offline data-preparation and evaluation path with versioned input manifest,
   approval, rollback to prior release, and audit event for each release or
   rollback.
4. Implement a minimal monitoring summary for approved operational models:
   input availability/freshness/coverage; rate of unknown/degraded outputs;
   alert/candidate volume; responder overrides/dismissals; and consented data
   representation by coarse area/time.  Do not infer protected attributes or
   show individual vessel/catch histories to build a fairness dashboard.
5. Surface release state, model/source version, data age/coverage, and limit in
   the existing dashboard/mobile contexts where the output is used.  Human
   directives remain visibly distinct from model suggestions and official
   PAGASA notices remain separately attributed.

### Tests

- Test default-deny release behavior, an approved release with all evidence,
  expired/mismatched release metadata, and rollback to prior approved state.
- Test a synthetic/stale/low-coverage output cannot cross into an operational
  action state even if its raw score is high.
- Monitoring tests prove aggregates obey purpose/role boundaries and no raw
  vessel ID, exact catch location, free text, token, or demographic inference
  enters a monitoring response.
- Run targeted backend/dashboard/mobile tests and `ruff check .`.

### Commit

`feat(ai): gate model outputs by evidence`

## Phase 5 — Pilot readiness, review, and honest communication

### Work

1. Prepare a pilot data-collection protocol before taking live data: community
   explanation/consent materials, approved fields/minimization, device and
   sensor calibration, clock synchronization, ground-truth/incident labelling,
   coverage/outage logging, correction/withdrawal path, secure transfer, and
   named data/model stewards.  Do not collect demographics or AIS-like route
   data without a separate stated purpose and approval.
2. Run reproducible evaluations using the registered manifests.  Compare to
   the documented baseline and stratify only by approved non-sensitive factors
   such as coarse coverage zone, time period, input completeness, device/sensor
   availability, and new-versus-established profile.  Record uncertainty and
   sample size; do not promote a model on a small flattering slice.
3. Conduct the planned human review: fishers/community representatives for
   consent and harms, MDRRMO/PCG for safety false-alarm/miss burden, and
   fisheries/LGU owners for aggregation/release decisions.  Capture their
   decisions in the audit/release record—not private meeting notes in code.
4. Update `docs/08_DEMO_AND_STATUS.md`, README, disclosures, model cards, and
   operations-console wording with exact dates, dataset/release IDs, checks,
   reviewer role, status, and remaining uncertainty.  If field evidence is
   absent, retain `demo`/`research` wording plainly.

### Tests

- Run all model/evaluation registry checks plus `python -m pytest -q` and
  `ruff check .` in `backend`.
- Run dashboard/mobile checks that render provenance and release state.
- Manual acceptance: a reviewer can trace an operational output to a model
  card, release record, data source/age/coverage, and audit event; a fisher can
  withdraw hotspot consent without losing safety services; and no screen
  presents a simulated or proxy result as a human or official decision.

### Commit

`docs(ai): record data strategy and pilot verification`

## Handoff checklist for Claude Code

- Read the canonical PRD, `docs/16_QA_DISCLOSURES.md`,
  `docs/23_INTEGRATED_SYSTEM_DESIGN.md`, and Plans 38–41 before coding.
- Prefer one registry, one audit helper, and the existing role guards over new
  governance services, event buses, data warehouses, or model dashboards.
- Keep raw live/restricted data out of the repository.  Checksum/manifests and
  aggregate evaluation results are the deliverables, not copied datasets.
- Treat an unmet owner decision, consent requirement, privacy assessment, or
  field-validation gate as a stop condition.  Report exact tests and commit
  hash after every phase.
