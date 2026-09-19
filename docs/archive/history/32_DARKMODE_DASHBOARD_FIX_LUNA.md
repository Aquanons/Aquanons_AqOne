# 32 — Dark Mode Dashboard Fix (for Luna)

**Status:** COMPLETE
**Owner:** GPT Luna / Jade
**Created:** 2026-08-23
**Updated:** 2026-09-19
**Related:** [`docs/47_VISUAL_DESIGN_GUIDE.md`](../47_VISUAL_DESIGN_GUIDE.md)

> **Historical document:** Implementation plan executed for dark mode dashboard fixes on 2026-08-23.
> Current visual and theme specifications are maintained in [`docs/47_VISUAL_DESIGN_GUIDE.md`](../47_VISUAL_DESIGN_GUIDE.md).

**Audience: GPT Luna, executing on a dedicated branch. Do not work on `master`
or on the `demo` branch.**

---

## 0. DIRECTIVE — READ BEFORE ANYTHING ELSE

**Follow this plan exactly. Do not deviate, improvise, redesign, or "improve"
it.** This is not a starting point for your own investigation — the
investigation is already done. Every file, line number, selector and storage
key below was verified by reading the actual code in this repository on
2026-08-23.

- **Do not invent your own root cause.** Three bugs are named below, with
  exact file/line evidence. Fix those three. Do not go looking for a fourth
  unless instructed in §4.
- **Do not touch any file not named in §1–§3.** Not `profile2.css`, not
  `dashboard-core.js`, not anything under `mobile/` or `backend/`.
- **Do not change light-mode appearance.** Every fix here is additive
  (new `[data-theme="dark"]` rules, new lines) — existing light-mode
  selectors and their values must be byte-for-byte unchanged unless a step
  explicitly says to edit an existing line.
- **Do not rename, move, or reformat existing code.** No drive-by cleanup,
  no reordering CSS blocks, no "while I'm here" edits.
- **Do not add features.** No new toggle, no settings panel, no `prefers-color-scheme`
  auto-detection. This plan makes the existing dark-mode toggle work
  correctly everywhere it already exists. Nothing more.
- **Commit after every individual step, not at the end.** See §5. This is
  non-negotiable — it's how Lenard reverts a single bad step without losing
  the rest of your work.

**If something in this plan contradicts what you find in the code, or a line
number is off because the file changed since 2026-08-23: STOP and report it
to Lenard before proceeding.** Do not silently "fix it your way" instead —
re-read the actual current line, confirm the fix still makes sense, and only
then proceed with the same intent described here.

---

## 1. Bug 1 — Dark mode doesn't reach several dashboard elements

**File:** `web/css/dashboard.css`

**Root cause:** The block of rules commented `/* Dashboard layout refresh:
toolbox and inline tool panel */` (starts around line 4905) hardcodes light
hex colors for header controls and the tool panel, instead of using the
`var(--surface)` / `var(--bg)` tokens the rest of the file uses. Because this
block appears *after* the original theme-aware rules, it wins the cascade at
equal specificity, and none of it has a `[data-theme="dark"]` counterpart —
so these elements never change when dark mode is toggled.

Confirmed offending declarations (line numbers are pre-edit, from the
2026-08-23 read of the file — re-verify before editing if the file has since
changed):

| Line | Selector | Hardcoded value |
|---|---|---|
| 4642 | `.app-header .layer-switcher` | `background: #f7f9fb;` |
| 4656 | `.app-header .layer-btn:hover` | `background: #edf3f8;` |
| 4665 | `.search-input` | `background: #f7f9fb;` |
| 4674 | `.lang-toggle-container` | `background: #f7f9fb;` |
| 4688 | `.sync-status` | `background: #fdeced;` |
| 4698 | `.icon-btn-top` | `background: #f7f9fb;` |
| 4701 | `.icon-btn-top:hover` | `background: #edf3f8;` |
| 4706 | `.user-pill` | `background: #f7f9fb;` |
| 4715 | `.demo-data-banner` | `background: #f7f9fb;` |
| 4965 | `.rail-btn:hover` | `background: #f7f9fb;` |
| 4969 | `.rail-btn.pin-mode-active` | `background: #fff5ea;` |
| 4974 | `.tool-panel-body` | `background: #fbfcfd;` |
| 4984 | `.tab-badge.badge-red` | `background: #fdeced;` |
| 4985 | `.tab-badge.badge-orange` | `background: #fff5e5;` |

Plus the status-pill backgrounds around lines 4806–5039 (`#fff8e8`,
`#fdeced` reused twice more, `#f8fafc` twice, `#f7f9fb` twice) — read that
range yourself and list every hardcoded background in it before you start;
the table above is not exhaustive of that range on purpose, so you actually
read the code instead of trusting a table blindly.

**Fix — additive only, do not edit the rules above in place:**

