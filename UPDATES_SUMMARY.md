# What Changed (Explained Simply)

This is a list of everything new in the AqOne app, written so simply a 7-year-old can follow it.
Think of AqOne like a classroom where fishermen can call for help and helpers can see them on a map.

## A button that makes the map HUGE

There is a new little button next to the retry arrow above the map.
When you tap it, the map fills the whole screen so you can see everything big and clear.
Tap it again (or press Esc) and the map goes back to normal.
The map redraws itself so it never looks broken or half-empty.

## Only 5 finished problems show, with a View button

The "finished problems" list used to show every single one, which made the page very long.
Now it shows only the 5 newest, and a View button opens the full list when you want it.
The button hides itself when there are 5 or fewer.

## The top cards fit nicely with almost no gap

The three small cards at the top (SOS count, squall warning, last update time) used to have ugly empty space inside and below them.
Now they hug their words snugly, the gap below them is only 1 pixel, and the map underneath got taller to use the saved space.
Long words get "..." instead of pushing the third card off the screen.

## A 4th card that counts friends online

A new card called APP USERS joined the top row, and all four cards are the same size.
The big number tells how many friends are around right now: helpers on computers plus fisher phones that talked to the system in the last 15 minutes.
The small text breaks it down, like "1 helpers, 0 phones, 1 name on the list".
It checks every 30 seconds and honestly says OFFLINE when it cannot reach the server.

## The counter knows YOU are here

At first the counter could not see helpers at all, so it said 0 even with you sitting right there.
Now your open dashboard waves "I'm here!" every 30 seconds, and the counter includes you.
Closing your tab stops the waving, and you drop off the count after about 2 minutes.
Every tap a fisher phone makes (SOS, profile save, catch note, trip update, sign-up) also stamps that boat as "here".

## A class list page when you tap the card

Tapping APP USERS opens a full list of every boat: name, license number, phone number, awake-or-asleep status, sea status, and last known spot on the water.
Buttons filter the list: All, Active, Inactive, or At sea.
Empty details show honest labels like "Unregistered" instead of hiding.

## Sending an SOS counts as being active

Before, sending an SOS did not light up the Active lamp because SOS messages need no login.
Now any hello to the system in the last 15 minutes (SOS, buoy ping, catch note, or paired-device check-in) marks that boat Active.
This uses one shared rule, so the card and the list page can never disagree.

## Fixed phones show as ON LAND, not at sea

Test SOS taps made from town were labeled "went to sea" just because the phone had a location.
Now every location is checked against the real shape of the bay water.
Water spots still say WENT TO SEA (or AT SEA when a trip is open), town spots say ON LAND in gray, and boats with no location say NO SEA RECORD.
The shape of the bay is hand-drawn and approximate, so a spot exactly on the shoreline could read either way.

## Profiles match between phone and dashboard

The phone showed new details (new name, new boat, new number) while the dashboard showed old ones for the same boat.
That happened because the server rejected name changes from unpaired phones without telling anyone, while the phone showed its own unsent edits.
Now the newest save wins for boats with no paired device (the long secret boat code already proves ownership, the same trust as SOS messages), while boats with a paired device still require that device.
Full details live in `PROFILE_MISMATCH_FIX.md`.

## The whale logo everywhere

The dashboard header keeps its whale logo, and the little browser-tab picture is now the same AqOne whale instead of a different cartoon whale.
The tab picture is also much smaller to download.

## Papers that explain things

Three new notes were added: `DASHBOARD_UPDATES.md` (the screen changes in grown-up words), `APP_FEATURES.md` (every feature, how the whole system works, the computers-and-code details, and all 14 data collections), and `PROFILE_MISMATCH_FIX.md` (the phone-vs-dashboard mystery and its fix).
This file you are reading is the simple version of all of them.
