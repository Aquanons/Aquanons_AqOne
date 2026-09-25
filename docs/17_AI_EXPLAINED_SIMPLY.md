# 17 — The AI, Explained Simply

For the team. No jargon, no maths. If you read only the next six lines, that's enough.

---

## The whole thing in six lines

We have **three AIs in the backend**. Each one answers a different question:

1. **Squall** — "Is a storm about to hit? Tell them to come home."
2. **Trip anomaly** — "Is this boat late in a way that's unusual *for this boat*?"
3. **Drift** — "Someone is in the water. Where do we look?"

Plus a fourth that lives in the dashboard, not the backend:

4. **Danger zone** — "Which parts of the sea are dangerous today?"

That's it. Everything below is just detail.

---

## 1. Squall alerts — the early warning

**Question it answers:** is bad weather about to arrive?

**How it works, plainly:** PAGASA, the national weather agency, already issues
thunderstorm and wind warnings. We pull them from the PAGASA weather API, and
when one covers the fishing grounds we send a **RETURN NOW** alert through the
radio network to boats that have no phone signal.

Our buoys do not have a barometer. We don't make our own forecast; we carry
PAGASA's forecast to people who otherwise wouldn't hear it.

**Data in:** PAGASA advisories and forecasts, plus Open-Meteo wind and wave data.

**Data out:** a RETURN NOW warning, credited to PAGASA.

**What kind of AI:** none. This part is a relay, not a model.

**Honest caveat:** our warning is only as early and as local as PAGASA's. The
older pressure model in `backend/app/ai/squall.py` belonged to a buoy-barometer
design that has been dropped.

---

## 2. Trip anomaly — the "he should be back by now" detector

**Question it answers:** is this boat overdue?

**How it works, plainly:** The system quietly learns each boat's habits — what
time Juan usually leaves, which buoys he usually passes, roughly when he
usually comes back. Once it knows his normal pattern, it notices when he
breaks it.

**This is the important bit:** it is *not* a timer. It's not "alert after 6
hours." Six hours is nothing for one fisher and alarming for another. The system
compares each boat **against its own history**, which is why it can catch a
problem the same day instead of waiting for a family member to report someone
missing the next morning.

**Data in:** which buoys a boat passed, and when — over the last couple of weeks.

**Data out:** an anomaly flag with a confidence score, and an escalation stage.

**Where it lives:** `backend/app/ai/trip_profile.py`

**What kind of AI:** unsupervised statistical learning. It builds a profile per
vessel — averages, spread, typical ranges — with no library, just numpy. No
human ever labels "this trip was bad." It figures out normal on its own.

**It doesn't alarm immediately.** There are four stages, from a quiet check-in
request up to a full alert, so a slightly-late boat doesn't trigger a rescue.

**Honest caveat:** a brand-new fisher has no history yet, so it can't judge him.
And a fisher with genuinely irregular habits will trip more false alarms.

---

## 3. Drift prediction — the search map

**Question it answers:** someone went in the water at this spot, an hour ago.
Where are they *now*?

**How it works, plainly:** A person in the water doesn't stay put. Current
pushes them. Wind pushes them. So we simulate it: we release thousands of
imaginary particles from the last known position and let each one drift, each
with slightly different assumptions. Where most of them end up is where we
search.

The result isn't a dot on a map. It's a **shape** — the 50%, 75% and 95% zones.
"There's a 95% chance they're inside this outline."

**One thing that matters a lot:** as the Coast Guard searches an area and finds
nothing, we feed that back. "Not here" is information. The map updates and the
probability shifts elsewhere. The search area *moves* instead of staying frozen.

**Data in:** last known position and time, wind, current readings from buoys,
and what kind of object it is (a person floats differently than a swamped boat).

**Data out:** a probability map and search zones.

**Where it lives:** `backend/app/ai/drift.py` and `backend/app/ai/search.py`

**What kind of AI:** this one is **physics, not machine learning**. It's a Monte
Carlo simulation using published drift coefficients — the same family of model
real search-and-rescue services use. Don't call it "trained." Call it
"simulated" or "physics-based." That's more impressive anyway, and it's true.