Add one new `[data-theme="dark"]` block at the **end of the file** (after
the last existing rule) that overrides each selector above for dark mode.
Use the existing dark tokens already defined at the top of the file
(`--surface`, `--surface-2`, `--border`, `--text-secondary`) rather than
inventing new hex values, e.g.:

```css
[data-theme="dark"] .app-header .layer-switcher,
[data-theme="dark"] .search-input,
[data-theme="dark"] .lang-toggle-container,
[data-theme="dark"] .icon-btn-top,
[data-theme="dark"] .user-pill,
[data-theme="dark"] .demo-data-banner,
[data-theme="dark"] .rail-btn:hover,
[data-theme="dark"] .tool-panel-body {
  background: var(--surface-2);
}

[data-theme="dark"] .app-header .layer-btn:hover,
[data-theme="dark"] .icon-btn-top:hover {
  background: var(--border);
}
```

Then handle the status-tinted ones (`.sync-status`, `.rail-btn.pin-mode-active`,
`.tab-badge.badge-red`, `.tab-badge.badge-orange`, and the rest you found in
the 4806–5039 range) **separately, keeping their color meaning** (red stays a
red tint, orange stays an orange tint) but at a darkened value that has
enough contrast against `var(--surface)`. Do not make them gray — a red
status badge that turns gray in dark mode is a regression, not a fix. Use
low-opacity `rgba()` versions of `--danger` / `--warning` for these
(e.g. `rgba(239,68,68,0.18)` for a dark-mode red tint) rather than picking
new arbitrary hex values.

**Verify:** open the dashboard, toggle dark mode with the header sun/moon
button, and visually confirm every element in the table above changes
color along with the header. Open the "Operational Layers" tool panel
specifically — it's the one Lenard screenshotted — and confirm its
background and text are both legible in dark mode.

---

## 2. Bug 2 — Toggling dark mode on the dashboard doesn't carry over to the profile page

**Files:** `web/js/dashboard/dashboard-profile-pill.js` (edit),
`web/js/profile.js` (read only, do not edit — see why below)

**Root cause:** Two independent theme implementations, two different
localStorage keys, syncing only one direction:

- `dashboard-profile-pill.js` (lines 66–117) writes the dashboard's own
  toggle state to key `aqone-theme`, and only *falls back* to reading
  `aqone_dark_mode` once, at page load, if `aqone-theme` was never set.
  It never *writes* `aqone_dark_mode`.
- `profile.js` (`initDarkMode()`, around line 280–304, running on
  `Systemprofile.html`) only ever reads and writes `aqone_dark_mode`. It has
  no knowledge of `aqone-theme` at all.

So: toggle dark mode from the dashboard header → `aqone-theme` gets set,
`aqone_dark_mode` does not → click the profile pill → `Systemprofile.html`
loads, `profile.js` checks only `aqone_dark_mode`, finds it unset, renders
light. The setting is lost every time you navigate to the profile page from
the dashboard.

**Fix — edit only `dashboard-profile-pill.js`, do not touch `profile.js`:**

In the theme-toggle IIFE (lines 66–117), every place that currently does
`localStorage.setItem(STORAGE_KEY, next);` must **also** write the profile
page's key in the format `profile.js` expects (the string `'true'` or
`'false'`, not `'dark'`/`'light'`). There are two call sites: the
`themeBtn` click handler (~line 101–106) and the `prefDarkToggle` change
handler (~line 109–116). Add this line right after each existing
`localStorage.setItem(STORAGE_KEY, next);`:

```js
localStorage.setItem(PROFILE_KEY, next === 'dark' ? 'true' : 'false');
```

`PROFILE_KEY` is already declared at the top of this IIFE (line 68) — you
are not introducing a new variable, just using the one already there.

Do not edit `profile.js` to make it read `aqone-theme` instead. Keep the
direction of the fix as "the dashboard writes both keys" — that's the
smaller, single-file change and it's the one specified here. If you think
`profile.js` also needs a change, stop and say so; do not make that call
yourself.

**Verify:** on the dashboard, toggle dark mode on. Click the profile pill to
navigate to `Systemprofile.html`. Confirm it loads already in dark mode.
Toggle it off there, navigate back to the dashboard, confirm it's light
again.

---

## 3. Bug 3 — Logging out sends you back to the dashboard, not to the login page

**File:** `web/js/profile.js`, function `initHeaderAndActions()`,
around lines 465–474.

**Current code (verified 2026-08-23):**

```js
if (logoutBtn) {
    logoutBtn.addEventListener('click', () => {
        if (confirm('Are you sure you want to log out?')) {
            showToast('Logging out...', 'info');
            setTimeout(() => {
                window.location.href = 'dashboard.html';
            }, 1000);
        }
    });
}
```

**Root cause, two parts:**

