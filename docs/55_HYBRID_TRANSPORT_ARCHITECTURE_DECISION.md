# 55 - Hybrid Transport Architecture Decision

**Status:** ACTIVE
**Owner:** Team Aquanons
**Created:** 2026-09-17
**Updated:** 2026-09-17
**Related:** `docs/00_START_HERE.md`, `docs/01_ARCHITECTURE.md`, `docs/02_LOAM_PACKET_SPEC.md`, `docs/03_PHONE_BUOY_WIFI.md`, `docs/33_LORA_RF_BUDGET.md`

## Decision

AqOne will use a hybrid transport architecture.

Boat-mounted safety pods are the primary phone access and SOS origin nodes.
Each pod provides short-range local WiFi, a physical SOS path, local queueing,
and LoRa to the shore gateway.

Stationary navigational buoys remain in the system where their fixed position,
sensors, or relay coverage provides a measurable benefit.

The primary topology is:

```text
Phone --local WiFi--> Boat pod --LoRa--> Shore gateway --HTTPS--> Backend
                                     ^
                                     |
                         Optional LoRa relay buoy
```

## Why the architecture changed

The original design required the WiFi access point on each navigational buoy to
cover the water around it.
That makes coverage area depend on the number of buoys, their moorings, their
power systems, and their maintenance access.

Moving the WiFi endpoint onto the boat reduces the phone link to a few metres,
where normal WiFi is appropriate.
LoRa becomes the long-distance transport to a tall, shoreline-mounted,
bidirectional gateway.

This avoids deploying fixed buoys solely to create phone WiFi coverage while
preserving the benefits of fixed offshore instrumentation.

## Node roles

| Node | Primary responsibility | Optional responsibility |
|---|---|---|
| Boat safety pod | Phone WiFi, physical SOS, flash-backed queue, direct LoRa | GPS, battery, motion events |
| Stationary sensor buoy | Fixed-position current and environmental telemetry (no barometer; weather comes from the PAGASA weather API) | LoRa relay, physical warning indicator |
| Stationary relay buoy | Extend LoRa coverage into measured dead zones | Fixed sensors and warning cache |
| Shore gateway | Tall LoRa endpoint, acknowledgements, backend HTTPS | Second gateway for redundancy |
| Shore check-in receiver (approved 2026-09-26, not built) | Listens only on the check-in channel and uploads pod check-ins in batches (`docs/68_WEATHER_TIERED_CHECKINS_SPEC.md` D9) | None |

Stationary buoys do not need to provide phone WiFi unless a field test gives
that feature a specific operational purpose.

## Compatibility decisions

- Keep the existing LoAM binary frame and HMAC signing scheme.
- Direct pod-to-gateway frames use `HOPS = 0`.
- Optional relay buoys continue to use TTL flooding and the seen-set.
- Keep SOS traffic at absolute priority over sensor, warning, chat, and beacon
  traffic.
- Preserve the existing phone API shape during the prototype; the current
  `buoy_id` field is a compatibility name for the serving radio node and should
  not be renamed without an interface migration.
- Keep fixed-position sensor data separate from moving boat-pod data for
  nowcasting. Boat telemetry may be stored, but it is not automatically treated
  as a fixed sensor-array observation.

## Reliability requirements

Every boat pod must queue an SOS before acknowledging the phone, persist the
queue through power loss, retry until the shore gateway acknowledges receipt, and
provide a unique device identity and production key.

The shore gateway must transmit as well as receive so acknowledgements, ETAs,
and warnings can return to pods and stationary nodes.

The pod enclosure must be waterproof, strap-mounted, tethered, independently
powered, and fitted with an external vertical LoRa antenna positioned clear of
the hull and other electronics.

## Acceptance gate

The pivot is accepted only after one boat pod and one shore gateway demonstrate:

1. Phone in airplane mode connects to the pod over local WiFi.
2. The pod queues and transmits an SOS directly over LoRa.
3. The shore gateway receives it and forwards it to the backend.
4. The dashboard displays it and a responder acknowledgement returns.
5. A power interruption does not lose the queued SOS.
6. Repeated tests succeed at the farthest intended operating point.

Add stationary relay buoys only after the direct link test identifies a coverage
gap or after fixed sensors are required at that location.
