# 75 - Staging branch and merge-to-master rules

**Status:** ACTIVE - the rule applies now; the setup steps in Section 9 are still open
**Owner:** Lenard
**Created:** 2026-10-01
**Updated:** 2026-10-01
**Related:** `docs/76_PULL_REQUEST_WRITING_GUIDE.md`, `render.yaml`, `Dockerfile`, `docs/runbooks/RENDER_FREE_DB_ROTATION.md`, `.github/pull_request_template.md`, `AGENTS.md`

Everyone on the team reads Sections 1, 2, 4, 4A, 4B, 5 and 7 and the pull request guide in [`76_PULL_REQUEST_WRITING_GUIDE.md`](76_PULL_REQUEST_WRITING_GUIDE.md) once, then adds their name in Section 13.
The rest is reference.

## 1. The rules

These eleven rules exist for two reasons.

1. **We do not break production.**
   `master` is production: every merge to it deploys to Render and runs the database migrations on the live database.
2. **Every one of us has a high technical understanding of what AqOne is and how it works.**
   Not only of our own part, and not only enough to get a change merged.

Speed is not a goal.
When a rule slows you down, it is doing the second job.

| # | Rule | In practice |
|---|---|---|
| R1 | **One problem, one owner.** | Check the open pull requests before you start. If someone has it, help them; do not start a second fix. |
| R2 | **Claim it where everyone can see.** | Push your branch and open a draft pull request before you write the fix. A branch only on your laptop claims nothing. |
| R3 | **Nobody pushes to `master` directly.** | Not Len, not a teammate, not an AI agent. |
| R4 | **Every change goes to `staging` first.** | Your pull request targets `staging`, never `master`. |
| R5 | **A person tests it on real devices.** | Passing automated tests is required, but it is not enough. |
| R6 | **The tester is not the author.** | You cannot sign off your own change. |
| R7 | **`master` changes only through a release pull request from `staging`.** | With the checklist in Section 5 fully ticked. |
| R8 | **An unticked box blocks the release.** | "Not verified - no device" means it does not ship yet. |
| R9 | **You understand every line you send to `staging` or `master`.** | If an AI wrote it, the AI asks you questions about it first, and you answer in your own words (Section 4A). |
| R10 | **You understand the system, not only your change.** | You can explain the whole SOS path and your own area without notes (Section 4B). No exceptions, Len included. |
| R11 | **You write the pull request yourself, in the team format. An AI never writes it.** | Nine parts, in your own words. The format and a worked example are in [`76_PULL_REQUEST_WRITING_GUIDE.md`](76_PULL_REQUEST_WRITING_GUIDE.md). |

```text
your branch --PR--> staging --(test on real devices)--> release PR --> master --> production
                       ^                                    ^
               automated checks green             checklist fully ticked
                                                  tester is not the author
```

## 2. Why these rules exist

This is not about blame.
The process allowed both problems below, so the process is what changes.

**What happened on 2026-10-01**

*Three people fixed the same bug at the same time.*
Fishers could not log out.
One fix was pushed to a personal branch at 10:56 (`c550dc1`).
Eleven minutes later a second fix was started on another branch (`0389d6f`) that was never pushed.
The two fixes solve the bug in different files and conflict with each other when merged.
Nobody could see that someone else already had it.

*A feature push broke the LoRa path and nobody noticed.*
The pod to gateway to backend path worked before the recent feature merges.
It was only found broken when someone tested with the real boards afterwards.
No firmware file has changed in the repository since 2026-09-25, so the cause is most likely outside `firmware/`.
The cause is not confirmed yet; when it is, it is recorded in `docs/08_DEMO_AND_STATUS.md`.

**What each rule would have changed**

| What went wrong | Rule that stops it |
|---|---|
| Nobody knew a fix was already in progress | R1, R2 |
| A fix sat on a laptop where nobody could see it | R2 |
| Features reached `master` without the real SOS path being run | R4, R5, R7 |
| "I did not touch firmware" felt like a reason to skip the LoRa test | R5 - the LoRa lines are in every release (Section 5C) |
| The person who wrote the change was the only one who checked it | R6 |
| "Not verified - no device" was recorded and the change shipped anyway | R8 |