**Honest caveat:** the current readings feeding it are simulated right now. The
code that reads real buoy currents is built and live — there just aren't real
buoys in the water yet.

---

## 4. Danger zone — the risk map (runs in the dashboard, not the backend)

**Question it answers:** which areas are dangerous today?

**This is the only model trained on real-world data.** Nearly two and a half
years of actual weather, wave and typhoon records for our waters — about 21,000
hours of it.

**Data in:** wind, gusts, rain, weather code, wave height, wave period, depth,
and time of year.

**Data out:** a risk score for each of **43 sectors** — 3 named New Washington
areas plus 40 offshore scan points across Aklan — drawn as coloured zones on the
map, each with a plain-English reason.

### The unusual part: it runs inside the browser

Every other AI we have runs on the server. This one doesn't. It runs on the
dispatcher's laptop, inside the web page.

Here's how that works:

1. **We train it once, offline.** `web/ml/train_danger_zone_model.py` runs on a
   laptop, downloads the real weather and typhoon data, and fits the model.
   This never runs in production — we run it by hand.
2. **We export the finished model into a text file.** `web/js/dangerZoneModel.js`
   is *one single line* holding the entire trained model as data — all **90
   decision trees**, every threshold and every branch, written out.
3. **We rewrote the "run the model" part in JavaScript.**
   `web/js/dangerZonePredictor.js` reads that file and does the maths in the
   browser.

**What this means practically:** when you open the dashboard, it fetches live
weather for all 43 sectors, runs the model right there on your machine, and
draws the map. It never asks our backend anything. **If Railway went down, the
danger zone map would still work.**

### Why this is worth mentioning

Judges sometimes ask "is your AI actually running, or is that just a picture?"

For this one the answer is strong: the model is executing live, in front of
them, on weather data fetched seconds ago. You can open the browser console and
watch it happen.

**Where it lives:** `web/ml/` (training + documentation) and
`web/js/dangerZoneModel.js` + `web/js/dangerZonePredictor.js` (the live model).

### Two extras already built in

- It factors in **buoy health** — degraded buoys in a sector raise the risk.
- It explains itself. Instead of just "risk 0.78," it produces readable reasons
  like which condition crossed which threshold.

### Honest caveats — there are three

**It learned "when is the weather bad," not "where do people die."** Those are
related but not the same. A calm day with an engine failure is invisible to it.
This is written into our own model card; we didn't wait to be asked.

**One feature does most of the work.** Wind gusts account for 78% of the
decision. It's a well-calibrated gust threshold with extras, not a deep
multi-factor model. Say that rather than overselling it.

**The depth data contributes nothing.** We pulled seabed depth from GEBCO and
the model scored its importance at exactly 0.0. We left it in the model card
rather than quietly deleting it.

---

## How they fit together

```
BEFORE the trip     →  Danger zone: is it safe to go out?
DURING the trip     →  Squall: a storm is coming, return now
AFTER he's overdue  →  Trip anomaly: something is wrong
ONCE we know        →  Drift: here's where to search
```

Four stages of one story: prevent, warn, detect, rescue.

---

## Where the numbers live

The dashboard's SAR tab shows real measured performance — accuracy, detection
time, and so on. **If it looks empty, that's on purpose.** We made it show
nothing rather than show made-up numbers. The figures only appear once someone
runs the evaluation scripts.

---

## If someone asks you a hard question

**"Is this real AI or just if-statements?"**
Two are trained models (squall, danger zone). One is unsupervised learning
(trip anomaly). One is physics simulation (drift). Only the last is not machine
learning — and it's the most sophisticated of the four.

**"Is it trained on real data?"**
The danger-zone model is. The other three are calibrated on simulated data,
because no dataset of Filipino fishermen's trips at sea exists — nobody has ever
collected one. That's exactly what the pilot is for.

**Don't guess.** "I'd have to check" is a perfectly good answer. Nothing here
breaks if we admit a limitation. It breaks if one of us overclaims and it turns
out to be false.
