# Translations — read before editing

Full plan: `docs/22_LOCALIZATION_PLAN.md`.

## The translations in here are DRAFTS

`app_fil.arb` and `app_akl.arb` were machine-drafted. **No native speaker
has reviewed them yet.** The Aklanon file in particular is a starting
point for someone from Aklan to correct, not a finished translation —
expect the `ea`/`eu` spellings and the imperative phrasing to need work.

Strings tagged `SAFETY CRITICAL` in `app_en.arb` need **two** reviewers.
Understating "Not Advised to Go Out" in translation is a real hazard, not
a typo.

## Rules

- `app_en.arb` is the template and the only file that carries `@key`
  description blocks. Add new keys there first, with a description that
  explains the screen context — a translator seeing bare `"Saved"` will
  guess wrong.
- Never translate `MDRRMO`, `AqOne`, `LoRa`, `GPS`, `SOS`, or `buoy` ids.
- Prefer the word a fisherman actually says over the dictionary-correct
  one.
- A key missing from `app_fil.arb` / `app_akl.arb` falls back to English
  automatically and is listed in `untranslated.json`. Leaving a key out is
  better than guessing at it.

## Locale codes

`en`, `fil` (**not** `tl` — flutter_localizations ships `fil`), `akl`.
Aklanon has no Material localizations; `lib/core/l10n_fallback.dart`
handles that by loading Tagalog chrome. See §2 and §4.2 of the plan doc.

**Aklanon is the default.** A fresh install runs in `akl` whatever the
phone is set to (`kDefaultLocale`); only the in-app picker changes it.
`app_en.arb` is the template, not the default language.

The compass letters stay N/E/S/W in every language (Len, plan 70 D5).

## Regenerating

```
cd mobile
flutter pub get      # runs gen-l10n automatically (generate: true)
```

Generated output lands **in this folder** — `app_localizations.dart` plus one
file per locale, alongside the `.arb` sources. Import it as:

```dart
import 'package:aqone/l10n/app_localizations.dart';
```

Do not edit those files; they are overwritten on every `pub get`. They are
gitignored, so a fresh clone must run `flutter pub get` before it will
analyze or build.

**Not `package:flutter_gen/gen_l10n/...`.** That was the old synthetic
package, which recent Flutter versions no longer create. Importing it gives
you `Target of URI doesn't exist` on every file that touches a string, plus
a cascade of `Undefined class 'AppLocalizations'` — about sixty errors from
one wrong path. If you see that, the import is stale, not the generator.
