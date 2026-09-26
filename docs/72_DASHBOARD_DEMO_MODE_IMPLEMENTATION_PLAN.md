# Implementation Plan: toggleable dashboard demo mode

**Status:** DRAFT - Revision 1, not started; a separate workload from Plan 71
**Owner:** Lenard (approval), implementer not assigned
**Created:** 2026-09-26T23:05:00+08:00
**Updated:** 2026-09-26T23:05:00+08:00
**Related:** `docs/71_DASHBOARD_DRIFT_TRIP_RENDER_FIXES_IMPLEMENTATION_PLAN.md` (removes the hard-coded sample vessels this plan replaces), `docs/audits/DASHBOARD_DRIFT_TRIP_RENDER_AUDIT_2026-09-26.md`, `docs/05_PUBLIC_API.md`, `docs/43_DTI_PITCH_IMPLEMENTATION_PLAN.md`, `docs/53_EXTERNAL_DEADLINES.md`

Revision: 1
**Execution mode:** hard-stop (proposed by the plan rule: product code and more than three phases; Len may choose `auto` at approval)
Feature spec and revision: Len's chat request, 2026-09-26: "I think its just better to have a toggleable demo mode where the dashboard would be populated by sample vessels, sample alerts, and generally a sample of all the features and how it functions. but i think this is a seperate workload put this somewhere in the docs /implementation-plan /council."
The requirements below (DEMO-01 to DEMO-08) are the draft spec; Len's answers to the open questions become Revision 2.
Approved baseline and architecture revisions: `docs/Aqone_PRD (2).md` v3.0; `docs/05_PUBLIC_API.md` after Plan 71.
Len's chat approval: Not recorded.
Target branch: to be assigned in the Current Register when approved.

Success condition: a presenter can switch the dashboard into demo mode with no backend, no network and no login, see every dashboard feature populated with plausible sample data and working interactions, and switch back to a dashboard that shows only real data.
Next hard stop: Len answers Q1-Q5 and approves Revision 2.

## Why

Plan 71 removes the hard-coded sample vessels because they were shown as real, under the LIVE badge, next to real rows.
Sample data is still valuable for pitches, training and venues without a signal (`docs/53`: RSTW 2026-10-01 to 10-03, Enactus 2026-10-09 to 10-10).
The honest form of it is a mode the viewer chooses and can always see, that never mixes with live data.

## Council deliberation (2026-09-26)

### 1. Grounding

**Observed facts:**

- The dashboard reads every API through one seam, `ns.authFetch` in `web/js/dashboard/dashboard-core.js`, against `window.location.origin`.
- `login.html` already has "Continue without logging in for an offline demo", which stores the token `DEMO-OFFLINE-NO-AUTH` and `aqoneDemoBypassActive=1` in `sessionStorage` (`web/js/script.js:67-73`); with that token every protected API call returns 401.
- Sample content is scattered through the DOM modules today: the Vessels list and overdue markers (`dashboard-vessels-alerts.js`, deleted by Plan 71), sample incident and squall drawers (`dashboard-markers.js`), Live Overview figures ("Displaying sample data"), the SAR metrics footer, and the buoy drawer baseline.
- The backend has a separate presenter demo: `DEMO_MODE` mounts `/api/demo/*`, and scenario beats write rows tagged `is_synthetic` and `demo_tag` into the real tables (`app/demo/scenarios.py`), driven from `web/html/demo-control.html`.
- The pure renderers in `web/js/dashboard-utils.js` already badge synthetic rows DEMO.

**Unverified assumptions (Len to confirm):**

- Demo mode is for presentations and training on a laptop or projector, not for a responder's working console.
- It must work with no backend at all (venue WiFi down), which rules out a server-only design.
- "A sample of all the features and how it functions" means clickable features with in-memory effects (acknowledge, escalate, mark a searched area), not a narrated guided tour.
- The deployed production dashboard may offer the toggle, as long as it is unmistakable.

### 2. Perspectives and debate

- 😈 **Devil's Advocate:** Sample data inside real modules is how the fake OVERDUE boats reached the LIVE view; a toggle that swaps a few arrays in place will regress the same way. Mixed state is the failure: a real SOS arriving while demo mode is on, or a demo acknowledgement sent to the real backend. Fixtures also rot: when `docs/05` changes, a frozen demo keeps showing the old shape and hides contract bugs. Timestamps frozen in fixtures read "3 weeks ago" at the next event.
- ✂️ **Simplicity Champion:** Do not build a second dashboard or a mock server. Put one fake data source behind the existing `authFetch` seam: contract-shaped JSON per route, and a tiny in-memory store for the few mutations. Every module renders demo data through its real code path, so the demo also exercises the product. No new dependency, no build step. Reuse the existing offline-demo button as the entry instead of inventing a second one.
- 🛡️ **Security Auditor:** The trust boundary is "a viewer must always know what they are looking at". Demo mode must be all or nothing per tab, shown by a persistent banner and watermark that no panel can hide, and it must make zero network calls to `/api/*`, so nothing can write to real tables or leak a token. The toggle must not be a URL parameter an attacker can send to a responder to hide a real alert. No real vessel names, owner names or phone numbers in fixtures.
- 🛠️ **Architecture / DX:** The data-source swap is the composition root's job: `dashboard-core.js` chooses `liveSource` or `demoSource` once at start-up, and modules stay unaware. Fixtures live next to the contract (`fixtures/dashboard_demo/`) and are validated by the same web tests that feed the pure renderers, so a contract change breaks the demo in CI rather than on stage. Time-relative fixtures (`"-00:47"` offsets resolved at load) keep "47 minutes ago" true. Keep the backend scenario engine as the separate full-path demo; the two answer different questions.

