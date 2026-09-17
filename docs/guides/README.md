# docs/guides — supporting material

These are general engineering guides. They are **not** interface contracts.

The numbered documents in `docs/` are the contracts between workstreams. Where
a guide disagrees with a numbered contract, **the numbered contract wins.**

| Authority | Location |
|---|---|
| Interface contracts (binding) | `docs/0X_*.md` |
| Supporting guidance (advisory) | `docs/guides/*.md` |

## Known stale content

`guides/05_FLUTTER.md` and `guides/01_CONTRACTS.md` describe an earlier design
in which the **phone** built and signed a 46-byte binary LoRa frame and posted
it to `192.168.4.1:8080/tx`, with delivery states named
`queued_local / received_by_buoy / committed / acknowledged`.

That design was superseded. The live design is:

- The phone posts **JSON** to the buoy at `http://192.168.4.1/v1/sos`
  (`docs/03_PHONE_BUOY_WIFI.md`). The phone holds no signing keys.
- The **buoy** builds and signs the LoRa frame
  (`docs/02_LOAM_PACKET_SPEC.md`), using per-endpoint keys resolved by
  `SRC_ID` at the gateway.
- Delivery states are `saved → relayed → delivered → acknowledged`
  (`docs/06_DELIVERY_STATES.md`).

Do not implement the binary-frame-on-phone design.