**The cause underneath both**

Every one of us builds this codebase mostly through AI agents.
All of us, Len included, have been pushing to `master` without understanding the system the code goes into.
The agents wrote code that passed its tests, we sent it on, and the gap between what the repository does and what we understand kept growing.
That is why a feature could break the LoRa path without its author seeing the link, and why a bug turned into panic instead of a diagnosis.

Using AI is not the problem and nobody is asked to stop.
Sending code we cannot explain is the problem.
R9, R10 and R11 exist for that, and they apply to everyone, Len first.

**One more risk the rules cover**

`render.yaml` deploys `master` on every push, the `Dockerfile` runs `python migrate.py` before the server starts, and the free Render database has no backups.
A bad migration on `master` could lose every SOS record.
R3 and Section 5B exist for that.

## 3. The three kinds of branch

| Branch | What it is | Who can change it | What it deploys to |
|---|---|---|---|
| Your branch (`feat/...`, `fix/...`, `docs/...`) | Work in progress | You | Nothing |
| `staging` | Everything waiting to be tested | Pull request only, reviewed and merged by Len | The staging backend and its own database (Section 8) |
| `master` | What fishers and MDRRMO use | Release pull request from `staging` only, merged by Len | Production on Render |

## 4. How a change reaches master

1. **Claim it first.**
   Look at the open pull requests on GitHub.
   If someone already has this problem, help them there; do not start a second fix.
   If nobody has it, branch from `staging`, push the branch straight away, and open a **draft pull request** into `staging` yourself, with the title and a Summary saying what you are fixing.
   The draft pull request is the claim.
   A branch that exists only on your laptop claims nothing.
   `git fetch origin`, `git switch -c fix/my-change origin/staging`, `git push -u origin fix/my-change`.
2. **Do the work and keep it pushed.**
   Push at least once a day.
   Update the documents the change affects in the same pull request, never in a separate one.
3. **Pass the understanding check** (Section 4A).
4. **Write the pull request description yourself** (R11), in the format in [`76_PULL_REQUEST_WRITING_GUIDE.md`](76_PULL_REQUEST_WRITING_GUIDE.md).
   No AI writes, drafts, or polishes it.
5. **Mark the pull request ready.**
   Bring the branch up to date with `staging` first.
   Run the automated checks for every area you touched (Section 5A) and paste the results.
   Len reviews it and merges it.
   Nobody else can merge into `staging`.
6. **Test on staging with real devices.**
   Someone who did not write the change runs the physical tests (Section 5C) against the staging backend.
7. **Open a release pull request from `staging` into `master`.**
   The release owner writes it, and the pull request template holds the checklist.
   Tick every box that applies and name who tested.
8. **The release owner merges it.**
   Use "Create a merge commit".
   Never squash a release, or `staging` and `master` drift apart.
9. **Watch production for 10 minutes** (Section 5E).
   If anything is red, follow Section 6.
10. **Delete the branch** once it is merged.
   Old branches that fall far behind are how conflicting copies of the code survive.

Keep releases small.
One or two changes per release are easy to test and easy to roll back.

## 4A. The understanding check (R9)

You are responsible for the code you send, whoever or whatever typed it.
"The AI wrote it and the tests pass" is not understanding.

**When it happens:** before a pull request is marked ready for `staging`, and again for the release owner before a release to `master`.
Pushing your own branch as a draft to claim the work (R2) does not need it.

**If an AI agent helped write the change, the agent runs the check.**
Before it pushes for review or marks the pull request ready, it asks you at least three questions about this exact change and waits for your answers.

1. **What does it do?**
   What did this change, in which files, and why was it needed?
2. **Where does it sit in the system, and what could it break?**
   Which step of the SOS path does this code belong to, what else calls or depends on it, and which shared contract does it touch (LoRa frame, phone to pod, ingest, public API, delivery states, database)?
3. **How do you prove it and undo it?**
   How will you test it on a real device, and how do you take it back out if it is wrong?

The agent asks about the real diff, not general questions.
For example: "This changes how a pod delivery without a nonce is matched. What happens to an SOS that arrives from the pod before the phone's own call?"

