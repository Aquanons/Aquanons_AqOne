# Tall shoreline gateway sketch

`AqOneShore/AqOneShore.ino` — the board on the mast with the internet.

LoRa plus a WiFi station, and **no access point**: it hears direct boat-pod
frames and optional stationary-relay traffic, posts to the backend, polls for
the dispatcher's acknowledgement, and sends the answers back down. No phone
ever connects to it, and it never re-transmits LoRa frames.

Its field-node partner is [`../buoy/AqOneBuoy`](../buoy/AqOneBuoy).

Two files, both part of the sketch:

| File | |
|---|---|
| `AqOneShore.ino` | Everything gateway-specific. Set `AQONE_NODE_ID` / `AQONE_NODE_NAME`, the uplink WiFi, and an `OPS_TOKEN` or operator login at the top. |
| `AqOneLoam.h` | The shared radio layer. **Must stay byte-identical to the buoy's copy** — `diff` them after any edit. |

No `build_opt.h` here: this sketch has no WebSocket server, so the flag the buoy
needs does not apply.

Board setup, libraries, the radio protocol, which backend endpoints this calls
(and which one needs a credential), the bring-up order and the honest
limitations are all in [`../README.md`](../README.md).
