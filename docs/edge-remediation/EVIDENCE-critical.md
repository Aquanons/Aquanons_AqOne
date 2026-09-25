# Evidence: Critical edge cases (plan 66)

Plan: `docs/66_CRITICAL_EDGE_CASES_IMPLEMENTATION_PLAN.md`.
Each phase appends a dated section.
Record row counts, IDs and log excerpts only; never keys, phone numbers or URLs with credentials.

## Phase 1 - D2 toolchain (2026-09-25)

Installed PlatformIO Core with `python -m pip install -U platformio`.
Installed WinLibs POSIX UCRT with WinGet package `BrechtSanders.WinLibs.POSIX.UCRT`.

| Tool | Version | Location |
| --- | --- | --- |
| PlatformIO Core | 6.2.0 | `C:\Users\User\AppData\Local\Programs\Python\Python311\Scripts\pio.exe` |
| Host `g++` | 16.1.0 (WinLibs POSIX UCRT 16.1.0-14.0.0-r4) | `C:\Users\User\AppData\Local\Microsoft\WinGet\Packages\BrechtSanders.WinLibs.POSIX.UCRT_Microsoft.Winget.Source_8wekyb3d8bbwe\mingw64\bin\g++.exe` |

In a new PowerShell process with the updated user PATH, `pio --version` and `g++ --version` both succeeded.

Firmware build: `pio run -d firmware` exited 0.

| Environment | Result | Warnings |
| --- | --- | --- |
| buoy | SUCCESS (12.80 s) | 0 |
| shore | SUCCESS (13.94 s) | 0 |

The build used temporary random scratch `AqOneSecrets.h` files in both sketch folders.
Both files were removed after the build.
No `AqOneSecrets.h` remains under `firmware/`, and `git status --short` shows no firmware changes.

Host compile: `g++ -std=c++17 -Wall -Wextra -Werror` on `int main(){return 0;}` compiled with exit 0 and ran with exit 0.
The temporary source and executable were removed.

Limit: shells opened before the install do not see `g++` until they are restarted.
No secret values were recorded.
Claude re-ran the firmware build and the host compile independently the same day with the same results (buoy 37.6 s, shore 16.1 s, 0 warnings).