**How the agent judges the answers:**

- You answer in your own words; the agent does not give the answer first.
- The agent compares your answer with the code.
- If an answer is wrong or vague, the agent explains that part, then asks a new question about it.
- The agent does not push for review until the answers are right.
- "I don't know" is an honest answer and a good one: it starts the explanation, it does not end the work.

**If no AI was involved,** you write the same three answers yourself, and the reviewer may ask more.

**Where it shows:** in the pull request description you write yourself (R11).
Parts 4, 5, 6 and 7 of the format are the same three questions, answered in writing.
The agent does not write them for you and does not paste its own summary into the pull request.
The reviewer reads them and may ask you to explain any line in person.

The check is there to teach, not to catch people out.
If you cannot explain a change yet, the right move is to learn it, shrink it, or ask the area owner, not to send it.

**This runs on honesty.**
You could paste the questions into another AI and copy its answer.
Nothing in the tooling stops that, and it only cheats you.
The real backstop is a teammate: any reviewer may ask you to explain a change out loud, without the screen.

## 4B. Know the system (R10)

The understanding check covers one change.
It does not help if you cannot place that change in the system.
So each of us does this once, and again when our area changes a lot.

**Step 1 - read, in this order.**

| Read | To learn |
|---|---|
| [`00_START_HERE.md`](00_START_HERE.md) | What AqOne is and the build order |
| [`56_TECHNICAL_ARCHITECTURE_AND_DATA_FLOW_SPEC.md`](56_TECHNICAL_ARCHITECTURE_AND_DATA_FLOW_SPEC.md) | How data moves through the whole system |
| [`06_DELIVERY_STATES.md`](06_DELIVERY_STATES.md) | The four states and what evidence each one needs |
| [`19_HELTEC_DATA_FLOW.md`](19_HELTEC_DATA_FLOW.md) | What the boards do with a frame |
| [`18_BACKEND_STRUCTURE.md`](18_BACKEND_STRUCTURE.md) | Where things live in the backend |
| The guide for your own area in [`guides/`](guides/) | Your part in depth |

Reading with an AI agent is fine and encouraged.
Ask it to explain, then to quiz you, not to summarise so you can skip the reading.

**Step 2 - the walkthrough.**
Explain these to a teammate, out loud, without notes or a screen.

1. An SOS from button press to acknowledgement: phone, pod, LoRa, shore gateway, backend, dashboard, and back.
   Name what each hop sends and what proves the hop happened.
2. The four delivery states, and why the app may never show a state it has no evidence for.
3. What happens when a hop fails: no pod in range, the gateway has no internet, the backend is asleep.
4. For your own area: its main files, what it promises to the other areas, and which contract document holds that promise.
5. What a merge to `master` sets off, from the push to the live database.

The teammate listening asks questions.
Where you get stuck is your reading list, not a failure.

**Step 3 - record it** in Section 13: the date and who listened.

Until your walkthrough is recorded, you can still open pull requests, but someone who has done theirs must review each one.
This is the same for everyone.

**Agents help keep it alive.**
When an understanding-check answer shows a gap in how the system works, not just in the change, the agent says so and points to the document above that covers it.

## 5. The checklist before merging to master

This list is copied into `.github/pull_request_template.md`.
If the two ever differ, this document wins.

### A. Automated checks - run on the `staging` commit being released

Run the rows for every area that changed.

| Area changed | Commands | Must show |
|---|---|---|
| `backend/` | `python -m pytest -q` and `python -m ruff check .` | All tests pass, no lint errors |
| `web/` | `node --test web/test/*.test.js` and `node --check` on every `.js` | All tests pass |
| `mobile/` | `flutter analyze` and `flutter test` | No issues, all tests pass |
| `firmware/` | `pio run -d firmware` and `diff firmware/buoy/AqOneBuoy/AqOneLoam.h firmware/shore/AqOneShore/AqOneLoam.h` | Both builds succeed, `diff` prints nothing |

- [ ] Every row that applies is green, and the output is pasted in the release pull request.

### B. Database - required when `backend/migrations/` changed

