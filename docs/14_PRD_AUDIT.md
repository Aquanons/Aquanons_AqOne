# 14 — PRD Audit

What the PRD promises versus what master actually does. Evidence taken from the
code on `0ce348a`, not from documentation.

Audited against **Aqone_PRD.md v2.0**. Note that a **v3.0** exists adding §5.4
mass-casualty dispersion, §5.5 live roster and §5.6 nearest-responder broadcast.
None of those three are built. Pick one version as canonical before anyone else
audits this.

---

## Verdict

The three AI components in §5 are real and measured. The **single most important
claim in the document is not implemented**, and four supporting claims are
missing. Nothing is fabricated - the gaps are absences, not fakes.

| | |
|---|---|
| Implemented and measured | squall nowcasting, trip anomaly, drift prediction |
| **Claimed but absent** | **learned current field feeding drift** |
| Also absent | Bayesian re-tasking, survivability weighting, residual learning, buoy-side alert, phone↔buoy messaging |

---

## 1. The gap that matters most

PRD §5.3(a) is set apart in a blockquote as **"the core insight of the entire
product"**:

> The buoys exist to carry messages. As a byproduct they generate the exact
> oceanographic dataset required to find drifting people - a dataset that cannot
> be replicated without first building the network.

**It is not wired up.**

```
drift.py reads current_observations from the database : NO
drift.py uses _synthetic_current_vector               : YES
```

The generator produces `current_observations` (16 references) and the migration
creates the table, but `predict_drift` never reads it. It advects particles
through its own synthetic current field instead.

So the moat argument - the reason a judge should believe nobody can copy this -
is currently a claim with no code behind it. Everything else in the audit is
less important than this.

**Fix:** load the per-buoy current observations, interpolate them onto the
particle positions, and fall back to the synthetic field when the array has no
coverage. Roughly an afternoon. It also makes the containment metric mean
something, because the model would then be corrected by the same array the
product sells.

---

## 2. Claimed in §5.3, not present

| Claim | Status |
|---|---|
| "As assets search sectors and report negative findings, the posterior updates and re-tasks them" | **Not implemented.** No posterior update, no sector state. The contours are static once computed. |
| "Survivability weighting prioritises tasking when incidents compete for one asset" | **Not implemented.** No time-in-water model anywhere. |
| "Residual learning - improves with every actual recovery" | **Not implemented.** No path from a real outcome back into the model. |

The first is the one a SAR-literate judge will ask about, because Bayesian
search allocation is the standard of the field and the PRD names it explicitly.

---

## 3. Claimed elsewhere, not present

**§5.1 buoy-side physical signalling.** The PRD promises buoys "carry a physical
alert - light or audible signal - so a vessel in visual range receives the
warning with no phone contact at all." Nothing in `firmware/` implements this.

**§4.4 opportunistic messaging.** The PRD's stated everyday hook is "messages
queued on the phone and delivered on passing a buoy." `buoy_client.dart` speaks
only `/v1/status` and `/v1/sos`. **There is no messaging.** This matters beyond
a feature gap: §4.4 is the adoption argument for why a fisher keeps the app
installed at all.

---

## 4. What is genuinely built

| PRD section | Evidence |
|---|---|
| §5.1 squall nowcasting | 8 spatial propagation features, LogisticRegression pipeline, model committed |
| §5.2 trip anomaly | learned per-vessel profiles, 4-stage escalation ladder, itemised factor breakdown |
| §5.3 drift | 3 object classes with distinct leeway, 50/75/95% contours, calibrated uncertainty |
| §7 hotspot removed | only two matches remain, both in a code comment |
| §4.2 buoy instrumentation | GPS, current sensing, two radios, mesh chained to shore (barometer since dropped for the PAGASA weather API) |

---

## 5. Success metrics (§6)

Seven of ten are measured by the eval scripts:

```
containment_rate            measured
search_area_reduction       measured
median_detection_latency    measured
false_alarm_rate            measured
mean_lead_time              measured
precision / recall          measured
```

Three cannot be measured because no data source exists, and should be cut from
the PRD or explicitly marked as post-deployment:

- **Survival rate of alerted incidents** - requires real rescues
- **Buoy coverage of municipal waters** - computable today from the polygon and
  the buoy array; currently nobody computes it
- **App adoption** - requires real users

Buoy coverage is the cheap one: the water polygon and the WiFi radii are both
in code, so it is a percentage-of-area calculation and nothing more.

---

## 6. Priority order

1. **Wire the learned current field into drift prediction.** The PRD's central
   claim. Half a day. Nothing else moves the pitch as much.
2. **Compute buoy coverage.** An hour, and it retires a success metric.
3. **Bayesian re-tasking**, even a simple version: mark a sector searched,
   renormalise the remaining probability mass. Half a day, and it answers the
   question a SAR-literate judge will actually ask.
4. **Reconcile the PRD versions.** Decide whether v3's three extra features are
   scope or aspiration, and say so in one document.
5. **Phone↔buoy messaging**, or amend §4.4 to stop claiming it.
6. **Survivability and residual learning** - defer, and describe them as roadmap
   rather than built.

---

## 7. Honesty notes for the pitch

- The models are calibrated on **synthetic** data. The eval numbers are real
  measurements of the models against that data; they are not field results.
- The squall classifier is trained on squalls the generator injected, so its
  precision measures self-consistency rather than meteorological skill. The
  danger-zone GBDT on the branch is trained on real Open-Meteo history and is
  the stronger claim.
- `unsafeWindKph = 30` in `mobile/lib/core/config.dart` drives the sail-safety
  label. It is a **single hardcoded threshold**, not a model and not an official
  warning. Either present it as a rule of thumb with its source and timestamp,
  or stop calling it a safety verdict.
