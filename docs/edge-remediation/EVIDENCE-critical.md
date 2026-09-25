# Evidence: Critical edge cases (plan 66)

Plan: `docs/66_CRITICAL_EDGE_CASES_IMPLEMENTATION_PLAN.md`.
Each phase appends a dated section.
Row counts, IDs and log excerpts only; never keys, phone numbers or URLs with credentials.

## Phase 1 - D2 toolchain (2026-09-25)

Installed by Gemini; Gemini left no evidence or handoff update, so Claude re-ran every check below.

| Tool | Version | Location |
| --- | --- | --- |
| PlatformIO Core | 6.2.0 | `C:\Users\User\AppData\Local\Programs\Python\Python311\Scripts\pio.exe` (pip, Python 3.11.9) |
| Host `g++` | 16.1.0 (WinLibs POSIX UCRT r4, winget `BrechtSanders.WinLibs.POSIX.UCRT`) | `%LOCALAPPDATA%\Microsoft\WinGet\Packages\BrechtSanders.WinLibs.POSIX.UCRT_Microsoft.Winget.Source_8wekyb3d8bbwe\mingw64\bin`, on the User PATH |

Firmware build, `pio run -d firmware` with scratch `AqOneSecrets.h` in both sketch folders (random `LOAM_KEY`, never printed), deleted afterwards:

| Environment | Result | Warnings |
| --- | --- | --- |
| buoy | SUCCESS (37.6 s) | 0 |
| shore | SUCCESS (16.1 s) | 0 |

Both sketch sources recompiled (`AqOneBuoy.ino.cpp.o`, `AqOneShore.ino.cpp.o`); the ESP32 framework and libraries came from the PlatformIO cache.
After deleting the scratch files, no `AqOneSecrets.h` remains under `firmware/` and `git status --short` shows no firmware changes.

Host compile: `g++ -std=c++17 -Wall -Wextra -Werror` on `int main(){return 0;}` compiled with exit 0 and ran with exit 0.

Limit: shells opened before the install do not see `g++` until they are restarted.