- [ ] The change is a new numbered migration file.
      No existing migration was edited (`git diff --stat origin/master -- backend/migrations` shows only new files).
- [ ] `python migrate.py` ran clean on an empty database.
- [ ] `python migrate.py` ran clean on the staging database while it held older data.
      This is the path production will take.
- [ ] `python migrate.py` ran a second time with no error and no change.
      Production runs it on every deploy.
- [ ] The backend that is on `master` today still works against the migrated database, or the release pull request says rollback is not possible and Len accepted that.
- [ ] A production dump was taken just before the merge (steps 2 to 4 of `docs/runbooks/RENDER_FREE_DB_ROTATION.md`).

### C. Physical tests - on real devices, against staging

**Core path - every release, whatever changed:**

- [ ] Staging `/health/ready` is green and reports the commit being released.
- [ ] A real Android phone with a staging build sends an SOS.
- [ ] The dashboard in a real browser shows that SOS in the live feed without a reload.
- [ ] Acknowledge on the dashboard, reload the page, and the acknowledgement is still there.
- [ ] The phone shows the delivery states honestly, up to `acknowledged`.
- [ ] The SOS is resolved and the dashboard browser console shows no errors.
- [ ] **LoRa path:** a button press on a real pod travels through the real shore gateway and appears on the dashboard.
- [ ] **LoRa path:** a phone in airplane mode, joined to the pod WiFi, sends an SOS that appears on the dashboard.

The two LoRa lines are in the core path on purpose.
On 2026-10-01 this path was found broken although no firmware had changed, so "I did not touch firmware" is not a reason to skip them.

**Extra tests for the area that changed:**

- [ ] **Mobile:** every changed screen was walked on the real phone, in light and dark mode, in English and Aklanon.
      The build was installed twice: once fresh, and once over the previous APK.
- [ ] **Web:** every changed dashboard page was used in Chrome at the dispatch-desk screen size.
- [ ] **Backend:** every changed endpoint was exercised through the app or the dashboard, not only through pytest.
- [ ] **Firmware:** both real boards were flashed from the release commit before the LoRa lines above were run.

### D. Sign-off

- [ ] The tester is not the author, and the tester's name is in the release pull request.
- [ ] Every change in this release has its understanding check answered in its pull request (Section 4A), and the release owner can explain what the release changes.
- [ ] Len reviewed every change in this release.
- [ ] What was tested, on which devices, and the result is recorded in `docs/08_DEMO_AND_STATUS.md`.
- [ ] Every document the change affects was updated in the same pull requests: the contract, the plan, and the Current Register.
- [ ] No event freeze is active (`docs/53_EXTERNAL_DEADLINES.md`).
- [ ] No secret is in the diff.

### E. After the merge - the release owner, within 10 minutes

- [ ] `https://aqone-backend.onrender.com/health/ready` is green and reports the merge commit.
- [ ] The dashboard loads and the live feed shows existing incidents.
- [ ] The team was told the release is live.

## 6. If production breaks

1. **Tell the team at once**, and stop all other merges.
2. **Put the last good version back.**
   In the Render dashboard, redeploy the last good commit of `aqone-backend`.
3. **Revert on GitHub.**
   Open a pull request that reverts the release merge commit.
   This is the only pull request that may target `master` without coming from `staging`.
4. **Remember that reverting code does not undo a migration.**
   Never edit or delete the migration that ran.
   Fix the schema with a new numbered migration, and take that fix through `staging` like any other change.
5. **Record what happened** in `docs/08_DEMO_AND_STATUS.md`: what broke, why the checklist did not catch it, and which checklist line is added so it is caught next time.

## 7. When something is broken and urgent

Panic is when three people fix the same thing.
So the first move is to talk, not to code.

1. **Say it in the team chat:** what is broken and who saw it.
2. **One person takes it** and says so in the chat: "I have the logout bug."
   That person opens the draft pull request (Section 4, step 1).
3. **Everyone else stops.**
   Help by reproducing the bug, testing, or reviewing; do not open a second fix.
   This includes asking an AI agent to fix it: check the open pull requests first.
4. **If two fixes already exist,** Len picks one and the other is closed, not merged.

