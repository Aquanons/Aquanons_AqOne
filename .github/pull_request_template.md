<!--
HOW TO USE THIS TEMPLATE
- Write every part yourself, in your own words. An AI never writes a pull request (rule R11).
- How to write each part, with an example: docs/76_PULL_REQUEST_WRITING_GUIDE.md
- The rules: docs/75_STAGING_AND_MERGE_RULES_DECISION.md
- Pull requests go into `staging`. Only a release pull request from `staging` may target `master`.
- Open this as a DRAFT the moment you start, with just the title and Summary. Fill in the rest before you mark it ready.
- Title format: type(area): what changed      example: fix(mobile): logging out returns to the welcome screen
-->

## 1. Summary

<!-- Two or three sentences. What does this pull request do? -->

## 2. Why

<!-- The problem as a person would see it, then the cause. Link the plan, spec or bug report. -->

## 3. What changed

<!-- One line per file: the file, then what changed in it. -->

Areas touched:

- [ ] backend
- [ ] database migration
- [ ] web
- [ ] mobile
- [ ] firmware
- [ ] docs only

## 4. How it works

<!-- Explain the approach to a teammate who has not seen the code. Where does it sit in the SOS path or the system? Why this way? -->

## 5. What could break

<!-- What else uses the code you touched? Which shared contract does it touch? -->

## 6. How I tested it

**Automated** (command and the last line of its output):

**By hand** (steps, device, what you saw):

**Not tested** (what, and why):

## 7. How to undo it

<!-- Usually "Revert this pull request". Say so if a migration ran or a board must be reflashed. -->

## 8. Documents updated

<!-- The documents changed in this same pull request. -->

## 9. What I am unsure about

<!-- What you do not fully understand, or what the reviewer should check hardest. -->

**AI use on the code:** <!-- for example: "An AI agent wrote the code; I reviewed every line." or "None." -->

- [ ] I wrote this description myself, and I can explain every part of it out loud.

---

## Release checklist - fill in ONLY when this pull request targets `master`

Delete this section for a pull request into `staging`.
Every box that applies must be ticked before the merge.
Copy of `docs/75_STAGING_AND_MERGE_RULES_DECISION.md` Section 5; that document wins if they differ.

**Tested by (not the author):**
**Devices used:**
**Staging commit tested:**

### A. Automated

- [ ] Checks for every area touched are green on the staging commit, output pasted above

### B. Database (only if `backend/migrations/` changed)

- [ ] New numbered migration file; no existing migration edited
- [ ] `python migrate.py` ran clean on an empty database
- [ ] `python migrate.py` ran clean on the staging database holding older data
- [ ] `python migrate.py` ran a second time with no error and no change
- [ ] The backend on `master` today still works against the migrated database, or Len accepted that rollback is not possible
- [ ] Production dump taken just before this merge

### C. Physical tests on real devices, against staging

- [ ] Staging `/health/ready` is green and reports the commit being released
- [ ] Real Android phone with a staging build sends an SOS
- [ ] Dashboard in a real browser shows it in the live feed without a reload
- [ ] Acknowledge on the dashboard, reload, acknowledgement still there
- [ ] Phone shows the delivery states honestly, up to `acknowledged`
- [ ] SOS resolved; no errors in the dashboard browser console
- [ ] LoRa path: button press on a real pod travels through the real shore gateway and appears on the dashboard
- [ ] LoRa path: phone in airplane mode on the pod WiFi sends an SOS that appears on the dashboard
- [ ] Mobile changes: changed screens walked on the phone in light and dark mode, English and Aklanon; fresh install and install over the previous APK
- [ ] Web changes: changed pages used in Chrome at the dispatch-desk screen size
- [ ] Backend changes: changed endpoints exercised through the app or dashboard
- [ ] Firmware changes: both real boards flashed from this commit before the LoRa lines were run

### D. Sign-off

- [ ] Tester is not the author
- [ ] Every change in this release has its understanding check answered, and the release owner can explain what the release changes
- [ ] Len reviewed every change in this release
- [ ] Result recorded in `docs/08_DEMO_AND_STATUS.md`
- [ ] Affected documents updated in the same pull requests (contract, plan, Current Register)
- [ ] No event freeze is active
- [ ] No secret in the diff

### E. After the merge (release owner, within 10 minutes)

- [ ] Production `/health/ready` is green and reports the merge commit
- [ ] Dashboard loads and the live feed shows existing incidents
- [ ] Team told the release is live