### 3. Consensus and tension

- **Where all seats agree:** one swap at the `authFetch` seam; all-demo or all-live per tab, never mixed; an always-visible banner; no network calls in demo mode; delete every scattered sample literal once the demo source serves it.
- **Core tension:** fidelity against honesty and upkeep. A richer demo (live-looking timelines, alarms, drift maps) sells better but costs fixture upkeep and risks being mistaken for reality; a minimal one is safe but may undersell the product.

### 4. The verdict

- **Recommended path:** a client-side demo data source behind `authFetch`, entered from the existing offline-demo button and a toggle in the header, with contract-validated, time-relative fixtures, in-memory mutations, a scripted timeline that replays a short incident story, and a banner plus watermark; then delete the scattered sample literals.
- **Revisit when:** a second consumer needs demo data (the handset, a training course), or fixture upkeep outgrows one person; then move the fixtures behind a backend demo tenant with its own database.

## Requirements (draft)

| ID | Requirement | Observable acceptance |
|---|---|---|
| DEMO-01 | Demo mode is entered from the login page's offline-demo button or a header toggle, and left from the same toggle; it lasts for the browser tab's session. It cannot be switched on by a URL alone. | Web test on the mode resolver; render check: toggle on and off. |
| DEMO-02 | In demo mode the dashboard makes no request to `/api/*`. | Render check: network log in demo mode has no `/api/` request. |
| DEMO-03 | A banner and a watermark that no panel covers say DEMO - SAMPLE DATA for the whole time; the LIVE badge never shows. | Render check screenshot of every tab and drawer. |
| DEMO-04 | Every dashboard feature has sample data: SOS feed and drawer, alerts, Trip Checks, vessel risk feed, squall nowcast, drift and search (with a searched sector and next area), advisories, buoys, sea conditions, operations status, SAR metrics. | Render check: each panel is non-empty in demo mode. |
| DEMO-05 | Actions work in memory: acknowledge, resolve and reply on an SOS; acknowledge, dismiss, escalate and resolve on a trip check; open, rerun and mark a searched area on a drift case. A reload restores the starting story. | Web tests on the in-memory store; render check of each action. |
| DEMO-06 | Fixtures follow the `docs/05` shapes and use relative timestamps. | Web test: every fixture passes through its pure renderer, and the contract examples in `docs/05` and the fixtures share their keys. |
| DEMO-07 | Outside demo mode no sample content exists anywhere in the dashboard source. | Web source check: no sample literal outside the demo source module and fixtures. |
| DEMO-08 | Fixtures contain no real person's name, phone number or licence number. | Web test over the fixture files. |

## Open questions for Len

| # | Question | Recommendation |
|---|---|---|
| Q1 | Offer the toggle on the deployed production dashboard, or only in the offline-demo entry? | Both, since the banner makes the mode unmistakable; revisit once MDRRMO responders use the console daily. |
| Q2 | A scripted timeline (an SOS arrives, a trip check escalates, a drift case opens) or a static snapshot? | Scripted, restartable, about three minutes. |
| Q3 | Keep the backend `DEMO_MODE` scenario engine alongside it? | Yes. It proves the real path end to end; this plan does not change it. |
| Q4 | Sound alarms in demo mode? | Off by default, with the normal "click to enable" control. |
| Q5 | The handset's pitch mode (`PITCH_MODE`) is out of scope? | Yes; a later plan may reuse the fixtures. |

## Phases (draft)

| Phase | Outcome | Requirements |
|---|---|---|
| 1 | The data-source seam: `liveSource` and `demoSource` chosen once in `dashboard-core.js`; mode resolver; banner and watermark; `demoSource` answers every route with an empty contract-shaped response | DEMO-01, -02, -03 |
| 2 | Fixtures for every panel, time-relative, validated against the pure renderers and the `docs/05` examples | DEMO-04, -06, -08 |
| 3 | In-memory store for the actions, reset on reload | DEMO-05 |
| 4 | Scripted timeline (if Q2 is yes) | DEMO-04 |
| 5 | Delete every scattered sample literal and add the source check; walkthrough with screenshots; update `docs/08`, the register and the index | DEMO-07 |

Each phase starts with red tests and ends with the web gate (`node --test test/*.test.js`, `node --check`) and the Plan 71 render check (`tools/render-check/`).

## Dependencies

- Starts after Plan 71 Phase 3, which removes the sample vessels and leaves the Vessels tab reading the real risk feed.
- Uses the Plan 71 render check and its screenshots as the baseline.
- Must land before the pitch dates in `docs/53` to be useful there; the current deadlines are RSTW 2026-10-01 and Enactus 2026-10-09.