There is no emergency shortcut around testing.
An urgent fix takes the same path: draft pull request, `staging`, physical test, release pull request.
What shrinks is the size of the change, not the testing.
The core path in Section 5C is always run.

## 8. What "staging" means

Staging is a backend that runs the `staging` branch against **its own database**, reachable over **HTTPS**.
It never uses the production `DATABASE_URL`.

Two facts shape how it is set up:

- The production Render workspace cannot host it.
  It allows one free database, and a second free web service would use up the monthly instance hours and suspend production (`docs/runbooks/RENDER_FREE_DB_ROTATION.md`, Section 1).
- A phone cannot reach a backend on a laptop over plain HTTP.
  The app allows cleartext only to the pod at `192.168.4.1` (`mobile/android/app/src/main/res/xml/network_security_config.xml`).

So staging is one of these, and Len chooses in Section 9:

| Option | How | Trade-off |
|---|---|---|
| Hosted staging (recommended) | A second Render workspace that deploys the `staging` branch with its own free database | Always available to every tester; its database also expires every 30 days |
| Laptop staging | Local PostgreSQL and `uvicorn` on the `staging` branch, published through an HTTPS tunnel | No second account; only works while that laptop is on |

Staging builds of the app point at the staging URL:

```bash
flutter build apk --release --dart-define=BACKEND_BASE_URL=<staging https url>
```

For firmware tests, the shore board is flashed with the staging URL and the staging `GATEWAY_API_KEY`, then flashed back.
Staging has its own secrets.
Never copy a production secret into staging.

## 9. Setup still to do

The rule applies from 2026-10-01 by agreement.
Until these steps are done, GitHub does not enforce it.

| Step | Owner | Done |
|---|---|---|
| Add a GitHub Actions workflow that runs Section 5A on every pull request, and make it a required check | Len | No |
| Decide how the shore gateway is pointed at staging for the LoRa lines without reflashing it for every release | Daniel and Len | No |
| Create `staging` from `master` once `master` is healthy: `git push origin origin/master:refs/heads/staging` | Len | No |
| GitHub branch protection on `master` and `staging`, and teammate roles set to Write (Section 9A) | Len | No |
| Choose and build the staging environment (Section 8) | Len | No |
| Retarget open pull requests and in-flight branches to `staging` | Each author | No |

## 9A. GitHub settings that enforce the rules

Len sets these once, in the repository on GitHub, under **Settings > Branches > Add branch protection rule**.
The repository is public and owned by the `Aquanons` organization, so these settings are free.

Make two rules with the same settings, one for `master` and one for `staging`.

| Setting | Value |
|---|---|
| Branch name pattern | `master` (second rule: `staging`) |
| Require a pull request before merging | On |
| Require approvals | 0 |
| Require conversation resolution before merging | On |
| Restrict who can push to matching branches | On, and add only `len-build-it` |
| Do not allow bypassing the above settings | On |
| Allow force pushes | Off |
| Allow deletions | Off |

What these do together:

- "Restrict who can push" decides who may press the merge button.
  With only `len-build-it` on the list, Len is the only person who can merge into `staging` or `master`.
- Len's merge is the approval.
  That is why "Require approvals" is 0: no teammate's approval is needed or counted.
- "Require a pull request" with "Do not allow bypassing" means even Len cannot push straight to either branch (R3).
  His own changes go through a pull request that he opens, writes, verifies, and merges himself.
- `.github/CODEOWNERS` names `len-build-it` for every file, so GitHub asks for his review on every pull request automatically.

**Roles - or the rules can be switched off**

Anyone with the Admin role on the repository, and any owner of the organization, can edit or delete these rules.
Under **Settings > Collaborators and teams**, give every teammate the **Write** role, not Admin or Maintain.
Under the organization's **People** page, check who is an Owner.

**Check that it works**

Ask a teammate to try `git push origin master` with a harmless commit, and to open a pull request into `staging`.
The push must be rejected, and the merge button must be unavailable to them.

## 10. Roles

