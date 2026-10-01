# 76 - How to write a pull request

**Status:** ACTIVE
**Owner:** Lenard
**Created:** 2026-10-01
**Updated:** 2026-10-01
**Related:** `docs/75_STAGING_AND_MERGE_RULES_DECISION.md` (rule R11), `.github/pull_request_template.md`

This guide is for everyone on the team, and most of us are beginners at this.
It shows the format every pull request follows and how to fill in each part.

## 1. The rule (R11)

**You write the pull request yourself, in your own words, in the format below.**
**An AI never writes it.**

- No AI writes, drafts, rewrites, or "polishes" the title or the description.
- An AI may have written the code.
  The description is yours.
- The goal is not speed.
  There are two goals: we do not break production, and every one of us has a high technical understanding of what AqOne is and how it works.

Why we do it this way: if you cannot describe your change in plain words, you do not understand it yet.
Writing the description is how you find that out before the reviewer does.
A description that an AI wrote tells the team what the AI thinks the code does; it tells nobody what you know.

## 2. What a pull request description is for

Three people read it.

- **The reviewer, today.**
  They need to know what to look at and what to worry about.
- **The tester, this week.**
  They need to know what to try on the real phone and boards.
- **You or a teammate, six months from now,** asking "why is this code like this?"
  The description is the answer.

Write for the third person.
They have none of the context you have right now.

## 3. The format

Every pull request has a title and these nine parts, in this order.
The template on GitHub gives you the headings.

| # | Part | The question it answers |
|---|---|---|
| - | Title | What is this, in one line? |
| 1 | Summary | What does this pull request do? |
| 2 | Why | What problem made this necessary? |
| 3 | What changed | Which files, and what changed in each? |
| 4 | How it works | How does the change do its job, and where does it sit in the system? |
| 5 | What could break | What depends on this code? |
| 6 | How I tested it | What did I run, what did I do by hand, and what did I not test? |
| 7 | How to undo it | If this is wrong, how do we take it back out? |
| 8 | Documents updated | Which docs changed with the code? |
| 9 | What I am unsure about | What should the reviewer look at hardest? |

At the bottom there is one line where you say honestly how AI was used on the code.

## 4. How to write each part

### Title

Format: `type(area): what changed`.

| Type | Use it for |
|---|---|
| `fix` | A bug fix |
| `feat` | A new feature |
| `docs` | Documentation only |
| `test` | Tests only |
| `refactor` | Changing how code is written without changing what it does |

Area is one of `backend`, `web`, `mobile`, `firmware`, `docs`.
Say what changed for the user or the system, not what you did.

| Not this | This |
|---|---|
| `fix bug` | `fix(mobile): logging out returns to the welcome screen` |
| `update main.dart` | `fix(mobile): logging out returns to the welcome screen` |
| `changes` | `feat(web): show the cancelled state on a nearby broadcast` |

### 1. Summary

Two or three sentences.
Someone who reads only this part should know what the pull request does.

### 2. Why

Describe the problem as a person would see it, then the cause if you know it.
Link the plan, spec, or bug report if there is one.

| Not this | This |
|---|---|
| "Logout was broken." | "After tapping Log out, the Profile screen stayed on top, so the fisher saw no change. After restarting the app it skipped the welcome screen, because remember-me was still on." |

### 3. What changed

One line per file: the file, then what changed in it.
If you cannot say what changed in a file, open it and read your diff again.

### 4. How it works

This is the most important part, and the hardest.
Explain the approach as if to a teammate who has not seen the code.

- What does the code do now, step by step?
- Where does it sit in the system: which step of the SOS path, which screen, which endpoint?
- Why this way, and what did you decide not to do?

If you find you are copying the code into sentences, step back and explain the idea.

### 5. What could break

Name what else uses the code you touched.
Say which shared contract it touches, if any: the LoRa frame, phone to pod, ingest, the public API, the delivery states, the database.
"Nothing" is almost never true; "I checked the callers of X and found A and B" is a real answer.

