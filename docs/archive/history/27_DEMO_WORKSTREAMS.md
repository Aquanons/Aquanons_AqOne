# 27 — Demo Workstreams

**Status:** SUPERSEDED
**Owner:** Team Aquanons
**Created:** 2026-08-15
**Updated:** 2026-09-19
**Related:** [`docs/08_DEMO_AND_STATUS.md`](../08_DEMO_AND_STATUS.md), [`docs/26_DEMO_BUILD_PLAN.md`](../26_DEMO_BUILD_PLAN.md)

> **Historical document:** Historical demo sprint workstreams and ownership mapping for AI Fest 2026.
> See [`docs/08_DEMO_AND_STATUS.md`](../08_DEMO_AND_STATUS.md) for current demo status and evidence.

Companion to [`26_DEMO_BUILD_PLAN.md`](../26_DEMO_BUILD_PLAN.md). That document
is the architecture; this one is who owns what.

**Written the way this team works.** Everyone owns their own area, so what
follows is *outcomes and contracts*, not implementation instructions. How you
build it is yours. What the demo needs from you, and by when, is not.

---

## Decisions locked

| Decision | Value |
|---|---|
| Demo mechanism | Backend scenario engine, `DEMO_MODE`-gated |
| Control | Presenter panel, beat-by-beat |
| Deployment | Separate Railway service + separate DB |
| **Handset on stage** | **In the loop, via the real buoy AP — phone in airplane mode** |
| Fleet markers | Static. No moving-vessel ticker. |
| Panel operator | TBD — not Lenard, he is presenting |
| Timeline | ~1 week, rehearsal on day 7 |

The handset decision is what changed the shape of this. It puts **Daniel on
the critical path** and makes the mobile app a demo deliverable rather than a
background item.

---

## The arc everyone is building toward

Six beats, ~6 minutes. Full detail in `26_DEMO_BUILD_PLAN.md` §4.

```
0  Baseline          fleet at sea, all green
1  Pressure falls    squall probability climbs
2  Zones escalate    north sectors amber → red
3  RETURN NOW        advisory published → HANDSET ALARMS
4  Boat overdue      BANCA-7 flagged against its own profile
5  SOS + drift       capsize → 50/75/95 contours
6  Ack + re-task     ETA to handset → negative sector → contours move
```

Beats 3 and 6 are the two that reach the phone. Everything else is dashboard.

---

## Lenard — scenario engine + deployment

Branch: `demo` off master.

- `DEMO_MODE`-gated router, migration `015_demo.sql`, surgical reset
- Six beats writing real rows into real tables
- Open-Meteo–shaped weather proxy (danger zones are browser-side — §3 of the plan)
- Presenter control panel
- Second Railway service, seeded, evals run

**Owes the team by day 5:** the demo backend URL and the `X-Demo-Key`.
Daniel cannot flash and mobile cannot build without the first one.

**Calibrate the pressure series before building the panel.** Squall recall is
0.133; a series that does not cross the threshold gives you a beat 3 where
nothing happens and a handset that never alarms.

---

## Daniel — buoy (critical path)

You are load-bearing now. The handset reaches the backend through your AP.

What the demo needs:

- One buoy that boots reliably and **holds the `Aquan` AP for 15+ minutes**
  with a phone attached — the pitch plus judges' questions, not just the 6
  minutes of the arc
- Uplink pointed at the **demo** backend, not production. URL from Lenard day 5.
- A rehearsed recovery if it browns out mid-demo. Beat 5's SOS is queued in
  flash — a power-cycle that still delivers is a *feature* worth showing.
- A second flashed buoy as a cold spare. Non-negotiable for stage hardware.

**Separate ask — the outdoor range test.** Still ❌ in the README, and every
range figure the team quotes is a datasheet number. Judges ask this. A rough
measured figure from a real afternoon beats a spec sheet, and "we measured
X metres" is a much better answer than "the datasheet says".

---

## Jade — dashboard

Every beat renders through your code. The wiring exists — `dashboard.js`
already calls `/api/ai/drift/incidents`, `/incident/{id}`,
`/api/ai/squall/current`, `/api/ai/anomaly/active`, and the layers and panes
are created. This is finishing, not building.

Working by rehearsal:

- Drift contours at all three levels, **and they visibly change** after
  `POST /incident/{id}/searched` — this is beat 6, the single most
  memorable moment in the demo
- Vessel track layer draws the last-known trail / `ground_truth_track`
- Squall trace and legend appear from the live feed and **clear correctly**
  when detections drop to zero — a legend stuck on-screen at beat 0 kills
  the before/after contrast
- `toggle-drift`, `toggle-squall`, `toggle-danger-zones` all work both ways

**You are not blocked on Lenard.** The 14-day synthetic dataset already in
the DB exercises all of these today. Start now; switch to the demo
deployment around day 5 to see it under the real arc.

---

## Jade + Doreen Kay — mobile

The handset is now a demo deliverable. It must alarm at beat 3 and show the
ETA countdown at beat 6, **in airplane mode, joined to Daniel's buoy**.

Three things stand in the way, all from last sprint:

1. **Nothing was verified.** No `flutter analyze`, no `flutter test` — no SDK
   in the environment those changes were made in. Manually reviewed only.
2. **`mobile/AqOne.apk` is stale**, a pre-sprint build. It does not contain
   the fixes below.
3. **The fixes the demo depends on are exactly the unverified ones.** The
   buoy IP correction (`10.0.0.1` → `192.168.4.1`), the field names
   (`uplink`, `queue_depth`, string `buoy_id`), and the offline ETA-polling
   fallback. Beats 3 and 6 ride on all three.

So: run the toolchain, rebuild against the demo backend
(`--dart-define=BACKEND_BASE_URL=…`), and **exercise it on Daniel's actual
hardware**, not a simulator. Pair up with him early — this is the integration
most likely to fail on stage and the one with the least slack.

---

## Arnold — ingest

- SOS de-duplication holds under the demo's injected traffic, including a
  rehearsal reset followed by a re-run with the same `client_ts`
- **Settle the gateway question:** the buoy sketch is WiFi-only and the
  multi-hop LoRa mesh is not implemented. If the gateway is not in the stage
  path, that should be said plainly in the pitch rather than left for a judge
  to discover in the repo.
- Available as overflow for the weather proxy if Lenard's plate overruns —
  it is an ingest-shaped problem and the most separable piece of his work.

---

## Doreen Kay — pitch and UI

- Narrative mapped to the six beats, so the words and the screen move together
- The framing line, said out loud: **the weather is scripted, the inference is
  real.** This is the demo's credibility. Do not let it go unsaid and get
  discovered instead.
- Honesty slide: synthetic calibration on three of four models, squall recall
  0.133, no outdoor range test. Volunteering limitations reads as rigour;
  being caught on them reads as spin.
- Control panel is functional, not pretty — but the operator has to read it
  under stage lights while nervous. Contrast and size over polish.

---

## Integration contracts

Three places workstreams touch. Agree these before day 4, not during rehearsal.

| Contract | Between | Needed by |
|---|---|---|
| Demo backend URL | Lenard → Daniel, mobile | Day 5 |
| `X-Demo-Key` | Lenard → panel operator | Day 6 |
| Beat 3 advisory payload shape | Lenard ↔ mobile | Day 4 — must match what `squall_alarm.dart` already polls, or the phone stays silent |

---

## Rehearsal

Day 7. Three full run-throughs, buoy powered, phone in airplane mode, panel
operator driving.

**Record the screencast during rehearsal.** It is a deliverable in its own
right and it is the insurance policy if the venue wifi, the buoy, or the
Railway service fails on the day.
