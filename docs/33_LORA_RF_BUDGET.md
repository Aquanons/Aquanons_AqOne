# 33 — LoRa RF Budget & Over-Water Range

Radio-layer design constraints for the hybrid coastal network. Owns the answer
to "how far does it actually reach", the spreading-factor choice, and the
spacing of optional relay buoys.
Complements [`02_LOAM_PACKET_SPEC.md`](02_LOAM_PACKET_SPEC.md), which owns the
frame format; this doc owns the deployment parameters that make the frame
arrive.

**Status:** prototyping (as of 2026-08-26). Numbers below are modelled, not
measured. Nothing here has been validated on the water yet — see
[Open items](#open-items).

## Platform assumption

The primary link is **boat pod → tall shoreline gateway**. The optional relay
link is **stationary node → stationary node**. The existing table uses a
conservative **1.5 m low-node antenna height at both ends**; this is a planning
assumption for boat pods and relay buoys, not an on-water measurement. The
shore gateway is modelled separately at 15–20 m. If the pod mast or antenna
height changes, re-derive — do not scale the ranges linearly.

## The governing constraint: this is not a free-space link

Over open water the link is **two-ray limited**, not free-space limited. The
sea reflects, and the reflected ray arrives close enough to out-of-phase that
it cancels most of the direct ray.

The two-ray breakpoint is `4·h₁·h₂/λ`. At 1.5 m both ends that is **~13 m at
433 MHz** (~27 m at 915 MHz). Every real hop is far beyond it. Likewise, the
first Fresnel zone at 4 km has a radius of **~26 m** while the antennas are
1.5 m up — the sea fills the zone completely.

Consequences, in order of importance:

1. Path loss grows at **40 dB/decade**, not 20. Range scales as the *fourth*
   root of power, not the square root.
2. **+6 dB buys ×1.41 range, not ×2.** Sensitivity and TX-power improvements
   are worth far less than intuition suggests.
3. **Antenna height is the dominant lever.** Doubling height at both ends is
   +12 dB, i.e. ×2 range — more than any chip upgrade available.
4. Any range figure derived from free-space path loss will be roughly **5×
   too optimistic**. Do not put free-space numbers in the pitch deck, the PRD,
   or a grant application.

### Working formula

```
L(dB) = 40·log₁₀(d_m) − 20·log₁₀(h₁) − 20·log₁₀(h₂)

Budget = P_tx + G_tx + G_rx + |S_rx| − M_fade
```

Assumptions used throughout: `P_tx` = +22 dBm, `G_tx` = `G_rx` = 2 dBi
(stock whip), `M_fade` = 10 dB, BW 125 kHz, CR 4/5, 94-byte frame
(the max LoAM frame size from `02_LOAM_PACKET_SPEC.md`).

## Range and airtime by spreading factor

Low-node-to-low-node, both antennas at 1.5 m. Use this table for pod-to-relay
and relay-to-relay planning; direct pod-to-shore uses the taller gateway
horizon described below.

| SF | SX1262 sens. | SX1262 range | LR2021 sens. | LR2021 range | Time-on-air |
|---|---|---|---|---|---|
| 7  | −123 dBm | 4.5 km | −127.5 dBm | 5.8 km | 165 ms |
| 9  | −129.5 dBm | 6.4 km | −134 dBm | 8.4 km | 530 ms |
| 10 | −132 dBm | 7.5 km | −136.5 dBm | 9.7 km | 950 ms |
| 12 | −137 dBm | ~10 km † | −141.5 dBm | 13 km † | 3.8 s |

**Time-on-air is for a 94-byte frame and is stale for the SOS (corrected 2026-09-26).**
The 94 bytes came from the old 64-byte payload cap in `02_LOAM_PACKET_SPEC.md`; the shipped firmware allows 225 payload bytes (`LOAM_MAX_PAYLOAD`), and a real SOS frame is about 170 to 255 bytes.
At SF10 / 125 kHz / CR 4/5 that is about **1.6 to 2.3 s per SOS hop**, and about 0.9 s for an ACK.
The weather-tiered check-in frame (`68_WEATHER_TIERED_CHECKINS_SPEC.md`) is 46 bytes, about **0.54 s**.

† **Capped by the horizon, not the budget.** The geometric radio horizon at
1.5 m both ends is `4.12·(√1.5 + √1.5)` = **10.1 km**. SF12 has budget for
more distance than the earth will give you.

## The horizon wall

This is the single most important line in this document:

> **At 1.5 m of antenna height, a low-node link is geometry-limited, not
> chip-limited.** No transceiver reaches past ~10 km pod-to-relay or
> relay-to-relay. Only the optional relay chain can extend the overall area.

The same holds on the shore link. A gateway on a 15–20 m mast has a horizon of
~23.5 km, and even an SX1262 at SF10 already models to ~27 km. Both links run
out of earth before they run out of link budget.

This is why the TTL-flood mesh in `02_LOAM_PACKET_SPEC.md` is not an
implementation convenience — it is what the physics requires. Worth stating
plainly to reviewers and funders, because it reframes the mesh from a design
choice into a necessity.

## Recommended configuration

**SF10 on the current SX1262 hardware** (7.5 km, ~950 ms for a 94-byte frame, ~1.8 s for a real SOS), superseding the
`SF 7` currently written into `02_LOAM_PACKET_SPEC.md`'s radio-parameters
table.

Rationale:

- SF7's 4.5 km forces relay spacing so tight the deployment cost stops working.
- SF12 is a trap: it costs 4× the airtime of SF10 and lands exactly at the
  10.1 km horizon, so it buys nothing usable. In a TTL flood where every relay
  retransmits, a 3.8-second frame makes collisions the binding constraint long
  before range is.
- SF10 keeps a 94-byte hop under a second; a real SOS hop is nearer 2 s, which is why routine check-ins get their own channel (`68_WEATHER_TIERED_CHECKINS_SPEC.md` D9) instead of sharing the SOS channel.

**Optional relay spacing: 4–5 km**, i.e. 60–70% of modelled low-node range. Do
not deploy buoys at this spacing by default: first test the direct pod-to-shore
link, then add relay buoys only for measured dead zones or fixed-sensor needs.
The margin is not padding — see [Sea state](#sea-state-and-why-the-margin-is-not-padding).

### Note — the dashboard's demo coverage radius is not a modelled range

The operations dashboard can draw a **5 km-wide** coverage zone per buoy
(2500 m radius) under its `?demo=1` flag. That figure is a **presentation
radius** chosen so vessels visibly fall inside coverage on a zoomed-out map
during a demo. It is not derived from anything in this document and is not a
capability claim. Real phone-contact range is ~1.2 km and real LoRa relay
range is the table above. The demo radius is deliberately smaller than every
buoy's `loraRadius`, so the demo zone always nests inside the real relay ring.
See [`34_DEMO_COVERAGE_DRAG_PLAN_LUNA.md`](34_DEMO_COVERAGE_DRAG_PLAN_LUNA.md).

## Sea state, and why the margin is not padding

A 1.5 m antenna against 1.5 m significant wave height means wave crests
intermittently occlude the path. The mesh degrades in precisely the weather
that generates distress traffic, which is the worst possible failure
correlation for an SOS system.

Design implications:

- Prefer the SF with margin over the SF with reach.
- Accept more relay hops than clear-weather geometry requires.
- Treat any single-hop link as unreliable by default; the seen-set and TTL
  flood are the reliability mechanism, not the individual link.

## Transceiver options

### SX1262 (current — Heltec WiFi LoRa 32 V3)

What `firmware/` is built against today. +22 dBm, ~−137 dBm at SF12/125 kHz.
Adequate: as shown above, the link is horizon-limited, so the SX1262's
sensitivity is not what is holding the system back.

### LR2021 (evaluated 2026-08-26 — not adopted)

Semtech's Gen-4 "LoRa Plus" part. Same **+22 dBm** sub-GHz TX, sensitivity to
**−141.5 dBm @ SF12/125 kHz**, 150–960 MHz continuous coverage, multi-SF
receive, 5.7 mA RX.

**Gain: ~4.5 dB of sensitivity. It does not extend low-node-to-low-node range**,
because the horizon binds first (see the table's † rows).

Where it would genuinely help, if adopted later:

- **Airtime, not distance.** Spend the 4.5 dB on a lower SF instead: SF9 on
  LR2021 reaches 8.4 km, beating SF10 on SX1262's 7.5 km, at 530 ms instead of
  950 ms. Nearly halving time-on-air directly reduces flood collisions — the
  one metric under real pressure in this architecture.
- **Multi-SF receive** makes per-hop adaptive SF implementable: relays could
  hear fast near-gateway hops and slow far hops in one listen.
- **150–960 MHz** means one part number covers both candidate bands, deferring
  the band decision to after regulatory confirmation (front-end matching and
  antenna still differ per band, so this is not free).

**Decision: not adopted for the prototype.** `firmware/` is Arduino on Heltec
V3; there is no drop-in LR2021 board in that class, so adoption means the
Seeed EVK or an nRF54L15 combo board plus a rewritten radio driver layer
against a young library ecosystem. Revisit at pilot hardware selection.

The LoAM frame in `02_LOAM_PACKET_SPEC.md` is deliberately transceiver-
agnostic, so this decision is reversible at no protocol cost.

## Open items

- [ ] **Band unresolved.** `02_LOAM_PACKET_SPEC.md` specifies 433.0 MHz;
      `19_HELTEC_DATA_FLOW.md` says 915 MHz. Must be settled before pilot
      hardware is ordered. Note that **range is frequency-independent in the
      two-ray regime**, so decide on antenna size, channel congestion, and PH
      regulatory grounds — not on range. 433 MHz diffracts marginally better
      over wave crests; 915 MHz gives a smaller antenna and more channel room.
- [ ] **PH regulatory confirmation** (NTC) for the chosen band, duty cycle,
      and permitted EIRP. Not yet checked. The +22 dBm assumption above may
      not survive it.
      The check-in channel (`68_WEATHER_TIERED_CHECKINS_SPEC.md` D9) adds a second
      frequency in the same band; Len accepted that as a risk rather than a
      prerequisite (2026-09-26).
- [ ] **Per-SF LR2021 sensitivities are extrapolated.** Only the SF12 figure
      is published; the other LR2021 rows apply the same ~4.5 dB delta.
      Confirm against the full datasheet table before quoting externally.
- [ ] **No on-water measurement yet.** Every range in this doc is modelled.
      A two-node range test at the real mounting height is the highest-value
      next experiment — it validates or destroys the 40 dB/decade assumption
      that everything else rests on.
- [ ] Fade margin of 10 dB is assumed, not derived from measured sea-state
      fading. Revisit after the range test.

## References

- Semtech LR2021 product page —
  <https://www.semtech.com/products/wireless-rf/lora-plus/lr2021>
- LR2021 datasheet Rev. 1.1 —
  <https://www.mouser.com/pdfDocs/61979758LR2021_V1_1_datasheet.pdf>
- Frame format: [`02_LOAM_PACKET_SPEC.md`](02_LOAM_PACKET_SPEC.md)
- Firmware/backend contract: [`19_HELTEC_DATA_FLOW.md`](19_HELTEC_DATA_FLOW.md)
