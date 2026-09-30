# Evidence: 2026-09-30 Reconciliation

## Red run

- **Timestamp**: 2026-10-01T00:06:00+08:00
- **Commit**: `88cc665667ddc2897806c425a11dc42f9046d1c0`

### Backend ruff

```powershell
$env:AQONE_PROBE_PG_ADMIN_URL = 'postgresql://postgres@localhost:55432/postgres'; python -m ruff check .
```

```
All checks passed!
```

### Backend pytest

```powershell
$env:AQONE_PROBE_PG_ADMIN_URL = 'postgresql://postgres@localhost:55432/postgres'; python -m pytest -q -p no:cacheprovider
```

```
10 failed, 661 passed, 5 skipped, 1 xfailed in 159.96s (0:02:39)
```

### Web tests

```powershell
node --test test/*.test.js
```

```
ℹ tests 216
ℹ suites 0
ℹ pass 213
ℹ fail 3
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 1169.4543
```

### Mobile l10n and analyze

```powershell
flutter gen-l10n
```

```
Because l10n.yaml exists, the options defined there will be used instead.
To use the command line arguments, delete the l10n.yaml file in the Flutter project.
```

```powershell
flutter analyze
```

```
51 issues found. (ran in 174.1s)
```

### Mobile tests

```powershell
flutter test
```

```
00:35 +397 -7: Some tests failed.
```

## T1 - restore the 409 rule

- **Timestamp**: 2026-10-01T00:07:00+08:00
- **Commit**: `4a4bf8e72fb0800c0aaf3e1a8b9f4b865ef0f2b8`

### Test execution

```powershell
$env:AQONE_PROBE_PG_ADMIN_URL = 'postgresql://postgres@localhost:55432/postgres'; python -m pytest tests/test_vessel_profile.py tests/test_vessel_profile_pg.py -q -p no:cacheprovider
```

```
11 passed in 4.56s
```

```powershell
python -m ruff check .
```

```
All checks passed!
```

## T2 - broadcast backend (docs/73 Section 14.1)

- **Timestamp**: 2026-10-01T00:16:30+08:00
- **Commit**: `30c541e0b823af4bb640e6bb731dc8bbed67ffeb`

### Test execution

```powershell
$env:AQONE_PROBE_PG_ADMIN_URL = 'postgresql://postgres@localhost:55432/postgres'; python -m pytest tests/test_sos_broadcast_pg.py tests/test_sos_broadcast.py -q -p no:cacheprovider
```

```
14 passed in 12.52s
```

```powershell
$env:AQONE_PROBE_PG_ADMIN_URL = 'postgresql://postgres@localhost:55432/postgres'; python -m pytest -q -p no:cacheprovider
```

```
671 passed, 5 skipped, 1 xfailed in 158.77s (0:02:38)
```

```powershell
python -m ruff check .
```

```
All checks passed!
```

## T3 - dashboard (docs/73 Section 14.2)

- **Timestamp**: 2026-10-01T00:19:30+08:00
- **Commit**: `bb107960189ece255345a830602b8c1962e1017b`

### Test execution

```powershell
node --test test/*.test.js
```

```
ℹ tests 216
ℹ suites 0
ℹ pass 216
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 1154.5741
```

```powershell
Get-ChildItem js, test -Recurse -Filter *.js | ForEach-Object { node --check $_.FullName }
```

```
```

## T4 - SOS back on Home (spec 64 D10)

- **Timestamp**: 2026-10-01T00:20:15+08:00
- **Commit**: `bb59c05cc83a0c9b525fd3ffbfa91b0afb94543c`

### Test execution

```powershell
flutter test test/home_sos_restore_test.dart test/widget_test.dart
```

```
00:02 +25: All tests passed!
```

## T5 - refused profile edits

- **Timestamp**: 2026-10-01T00:30:25+08:00
- **Commit**: `cfd8d0b263b655da037130836940026e63a1548e`

### Test execution

```powershell
flutter test test/profile_push_result_test.dart test/profile_pairing_prompt_test.dart
```

```
00:01 +6: All tests passed!
```

## T6 - wording (docs/73 G9)

- **Timestamp**: 2026-10-01T00:33:51+08:00
- **Commit**: `11b19a468d6c703b0c511fbbaef69a7c3cecb3f9`

### Test execution

```powershell
flutter test test/nearby_sos_test.dart
```

```
00:00 +4: All tests passed!
```

## T7 - seen store, watcher and banner (docs/73 G2, G3)

- **Timestamp**: 2026-10-01T00:50:31+08:00
- **Commit**: `3f8015949d0ca30e16eb7ea0a66d0c644cf6dc29`

### Test execution

```powershell
flutter test test/seen_broadcast_store_test.dart test/nearby_sos_watcher_test.dart test/nearby_help_banner_test.dart
```

```
00:02 +13: All tests passed!
```

## T8 - notification tap (docs/73 G10)

- **Timestamp**: 2026-10-01T00:57:21+08:00
- **Commit**: `e79642e8f67143e696d6d88f0c479820f7db64db`

### Test execution

```powershell
flutter test test/eta_notifier_payload_test.dart
```

```
00:00 +2: All tests passed!
```

G10 device check: NOT VERIFIED - no device

## Final gate

- **Timestamp**: 2026-10-01T01:05:00+08:00
- **Commit**: `d9438577cbc3a68c5a460b0a018a3e13bbb0c051`

### Backend ruff

```powershell
python -m ruff check .
```

```
All checks passed!
```

### Backend pytest

```powershell
$env:AQONE_PROBE_PG_ADMIN_URL = 'postgresql://postgres@localhost:55432/postgres'; python -m pytest -q -p no:cacheprovider
```

```
671 passed, 5 skipped, 1 xfailed in 164.07s (0:02:44)
```

### Web tests

```powershell
node --test test/*.test.js
```

```
ℹ tests 216
ℹ suites 0
ℹ pass 216
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 1211.3599
```

### Web JS syntax check

```powershell
Get-ChildItem js, test -Recurse -Filter *.js | ForEach-Object { node --check $_.FullName }
```

```
All files passed syntax check.
```

### Mobile analyze

```powershell
flutter analyze
```

```
No issues found! (ran in 21.7s)
```

### Mobile tests

```powershell
flutter test
```

```
00:29 +425: All tests passed!
```

### Diff stat from abc9093

```powershell
git diff --stat abc9093 HEAD
```

```
 38 files changed, 3201 insertions(+), 1105 deletions(-)
```

### Working tree status

```powershell
git status --short
```

```
<clean>
```

## Not verified

- G10 device check: NOT VERIFIED - no device
- Nearby broadcast on physical hardware / phones (Plan 74 Phase 4)