### 6. How I tested it

Three short lists.

- **Automated:** the command and the last line of its output.
- **By hand:** numbered steps, the device you used, and what you saw.
- **Not tested:** what you could not test, and why.

The third list matters most.
"Not tested on a real phone - I do not have one" is honest and useful.
Leaving it out is how untested code reached `master` before.

### 7. How to undo it

Usually: "Revert this pull request."
Say so if that is not enough, for example when a database migration ran or a board must be reflashed.

### 8. Documents updated

List the documents you changed in this same pull request.
If a contract document should have changed and did not, the pull request is not finished.

### 9. What I am unsure about

Say what you do not fully understand, or what you want the reviewer to check.
This is not a weakness.
It is the most useful thing you can tell a reviewer, and it is how we learn.

## 5. A worked example

This example was written to show the format, using the logout fix of 2026-10-01.
Read it for the shape, not as text to copy.

```markdown
fix(mobile): logging out returns to the welcome screen

## 1. Summary
Logging out from Profile now closes Profile and shows the welcome screen.
After a restart, the app asks the fisher to enter again.

## 2. Why
Two things were wrong.
After tapping Log out, the Profile screen stayed on top, so it looked like nothing happened.
After restarting the app, it skipped the welcome screen, because remember-me was still switched on.

## 3. What changed
- `mobile/lib/main.dart`: gave the app a navigator key, and changed `_logout`.

## 4. How it works
Profile is a screen pushed on top of the home screen.
Logging out used to change the app state underneath, but nothing removed the Profile screen on top.
Now `_logout` uses the navigator key to close every screen back to the first one.
It also turns remember-me off in storage and clears the entered state, so the next start shows the welcome screen.
The vessel identity is kept on purpose, and SOS delivery in the background keeps running, so a fisher who logs out by mistake can still be found.
I did not move Profile back into the bottom bar, because that would undo an earlier design decision.

## 5. What could break
Anything that opens a screen on top of home is closed on logout; I checked Profile and the SOS countdown.
It does not touch the SOS path or any shared contract.

## 6. How I tested it
Automated:
- `flutter test test/logout_flow_test.dart` -> `+3: All tests passed!`
- `flutter analyze` -> `No issues found!`
By hand:
- none yet
Not tested:
- On a real phone. I do not have one today. It needs: log out, see the welcome screen, close the app, open it, see the welcome screen again.

## 7. How to undo it
Revert this pull request. No database change.

## 8. Documents updated
- `docs/08_DEMO_AND_STATUS.md`: added the dated entry.

## 9. What I am unsure about
I am not sure what happens if the fisher logs out while an SOS is still being sent. Please look at that.

AI use: an AI agent wrote the code change and the tests. I wrote this description.
```

## 6. Using AI without breaking the rule

| Allowed | Not allowed |
|---|---|
| Asking an AI to explain the code until you understand it | Asking an AI to write or draft the description |
| Having the AI quiz you (the understanding check, R9) | Pasting your notes and asking it to "make it sound better" |
| Asking an AI "is anything in my description wrong compared to the code?" and then fixing it yourself | Letting it rewrite the wrong part for you |
| Checking spelling with your editor | Translating a description the AI wrote |

Plain, short, even clumsy sentences are fine.
English, Tagalog, or a mix is fine.
What matters is that the words are yours and they are true.

## 7. What the reviewer does

Len reviews every pull request.
He knows how each of us speaks and writes.
If a description does not sound like its author, he rejects it without further discussion, and the author writes it again.

- Reads the description before the code.
- Sends the pull request back if a part is missing, or if the description does not match the diff.
- May ask the author to explain any part out loud, without the screen.
- Sends it back if the author cannot explain it.

No tool can prove who wrote a description, so this rule runs on honesty, on Len knowing our voices, and on his questions.
Sending a pull request back is not a punishment.
It means the description is not finished yet.
