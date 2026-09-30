# Hardware schematics

This folder holds the hardware drawings for the AqOne field devices and the shore station.

| File | What it is |
|---|---|
| [`component-briefer.pdf`](component-briefer.pdf) | Three-sheet parts briefer: sheet 1 strap-on pod, sheet 2 shore station, sheet 3 buoy node. |
| [`strap-on-pod-buoy.glb`](strap-on-pod-buoy.glb) | 3D model of the strap-on pod mounted on a navigational buoy. |
| [`clip-on-relay-node.glb`](clip-on-relay-node.glb) | 3D model of the clip-on relay node. |
| [`shore-station.glb`](shore-station.glb) | 3D model of the shore station, updated to the corrected design below. |

The drawings are not to scale.
The costed parts list is section B.1 of [`../docs/funding/Aquanons_Master_Budget - Master Budget.csv`](<../docs/funding/Aquanons_Master_Budget - Master Budget.csv>).

Sheets 1 and 3 (strap-on pod and buoy node) are final.
Sheet 2 (shore station) has errors; use the corrected design below until the PDF is regenerated.

## Shore station

### What it does

The AqOne backend is a cloud server (`https://aqone-backend.onrender.com`), so the shore station exists to bridge LoRa into the internet.
Nothing at sea has internet; the shore station is the only device that does.

```
pod / buoy --LoRa 915 MHz--> RAK13300 --> RAK11200 --WiFi 2.4 GHz--> LTE router --> internet --HTTPS--> backend
pod / buoy <--LoRa 915 MHz-- RAK13300 <-- RAK11200 <--WiFi 2.4 GHz-- LTE router <-- internet <--HTTPS-- backend
```

The return path carries the dispatcher's acknowledgement, ETA and chat back down to the boats.
The shore firmware ([`../firmware/shore/AqOneShore/`](../firmware/shore/AqOneShore/)) is a WiFi station only: it joins the router's network and runs no access point, so no phone ever connects to it.

### Two devices, two sets of antennas

Like the buoy node, the shore station pairs a RAK stack with a separate network device.

| Device | Job | Antenna |
|---|---|---|
| RAK stack: RAK19007 base + RAK11200 (ESP32) + RAK13300 (SX1262) | Hears and answers the mesh over LoRa, and forwards over WiFi | External 915 MHz omni on the pole, through the RAK13300's IPEX connector |
| LTE router with WiFi | Internet uplink | The router's own WiFi and LTE antennas |

The RAK11200 has only a built-in PCB antenna and no connector for an external WiFi antenna.
That is fine here because the router sits a few centimetres away in the same enclosure.

### Corrected parts list

The budget line for each part is in brackets.

| # | Part | Notes |
|---|---|---|
| 1 | RAK19007 base + RAK11200 + RAK13300, 915 MHz part [9.1] | No RAK12500 GPS: the shore station does not move. Order the 868/915 MHz RAK13300, not the 433 MHz variant. |
| 2 | LTE router with WiFi, 12 V [9.10] | Must offer a 2.4 GHz network with WPA2. The ESP32 cannot join a 5 GHz-only or WPA3-only network. |
| 3 | 915 MHz fiberglass omni, 6-8 dBi, N-type [9.2] | Target antenna height is 15-20 m, per [`../docs/33_LORA_RF_BUDGET.md`](../docs/33_LORA_RF_BUDGET.md). |
| 4 | Galvanized pole 3-6 m with clamps and guy kit [9.7] | Mounted on a tall LGU-provided structure to reach the 15-20 m height. |
| 5 | LMR-400 jumper, about 2 m, N-N [9.3] | Antenna to enclosure. |
| 6 | Surge arrestor, 915 MHz, N-type [9.5] | On the LoRa line where it enters the enclosure, bonded to the ground kit. |
| 7 | RF pigtail, IPEX to N bulkhead [9.4] | RAK13300 to the enclosure wall. |
| 8 | Grounding kit: rod, cable, clamps [9.6] | Pole and surge arrestor. |
| 9 | IP67 enclosure, about 400x300x180 mm, and sealing set [9.8, 9.9] | Holds the RAK stack, router, battery and power parts at the top of the pole. |
| 10 | LiFePO4 12 V 20 Ah backup battery and mains smart charger [9.11, 9.12] | About 50 hours of backup for the RAK and router through brownouts. |
| 11 | 12 V to 5 V converter, fuses and wiring [9.13] | The RAK stack runs on 5 V; the router runs on 12 V. |
| 12 | Watchdog, power monitor and enclosure sensor [9.14] | Gateway health reporting. |

The equipment box goes at the top of the pole, next to the antenna.
LMR-400 loses about 0.13 dB per metre at 915 MHz, so a 2 m jumper costs about 0.3 dB, while a 10 m or longer run down to ground level costs 1.3 dB or more.
Mounting the LTE router up high also improves its cellular signal.

### Errata for briefer sheet 2

| Sheet 2 shows | Correct design | Why |
|---|---|---|
| RAK4631 WisBlock Core (item 17) | RAK11200 + RAK13300 on RAK19007 | The RAK4631 is an nRF52840 with LoRa and Bluetooth but no WiFi, so it cannot reach the router. The shore firmware needs WiFi to post to the backend. |
| Equipment rack at ground level with a long LMR-400 run up the mast (items 16, 17) | IP67 box at the top of the pole with a 2 m jumper | Roughly 1-1.5 dB less cable loss, which is range the shore link keeps. |
| Backend server, mini PC or Raspberry Pi 5 (item 18) | Remove | The backend is a cloud server on Render; the shore station posts to it directly over the internet. |
| UPS on AC mains (item 19) | 12 V LiFePO4 battery with a mains charger | The router and RAK both run on DC, so a DC battery avoids conversion losses and matches the budget. |
| Router on fiber with LTE backup (item 20) | LTE router with 2.4 GHz WiFi | Works wherever there is cell signal and runs on the 12 V backup battery. |
| 6-10 m mast | 3-6 m pole on a tall LGU structure, antenna at 15-20 m | Matches the budget and the RF plan. |

Until sheet 2 is regenerated from this table, this README and `shore-station.glb` are the source of truth for the shore station.

### 3D model callouts

`shore-station.glb` already shows the corrected design.
The IP67 box sits on the pole just below the antenna, with the RAK stack, LTE router, battery, charger and DC-DC converter inside.
The surge arrestor is at the enclosure entry on the short LMR-400 jumper, and the ground wire and mains cable run down the pole.
Its callouts keep the sheet 2 numbers where the part survived and reuse 18 and 19 for the new parts:

| # | Callout |
|---|---|
| 15 | Shore antenna |
| 16 | LMR-400 jumper + arrestor |
| 17 | RAK11200 + RAK13300 on RAK19007 |
| 18 | IP67 enclosure at pole top (was: backend server) |
| 19 | LiFePO4 12 V battery (was: UPS) |
| 20 | LTE router, 2.4 GHz Wi-Fi |

The model still stands the pole on a ground pad rather than on an LGU structure.

### Firmware status

The shore and field firmware still targets the Heltec WiFi LoRa 32 V3 bench boards.
Moving to the RAK stack needs only a pin and board port of the shared radio header and `platformio.ini`; the shore's WiFi-station behaviour already matches this design.