1. It redirects to `dashboard.html` — the page the user is trying to leave.
2. It never clears the session. `dashboard-core.js` stores the auth token
   under `sessionStorage` keys `aqoneToken` and `aqoneUser` (see its own
   `clearSession()` at lines 86–89, `TOKEN_KEY`/`USER_KEY` at 78–79). This
   handler never removes them, so even a correct redirect would leave the
   dashboard's auth guard (`dashboard-core.js` line 117, `if (!getToken())`)
   perfectly happy to let the user straight back in.

**Fix — decision made, implement exactly this:** redirect to `login.html`
(not `index.html`). Reason: `login.html` is the page `dashboard-core.js`
itself already uses as `LOGIN_URL` (line 80) for every other place the app
needs to bounce an unauthenticated user, and `Systemprofile.html` sits in
the same `web/html/` directory as `login.html`, so the relative path
resolves correctly with no `../`. Using `index.html` would be inconsistent
with that existing convention. This is Lenard's call — do not second-guess
it or substitute `index.html`.

Replace the handler body with:

```js
if (logoutBtn) {
    logoutBtn.addEventListener('click', () => {
        if (confirm('Are you sure you want to log out?')) {
            showToast('Logging out...', 'info');
            sessionStorage.removeItem('aqoneToken');
            sessionStorage.removeItem('aqoneUser');
            sessionStorage.removeItem('aqoneDemoBypassActive');
            setTimeout(() => {
                window.location.href = 'login.html';
            }, 1000);
        }
    });
}
```

Do not import or call `clearSession()` from `dashboard-core.js` — it's
declared inside that file's own IIFE and is not accessible from
`profile.js`. The three `removeItem` calls above are the correct, minimal,
self-contained equivalent for this file. Do not touch
`aqoneDemoBypassActive` handling anywhere else.

**Verify:** log in (or use the offline demo bypass), open dev tools →
Application → Session Storage, confirm `aqoneToken` exists. Navigate to the
profile page, click Log Out, confirm the browser lands on `login.html` and
that `aqoneToken` / `aqoneUser` / `aqoneDemoBypassActive` are gone from
session storage. Then try navigating back to `dashboard.html` directly by
URL — confirm it bounces you to `login.html` instead of loading.

---

## 4. Optional cleanup — only after §1–§3 are done and verified

**File:** `web/js/dashboard/dashboard-profile-pill.js`, lines 319–408.

There is a block here — profile-tab handlers, a second logout handler
pointing at `login.html`, save/cancel handlers — preceded by an existing
comment: `// TODO(luna): no matching DOM elements found in dashboard.html —
appears unreachable, confirm with Lenard`. Confirmed: it is dead code. None
of `.profile-tab`, `#btn-logout`, `#pf-fullname`, etc. exist in
`dashboard.html`, so every `document.getElementById`/`querySelectorAll` in
this block returns null or empty and the block does nothing on the page it
runs on.

Delete lines 319–408 (the whole IIFE at "PROFILE PAGE: TABS, SAVE HANDLERS,
LOGOUT" through its closing `})();`) and the `TODO(luna)` comment above it.
Do this as its **own commit**, separate from §1–§3, so it can be reverted on
its own if it turns out something outside this repo depends on it.

Do not go looking for other dead code elsewhere. This one block only.

---

## 5. Git workflow — commit every step separately

Branch from current `master`, today, by yourself:

```
git checkout master
git pull
git checkout -b luna-darkmode-fix
```

Never commit directly to `master` or to `demo`. One commit per fix, in this
exact order, each only after you've verified that specific fix per its
"Verify" instructions above:

1. `fix(dashboard): add dark-mode overrides for hardcoded header/panel colors`
   — only `web/css/dashboard.css` changes.
2. `fix(theme): sync dark-mode setting from dashboard to profile page`
   — only `web/js/dashboard/dashboard-profile-pill.js` changes.
3. `fix(profile): logout clears session and returns to login page`
   — only `web/js/profile.js` changes.
4. `chore(dashboard): remove unreachable profile-tab code flagged by TODO(luna)`
   — only if you did §4, only `web/js/dashboard/dashboard-profile-pill.js`
   changes.

Do not squash these into one commit. Do not combine two fixes into one
commit because "they're related." The whole point is that Lenard can
`git revert` any single one of these without touching the others if
something breaks.

Push the branch after each commit:

```
git push -u origin luna-darkmode-fix
```

(first push needs `-u`; after that, plain `git push` is enough.)

When all four commits are in and verified, stop. Do not open a PR or merge
to `master` yourself — tell Lenard the branch is ready for review.

---

## 6. If you get stuck

Stop and report to Lenard. Do not:

- guess at a line number that doesn't match what you see and edit the
  nearest-looking thing instead,
- decide the plan is wrong and do something else,
- fix something not listed here because you noticed it along the way,
- combine or reorder the commits in §5 for convenience.

A wrong assumption caught now costs one message. Discovered later, in a
tangle of unrelated changes, it costs an afternoon of untangling — and
defeats the entire reason this plan asks for one commit per step.