| Role | Who | Does |
|---|---|---|
| Author | Any team member, with or without an AI agent | Makes the change, can explain it (Section 4A), runs Section 5A, opens the pull request into `staging` and writes its description personally (R11) |
| Reviewer | Len, for every pull request, including his own | Reads the description before the code, and rejects a pull request whose description is not in the author's own words or that the author cannot explain (R9, R11) |
| Area owner | Per the ownership table in `AGENTS.md` | Answers questions about their area; does not approve or merge |
| Tester | A person who is not the author | Runs Section 5C on real devices and signs Section 5D |
| Release owner | Len, the only person who can merge to `staging` or `master` | Merges every pull request, and runs Section 5E after a release |

**Len's own pull requests.**
Len verifies them himself, together with an AI agent that checks his work with him.
The agent runs the understanding check on him (R9), compares what he wrote in the pull request with the diff, and tells him where the two do not match.
It does not write the pull request for him (R11) and it does not merge.
His pull requests follow every other rule too: the same nine-part format, and the physical test by someone who is not him (R6).
When Len is away, nothing is merged.

AI agents may write code and push it to your own branch.
They never open a pull request and never write, draft, or polish a pull request title or description (R11).
They never merge into `staging` or `master`, never push to either, and never tick a physical-test box.
Before an agent pushes a change for review, it runs the understanding check with the person it is working for (Section 4A).

## 11. What this replaces

This decision ends the "push verified work straight to `master`" practice used since 2026-09-25.
The "Target branch" lines in plans `65`, `66`, `69` and `70` that allowed it are amended to point here.
Completed plans `71` and `72` keep their text as a historical record.
Agent briefs that say "merge to `master` after the gates pass" now mean "open a pull request into `staging`".

## 12. Common questions

**It is a one-line fix. Can I push it straight to `master`?**
No (R3).
A one-line change takes minutes to test, and one-line changes break things too.

**It is urgent.**
Follow Section 7.
One person takes it, and it still goes through `staging` and the physical test.

**I started a fix and then found someone else's pull request for the same thing.**
Stop and tell them (R1).
Offer what you found as a comment or a review on their pull request.
Len decides if the two should be combined.

**Nobody has a phone or the boards today.**
Then the release waits (R8).
The change can sit safely on `staging` until someone can test it.

**I only changed documentation.**
It still goes through a pull request into `staging`, but the physical tests do not apply.
Tick "docs only" in the pull request template.

**An AI agent wrote the change and all its tests pass.**
You are still responsible for it (R9).
The agent asks you the understanding-check questions before it goes for review, you write the pull request yourself (R11), a person still tests on real devices (R5), and a person merges.

**The AI's questions are too hard, or I got one wrong.**
That is the check working.
Ask the agent to explain, read the code again, and answer the next question.
Nothing is sent until you can explain it.

**Can the AI at least draft the pull request, and I edit it?**
No (R11).
Editing an explanation that something else wrote is not the same as explaining.
Short, plain, even clumsy sentences that are yours are better than a polished text that is not.

**My English is not good.**
Write in Tagalog, English, or a mix.
The guide in `76` lists the allowed and not-allowed uses of AI.

**Writing the pull request takes too long.**
That is accepted.
If a part is hard to write, that is the part you do not understand yet, and now you know where to look.

**Who reviews my pull request?**
Len reviews every one, and only Len can merge it.
He knows how each of us writes, and he rejects a description that is not in the author's own words.

**Who can merge to `staging` or `master`?**
Only Len, and GitHub enforces it (Section 9A).

**Who reviews Len's pull requests?**
Len verifies his own, with an AI agent that questions him on the change and checks his description against the diff.
They are public like everyone else's, in the same format, so anyone can read them and ask him to explain.

**The checklist is missing something that would have caught a bug.**
Add the line in a pull request to this document.
That is how the checklist stays honest.

## 13. Read and agreed

Add the first date once you have read Sections 1, 2, 4, 4A, 4B, 5 and 7 and the pull request guide in `76`.
Add the second once you have done the system walkthrough (Section 4B), with the name of the teammate who listened.

| Name | Rules read | System walkthrough done | Listener |
|---|---|---|---|
| Lenard | | | |
| Arnold | | | |
| Daniel | | | |
| Jade | | | |
| Doreen Kay | | | |
