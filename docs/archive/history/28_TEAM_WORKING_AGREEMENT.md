# 28 — Working Agreement for the Demo Sprint

**Status:** SUPERSEDED
**Owner:** Team Aquanons
**Created:** 2026-08-15
**Updated:** 2026-09-19
**Related:** [`AGENTS.md`](../../AGENTS.md)

> **Historical document:** Working agreement for the original 7-day demo sprint.
> Current team guidelines and conventions are maintained in [`AGENTS.md`](../../AGENTS.md).

Seven days, five people, one stage demo. This is how we work so that the
demo does not come down to one person merging everything at 3am.

---

## 1. Your branch is fresh, or it is dead

Branch from **current master, today**. Do not resume a branch you last
touched weeks ago — two of ours are 182 commits behind master, and
resuming one means spending the sprint resolving conflicts instead of
building.

```
git checkout master
git pull
git checkout -b <yourname>-demo
```

Then **every morning, first thing:**

```
git checkout master && git pull
git checkout <yourname>-demo && git merge master
```

Skipping this for a week is exactly how a branch ends up 182 behind. One
minute a day prevents a lost afternoon.

---

## 2. Done means merged to master

Not "done on my machine." Not "pushed to my branch." **Merged to master and
still working there.**

Work that only exists on your branch does not count, cannot be demoed, and
does not exist as far as the demo is concerned. Open the PR when the piece
works, not when the whole area is perfect.

**Merge deadline: day 5.** Day 6 is integration, day 7 is rehearsal. Nothing
merges on day 7.

---

## 3. One owner per file

So that two people never edit the same lines and nobody waits on a conflict
they cannot resolve alone.

| Area | Files | Owner |
|---|---|---|
| Scenario engine | `backend/app/demo/**`, `backend/app/api/demo.py`, `backend/migrations/015_*` | Lenard |
| Control panel | `web/html/demo-control.html`, `web/js/demo-control.js` | Lenard |
| Dashboard | `web/js/dashboard.js`, `web/html/dashboard.html`, `web/css/dashboard.css` | Jade |
| Handset | `mobile/lib/**` | DJ |
| Buoy | `firmware/**`, `arduino/**` | DJ |
| Ingest | `backend/app/api/sos.py`, `gateway/**` | Arnold |
| Weather proxy | `web/js/dangerZonePredictor.js` + its backend route | Arnold |
| Pitch | `docs/` deck and narrative | Doreen Kay |

`backend/app/main.py` is shared — Lenard adds two lines there and nobody
else touches it this sprint.

If you need a change in someone else's file, **ask them for it**. Do not
edit it yourself, even if the fix is one line. That one line is how a merge
turns into an argument.

---

## 4. Daily checkpoint, 15 minutes

Same time every day. Three sentences each:

1. What I pushed yesterday
2. What I am pushing today
3. What is blocking me

Not a status meeting — a forcing function. If you have nothing pushed two
days running, say so on day two, not on day six. A problem raised on day two
gets reassigned; a problem raised on day six becomes a cut feature.

---

## 5. Late work gets cut, not rescued

Every beat in the demo fires independently. If a piece is not merged by day
5, that beat comes out of the arc and the demo still runs.

This is a promise in both directions. Nobody has to pull an all-nighter to
avoid breaking the demo — and nobody should expect someone else to finish
their piece for them. **The lead is not the safety net this sprint.** If the
lead spends the week finishing everyone's work, the scenario engine does not
get built and there is no demo at all.

Ask for help early and it is help. Ask on day 6 and it is a takeover.

---

## 6. If you do not use git

Doreen — the pitch deck and narrative do not need to live in git. Your
deadlines are the same (day 5), your deliverables are the slides and the
demo narration, and "done" means shared with the team and rehearsed on
day 7. The one thing that must reach the repo is the honesty slide's
content, so it stays consistent with the README.

---

## Quick reference

| Day | What happens |
|---|---|
| 1 | Everyone branches fresh from master. Old branches abandoned. |
| 1–5 | Build. Merge master into your branch every morning. |
| 5 | **Merge deadline.** Everything lands on master. |
| 6 | Integration. Buoy + handset + dashboard together, for real. |
| 7 | Rehearse ×3. Record the screencast. Nothing new merges. |
