> **Decision 2026-09-30 (Len): fix rejected.** The diagnosis below stands, but the anonymous-overwrite 409 rule in [`05_PUBLIC_API.md`](../05_PUBLIC_API.md) stays the contract. Commit `e32c085`, which applied this fix, is to be reverted and the stale-profile bug fixed another way; see the [Current Register](../README.md#current-register).

# Profile Mismatch Fix (app vs dashboard)

## Symptom

The roster page showed `Jade Salvador / MADAGASCAR / BOATR 8763937 / +639950588356` while the phone's Profile screen showed `Jade N. Salvadorr / MADAS / CFVGL 73736383 / +639950588357` for the same `vessel_id 282a60ef...1310`.
The dashboard was stale, the app looked new, and neither side warned about the disagreement.

## Diagnosis

Two defects combine into one visible mismatch.
Server side: `POST /api/vessel-profile` returns 409 for any anonymous write that changes an existing non-blank field (`backend/app/api/vessel_profile.py:83-113`).
The user has no paired device, so every profile edit is anonymous, so every edit is rejected, so the server row keeps the very first values forever.
App side: `registerVesselProfile` swallows all errors silently (`mobile/lib/services/backend_client.dart:332-347`), and the Profile screen renders only the local `IdentityStore`.
The app therefore displays edits the server never accepted, with no error, no warning, and no retry that could ever succeed (replaying a 409 payload 409s forever, so the "retried push converges" comment is wrong for this case).

## Trust analysis

The 409 block assumes anonymous writes are hostile, but the vessel_id is a 32-hex-character unguessable token, so presenting the full ID already proves ownership on the self-declared tier.
The SOS ingest endpoint already trusts the same basis: it accepts self-declared data from ID-knowers without any credential (`backend/app/api/sos.py:124-149`).
Vessels with a live paired device are already protected above the 409 block by 401/403 (`vessel_profile.py:77-81`), so relaxing the anonymous rule cannot touch them.
Conclusion: for vessels with no live paired device, last-write-wins is safe and matches the SOS trust model; the 409 rule only needs to survive implicitly through the live-device guard.

## Fix (backend only, ships in one redeploy)

1. In `register_vessel_profile`, compute `can_overwrite = is_authorized or not has_active_device` and pass it as `$7` instead of `is_authorized`, so the upsert overwrites stale self-declared fields instead of keeping them.
2. Delete the anonymous-409 comparison block, which becomes dead logic once any write is allowed through.
3. Update the endpoint docstring: anonymous writes are last-write-wins while no live device is paired; a live paired device still gates every write behind 401/403.
4. No migration is needed, and no frontend change is needed: the app already re-pushes the profile on every start and every edit, so the next push converges the server to what the phone shows.

## Verification

`ruff` clean on the touched backend files, all touched modules import, and the pure backend unit tests still pass.
Live check after redeploy: edit the phone profile once (or cold-restart the app to trigger the start-up push), then reload the roster page and confirm the new name, boat, license, and phone appear.
The 401/403 guard for live-paired devices must be re-tested by inspection: an anonymous POST for a vessel with an active device row must still fail.

## Follow-up (not in this fix)

The app still displays local data without comparing it to the server-returned stored row, so a future rejection would again be silent.
The follow-up is to parse the profile POST response in `registerVesselProfile` and surface a "pair your device to update the server copy" notice on mismatch, which needs new localized strings plus a rebuilt APK.
Device-verified fields (`phone_set_by = 'device'`) keep no special protection against anonymous overwrite after this change, which is accepted because revocation already ends that trust and SOS ingest never had it.
