# mobile — AqOne fisherman app

Flutter app that hands an SOS to a nearby buoy over WiFi while the phone has no
cellular signal.

Contracts this app implements:

| Concern | Doc |
|---|---|
| Phone → buoy HTTP | `docs/03_PHONE_BUOY_WIFI.md` |
| Delivery states | `docs/06_DELIVERY_STATES.md` |
| Backend reconciliation | `docs/05_PUBLIC_API.md` |
| Visual system | `docs/47_VISUAL_DESIGN_GUIDE.md` |
| What is not built | `docs/07_SCOPE_OUT.md` |

`docs/guides/05_FLUTTER.md` describes a superseded design in which the phone
built and signed binary LoRa frames. Do not follow it — see
`docs/guides/README.md`.

## Setup

The platform folders are not committed. Generate them once, then fetch
packages:

```bash
cd mobile
flutter create --platforms=android --project-name aqone --org ph.aqone .
flutter pub get
```

`flutter create` may overwrite `lib/main.dart`. If it does:

```bash
git checkout -- lib/main.dart
```

## Run

```bash
# against a real buoy on its SoftAP
flutter run

# against a laptop mock of the buoy
flutter run --dart-define=BUOY_BASE_URL=http://192.168.1.50:8080

# build debug APK (for teammates without the release signing key)
flutter build apk --debug

# release build for the demo (requires android/key.properties; see Release signing below)
flutter build apk --release

# pitch build (Phase 1 manual SOS focus)
flutter build apk --release --dart-define=PITCH_MODE=true
```

## Release signing

Release builds (`flutter build apk --release`) require `android/key.properties` holding the release keystore path and passwords.
If `key.properties` is absent or incomplete, the release build fails immediately with an error.

Teammates without the release key must use the debug build:

```bash
flutter build apk --debug
```

Never commit `key.properties` or keystore (`.jks`) files to the repository.
See `android/key.properties.example` for keystore creation instructions.

Overridable at build time:

| Define | Default |
|---|---|
| `BUOY_BASE_URL` | `http://192.168.4.1` |
| `BACKEND_BASE_URL` | `https://aqone-backend.onrender.com` |

## Languages

The app ships English, Tagalog and Aklanon. Translations live in
`lib/l10n/*.arb`; `flutter pub get` regenerates the `AppLocalizations` class
from them (driven by `l10n.yaml`, `generate: true` in `pubspec.yaml`). There
is no separate codegen command to remember.

The language follows the device by default and can be overridden in
onboarding or on the Profile page; the choice is persisted in
`shared_preferences` by `lib/core/locale_controller.dart`.

Adding a string:

1. Add the key and an `@key` description to `lib/l10n/app_en.arb`.
2. Add the same key to `app_fil.arb` and `app_akl.arb`, or leave it out — a
   missing key falls back to English and is listed in the generated
   `lib/l10n/untranslated.json`.
3. Read it with `AppLocalizations.of(context).yourKey`.

Two constraints worth knowing before you touch this:

- The Tagalog locale code is **`fil`, not `tl`** — `flutter_localizations`
  only ships Material localizations for `fil`, and an unsupported locale in
  `supportedLocales` throws at runtime.
- Aklanon (`akl`) has no Flutter localizations at all. The fallback delegates
  in `lib/core/l10n_fallback.dart` cover it and **must stay last** in
  `localizationsDelegates`.

Full plan, phase order and the string inventory:
`docs/22_LOCALIZATION_PLAN.md`. Translation review rules:
`lib/l10n/README.md`. **The Tagalog and Aklanon files are unreviewed
drafts.**

## Verify

```bash
flutter analyze
flutter test
```

`test/localization_test.dart` covers locale resolution and — the one that
matters — that Aklanon renders Material widgets without throwing. Run it
before any demo.

## Android configuration

`flutter create` does not add these. Apply them after generating the platform
folders.

`android/app/src/main/AndroidManifest.xml`, inside `<manifest>`:

```xml
<uses-permission android:name="android.permission.INTERNET"/>
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION"/>
<uses-permission android:name="android.permission.ACCESS_WIFI_STATE"/>
<uses-permission android:name="android.permission.CHANGE_WIFI_STATE"/>
```

On the `<application>` tag:

```xml
android:networkSecurityConfig="@xml/network_security_config"
```

`android/app/src/main/res/xml/network_security_config.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
  <domain-config cleartextTrafficPermitted="true">
    <domain includeSubdomains="false">192.168.4.1</domain>
  </domain-config>
</network-security-config>
```

The cleartext exception is scoped to the buoy address only. The buoy hop is
plain HTTP by design (`docs/03_PHONE_BUOY_WIFI.md`); the backend hop stays
HTTPS.

## How it behaves

1. First launch asks for a boat name. A 32-character device-local `vessel_id`
   is generated and stored. There is no account and no password
   (`docs/07_SCOPE_OUT.md`).
2. Pressing SOS takes a GPS fix if one is available, writes the message to a
   SQLite outbox as `saved`, then tries to hand it to the buoy.
3. A `200` with `accepted: true` moves it to `relayed` and records
   `buoy_id`, `src_id` and `seq` from the ack.
4. A retry worker re-attempts anything still `saved` every 20 seconds.
5. When the phone has internet, a reconcile pass reads
   `GET /api/v1/vessels/{vessel_id}/sos` and matches rows by `seq` to advance
   to `delivered` or `acknowledged`.

State only ever moves forward. The app never displays a state it has not
observed — an SOS sitting at `relayed` in a dead zone is shown as exactly that.

## Known contract gap

`docs/03` defines the phone's `vessel_id` as a device-local id of up to 32
characters. `docs/05` describes the backend path parameter as a UUID. This app
generates a 32-character hex string, which fits both descriptions but is not
dash-formatted.

Reconciliation therefore depends on the backend accepting that id, or on the
gateway mapping it. Until that is confirmed with the backend and gateway
owners, reconciliation fails closed: a non-200 or unmatched row leaves the
local state untouched rather than guessing. `saved` and `relayed` are observed
locally and are unaffected.
