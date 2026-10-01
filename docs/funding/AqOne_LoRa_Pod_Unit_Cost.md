# AqOne LoRa Pod Unit Cost

**Status:** DRAFT
**Owner:** Daniel (hardware); figures owned by the Master Budget
**Created:** 2026-09-30
**Updated:** 2026-09-30
**Related:** `docs/funding/Aquanons_Master_Budget - Master Budget.csv` (B.1.8, revised 28 Sep 2026), `docs/funding/AqOne_Handoff_Doreen.md`, `docs/funding/AqOne_Budget_and_Investor_Summary.md`

## Answer

One LoRa attachment (the strap-on boat pod) costs **₱17,500 in parts**.
With the budget's 5% contingency it is **₱18,375**.
The 22 pods in the DOST budget (20 deployed + 2 spares) come to ₱385,000 in parts.

Every figure below is copied from line B.1.8 of the Master Budget.
Lines the budget marks "Estimate" are flagged; the rest are the budget's supplier prices, not formal quotes.
If the budget changes, the budget wins and this page must be updated.

## What the pod is

A small sealed box that straps onto a fisher's banca.
It runs the LoRa radio to the shore gateway, gives the fisher's phone Wi-Fi on the same boat, knows the boat's GPS position, and has its own SOS button.
It has no solar panel; the family recharges it at home over USB-C.

## Parts list (one pod)

| # | Part | Why it is needed | Cost | Estimate? |
|---|---|---|---:|---|
| 8.1 | RAK WisBlock LoRa node (RAK19007 base + RAK11200 ESP32 + RAK13300 SX1262), 915 MHz | LoRa radio; the ESP32's Wi-Fi serves the phone | ₱3,000 | |
| 8.2 | GNSS set: RAK12500 + active patch antenna + backup cell | Boat position for SOS and drift search | ₱1,750 | |
| 8.3 | 915 MHz antenna, 3-5 dBi fiberglass, N-type | Link to the shore gateway or a relay buoy | ₱2,000 | |
| 8.4 | RF pigtail, IPEX to N bulkhead | Connects the board to the antenna | ₱800 | |
| 8.5 | 4 × LiFePO4 32700 cells (3.2 V 6 Ah) at ₱750 | About 76 Wh, about 2 days per charge | ₱3,000 | Yes |
| 8.6 | USB-C charging and protection board, 2 A | Home charging with a phone charger | ₱500 | Yes |
| 8.7 | Waterproof USB-C panel connector with cap | Charge without opening the sealed box | ₱400 | Yes |
| 8.8 | IP67 polycarbonate enclosure, about 200 × 150 × 100 mm | Houses electronics and battery | ₱1,200 | Yes |
| 8.9 | Sealing set: breather vent, cable glands, desiccant, conformal coating | Keeps salt and moisture out | ₱1,800 | |
| 8.10 | Strap-on mount kit + safety tether | Moves between boats without tools; stays aboard | ₱1,500 | Yes |
| 8.11 | Watchdog (TPL5010) + power monitor (INA226) | Auto-reset; battery level shown in the app | ₱550 | |
| 8.12 | Wiring set: wires, connectors, heat-shrink | Internal wiring | ₱650 | Yes |
| 8.13 | IP67 momentary SOS button with guard cover | SOS without the phone; guard stops accidental presses | ₱350 | Yes |
| | **Total parts** | | **₱17,500** | |

## By subsystem

| Subsystem | Lines | Cost | Share |
|---|---|---:|---:|
| Radio and GPS | 8.1-8.4 | ₱7,550 | 43% |
| Power and charging | 8.5-8.7 | ₱3,900 | 22% |
| Enclosure, sealing and mounting | 8.8-8.10 | ₱4,500 | 26% |
| Monitoring, wiring and SOS button | 8.11-8.13 | ₱1,550 | 9% |
| **Total** | | **₱17,500** | 100% |

## What the ₱17,500 does not include

| Item | Amount | Where it sits in the budget |
|---|---:|---|
| 5% contingency | ₱875 per pod | Contingency line (DOST eligibility still to confirm) |
| Repair parts for the fleet (10 cells, 4 charging boards, 4 USB-C ports, 5 SOS buttons) | ₱12,850 for 22 pods, about ₱584 per pod | B.7 Field Safety, Insurance, and Maintenance |
| Repair and replacement reserve after the pilot | 5% of pod cost per active pod per year, about ₱875 | Investor model, not the DOST budget |
| Service cost after the pilot | ₱300 per active pod per year | Investor model, not the DOST budget |
| Assembly labour | Not priced separately | Covered by the student stipends (A. Personal Services) |
| Shared tools, bench equipment, 3D printing | Bought once for all devices | B.1.10 (₱98,548 total) |
| Shipping, import duties and VAT on RAK parts | Unknown | Open item in the budget review |

Counting the contingency and the repair-parts share, a pilot pod costs about ₱18,959.

## How firm the number is

Seven of the thirteen lines are estimates, worth ₱7,600 or 43% of the pod.
These are the battery, charging board, USB-C port, enclosure, mount kit, wiring and SOS button.
They need a supplier canvass before the budget is submitted.

The RAK parts are priced locally and may not include shipping, duties and VAT.
If they are imported, the radio and GPS subsystem is likely to cost more than ₱7,550.

The pod is priced on RAK WisBlock boards, but the firmware in `firmware/` still targets the Heltec WiFi LoRa 32 V3.
The port to RAK11200/RAK13300 has not been done, and pod range and battery life on RAK boards have not been measured.

## Price history

| Version | Per pod | What changed |
|---|---:|---|
| With a 10-20 W solar panel | ₱18,800 | Solar dropped in favour of home USB-C charging |
| 2 cells, about 38 Wh, about 1 day per charge | ₱15,650 | Raised to 4 cells for an overnight trip plus a missed charge |
| 4 cells, no SOS button | ₱17,150 | Physical SOS button added (+₱350) |
| **Current (28 Sep 2026)** | **₱17,500** | |

## Selling price and margin

The investor model sells a pod to co-ops at ₱19,900, which leaves ₱2,400 (12.1%) over parts.
After the ₱750 investor royalty per pod, the margin is ₱1,650.
The model also assumes pod cost falls 12% a year; if it does not, pods are the model's weakest point.

## Other LoRa devices, for comparison

| Device | Per unit | Quantity in budget |
|---|---:|---:|
| Boat pod (this page) | ₱17,500 | 22 |
| Buoy relay node (clips onto an LGU buoy; solar, Wi-Fi hotspot, LoRa relay) | ₱64,150 | 3 |
| Shore gateway (mast, LTE router, backup battery) | ₱37,400 | 2 |
