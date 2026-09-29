# AqOne Budget and Investor Planning - Session Summary

Session date: 28 September 2026.
Covers the DOST Master Budget revision, the business model discussion, and the investor model for the startup competition.
All peso figures are exact values from the two workbooks unless marked "estimate" or "approx".

## 0. Revision after the independent review (28 Sep 2026, evening)

This section supersedes the figures below where they differ.
Current authoritative figures are in `AqOne_Handoff_Doreen.md` and the two workbooks.

DOST budget:
- Grand total is now ₱1,705,525.37 (was ₱1,558,472.87).
- MOOE ₱1,275,426.68; direct costs ₱1,624,309.88; contingency ₱81,215.49.
- Pods 22 (20 deployed + 2 spares) at ₱17,500 each with a physical SOS button (₱350): B.1 is now ₱750,798.
- B.5 is now ₱130,000 with sea access (16 pumpboat trips × ₱2,500, estimate); land travel restated as equivalent public transport cost (EO 77, Sec. 5(a)).
- New B.7 Field Safety, Insurance, and Maintenance: ₱58,050 (life vests ₱7,200; first aid ₱1,500; accident insurance top-up ₱7,000; buoy spares kit ₱29,500; pod repair parts ₱12,850).
- The ₱70,000 business/design line is now 2 project-owned laptops or tablets (not necessarily iPads).

Investor model:
- Royalty rule fixed: exactly half rates in Y2 and full rates from Y3 (the earlier file paid 37.5% in Y2 while labelled "half").
- Pod cost ₱17,500; new pod replacement and repair reserve of 5% of pod cost per active pod per year.
- Y1 company costs (₱800,000) funded outside the grant and investors; Y1 cost no longer scales with pace.
- Cash is checked just before each tranche arrives; any shortfall triggers bridge financing at the ₱75M valuation, which dilutes the investor.
- New outcomes: multiple 1.21× / 3.15× / 6.48×; IRR 6.0% / 41.8% / 75.7%; no-exit multiple 0.28× / 0.53× / 0.85×; lowest cash Y2-Y5 ₱120,404 / ₱139,473 / ₱145,788.

## 1. Files

| File | What it is | Status |
|---|---|---|
| `Aquanons_Master_Budget.xlsx` | DOST line-item budget (PS / MOOE / EO) | Final for this session. Saved to the AqOne project folder. |
| `Aquanons_Master_Budget - Master Budget.csv` | CSV export of the budget | Replaced with the new version in the AqOne project folder. |
| Google Sheet "Aquanons_Master_Budget" (Drive) | Team copy of the budget | Not yet replaced. Use File > Import > Upload > Replace spreadsheet to keep the same link. |
| `AqOne_Investor_Model.xlsx` | Investor model: hybrid deal, milestone tranches | Final for this session. Separate from the DOST budget. |
| `BUSINESS MODEL_AQONE.md` | Old business model doc | Archived on 29 Sep 2026 to `docs/archive/business-case/` because it cites ₱808,448.55 and the ₱144,738 cloud line. Section 4 below and `AqOne_Handoff_Doreen.md` replace it. |

Drive housekeeping found: the Sheet is shared as "anyone with the link can edit".
Three older copies named "Aquanons_Master_Budget" (two Sheets, one .xlsx, all from August) still exist in Drive.

## 2. DOST Master Budget

### 2.1 Grand total history

| Version | Grand total |
|---|---:|
| Original upload (FX ₱61.20, flat stipends) | ₱1,598,251.20 |
| Tiered stipends at ₱65.63/hr | ₱1,622,289.06 |
| Test: one MSI replaced by Dell Pro Rugged 14 (reverted) | ₱1,787,525.87 |
| Added 2 SSDs + 2 portable monitors | ₱1,650,383.91 |
| SSDs removed, monitors kept | ₱1,631,106.96 |
| **Final (approved batch applied)** | **₱1,558,472.87** |

Original breakdown: PS ₱216,000; MOOE ₱1,196,154; EO ₱109,990; direct ₱1,522,144; contingency 5% ₱76,107.20.

### 2.2 Final totals

| Section | Total |
|---|---:|
| A. Personal Services | ₱238,893.20 |
| B.1 Supplies and Materials | ₱708,798.00 |
| B.2 Software Subscriptions | ₱126,504.00 |
| B.3 Cloud Infrastructure and Hosting | ₱68,492.88 |
| B.4 Communication | ₱48,581.80 |
| B.5 Travel and Transportation | ₱90,000.00 |
| B.6 Dissemination, Engagement, Business/Design Support | ₱93,000.00 |
| **B. MOOE total** | **₱1,135,376.68** |
| C. Equipment Outlay | ₱109,990.00 |
| Direct project costs | ₱1,484,259.88 |
| Contingency (5%) | ₱74,212.99 |
| **Grand total** | **₱1,558,472.87** |

### 2.3 Input cells at the top of the sheet

| Cell | Input | Value | Basis |
|---|---|---:|---|
| B4 | USD to PHP rate | 62.75 | BSP reference rate, 25 Sep 2026 (buying 62.500, selling 63.000). Was 61.20. |
| B5 | Hourly labor rate | ₱65.63 | Wage Order RBVI-29: ₱525/day (non-agri, ≤10 workers) ÷ 8 = ₱65.625 |
| B6 | Buoy relay nodes | 3 | Planning assumption pending LGU consultation |
| B7 | Boat pods | 20 | 18 deployed + 2 spares |
| B8 | Shore gateways | 2 | Primary + redundant site |

### 2.4 A. Personal Services

| Line | Hours | Rate | Total | Monthly equivalent |
|---|---:|---:|---:|---:|
| Lead student researcher (Lenard: backend, architecture, deployment), 20 hrs/wk × 52 wks | 1,040 | ₱65.63 | ₱68,255.20 | ≈₱5,688 |
| 5 student researchers, 10 hrs/wk × 52 wks each | 2,600 | ₱65.63 | ₱170,638.00 | ≈₱2,844 each |

Team: 4 technical (Lenard backend/architecture/deployment, Arnold website dashboard, Daniel hardware and buoy firmware, Jade Flutter application) + 2 business (Doreen Kay pitching/branding/business direction, KC Condes pitching and business development support).
Label changed from "Project lead" to "Lead student researcher" because the DOST Project Leader is normally the ASU faculty member.

Alternatives considered:

| Option | Annual total |
|---|---:|
| Original flat ₱3,000/month × 6 × 12 | ₱216,000 (≈₱69.23/hr) |
| Flat at ₱65.63/hr, everyone 10 hrs/wk | ₱204,750 (at ₱65.625) |
| **Tiered at ₱65.63/hr (chosen)** | **₱238,893.20** |
| ChatGPT labor valuation doc (₱67/hr, tiered) | ₱243,880 |

The ChatGPT valuation doc wrongly "rounded" ₱65.625 to ₱67 and contains `:chatgpt-content-reference` artifacts to delete.
Paid stipend hours cannot also be claimed as in-kind counterpart.

### 2.5 B.1 Supplies and Materials

**Buoy relay node: ₱64,150 per node × 3 = ₱192,450.**
Previously ₱72,400 per node × 10.
Removed because nodes mount on LGU buoys only: Victron Orion ship charger (₱6,500/node), ship adapter bracket (₱1,500/node), ship-input fuse (₱250/node).

| Subsystem | Per node | × 3 |
|---|---:|---:|
| Power (100 W panel ₱5,500; Victron MPPT ₱5,500; 12V 50Ah LiFePO4 ₱12,000; 2 fuses ₱500; buck ₱400; wiring ₱800) | ₱24,700 | ₱74,100 |
| Communications (MikroTik BaseBox 2 ₱6,500; PoE ₱400; 2 × 2.4 GHz antenna ₱4,000; 2 pigtails ₱800; 2 × 2.4 GHz arrestor ₱2,400; RAK WisBlock ₱3,000; 915 MHz antenna ₱2,000; RF pigtail ₱800; 915 MHz arrestor ₱1,500) | ₱21,400 | ₱64,200 |
| GPS (RAK12500 ₱1,200; patch antenna ₱400; backup cell ₱150) | ₱1,750 | ₱5,250 |
| Control and monitoring (TPL5010 ₱300; BME280 ₱250; INA226 ₱250) | ₱800 | ₱2,400 |
| Enclosure and sealing (enclosure ₱3,500; vent ₱300; glands ₱400; desiccant ₱200; coating ₱900; mounting set ₱400) | ₱5,700 | ₱17,100 |
| Quick-release mounting (clamp ₱3,500; buoy bracket ₱1,500; mast ₱1,500; tether ₱600; lock ₱800; fasteners ₱400) | ₱8,300 | ₱24,900 |
| Safety lighting, optional (solar LED beacon ₱1,500) | ₱1,500 | ₱4,500 |

**Boat pod (strap-on, no solar, USB-C charged at home): ₱17,150 per pod × 20 = ₱343,000.**

| Item | Per pod |
|---|---:|
| RAK WisBlock (RAK19007 + RAK11200 + RAK13300), built-in Wi-Fi for the phone | ₱3,000 |
| GNSS set (RAK12500 + patch antenna + backup cell) | ₱1,750 |
| 915 MHz antenna | ₱2,000 |
| RF pigtail | ₱800 |
| 4 × LiFePO4 32700 cells (3.2 V 6 Ah) at ₱750, ≈76 Wh, about 2 days per charge (estimate) | ₱3,000 |
| USB-C charging and protection board, 2 A (estimate) | ₱500 |
| Waterproof USB-C port with cap (estimate) | ₱400 |
| IP67 enclosure ~200×150×100 mm (estimate) | ₱1,200 |
| Sealing set (vent, glands, desiccant, coating) | ₱1,800 |
| Strap-on mount kit + tether (estimate) | ₱1,500 |
| Watchdog + power monitor | ₱550 |
| Wiring set (estimate) | ₱650 |

Earlier pod versions: ₱18,800 (with 10-20 W solar), ₱15,650 (2 cells, ≈38 Wh, about 1 day).
Pod average draw is under 1 W with Wi-Fi hotspot, GNSS and LoRa running.

**Shore gateway: ₱37,400 per gateway × 2 = ₱74,800.**

| Item | Per gateway |
|---|---:|
| RAK WisBlock stack | ₱3,000 |
| 915 MHz omni 6-8 dBi (estimate) | ₱3,500 |
| LMR-400 coax jumper ~2 m (estimate) | ₱1,500 |
| RF pigtail | ₱800 |
| 915 MHz surge arrestor | ₱1,500 |
| Grounding kit (estimate) | ₱1,500 |
| Rooftop pole 3-6 m + clamps + guy kit (estimate) | ₱6,000 |
| IP67 enclosure ~400×300×180 mm | ₱3,500 |
| Sealing set | ₱1,600 |
| LTE router with Wi-Fi, 12 V (estimate) | ₱3,500 |
| LiFePO4 12 V 20 Ah backup battery, about 50 h (estimate) | ₱6,000 |
| Mains smart charger (estimate) | ₱2,500 |
| Power wiring set | ₱1,700 |
| Health monitoring | ₱800 |

The RF plan (`docs/33_LORA_RF_BUDGET.md`) models the gateway at 15-20 m, so the pole goes on an LGU-provided tall structure.
Firmware (`firmware/shore`) joins Wi-Fi for its uplink, hence the LTE router.

**B.1.10 Bench, tools and consumables: ₱98,548.**

| Item | Total |
|---|---:|
| MPU6050 10-pack | ₱2,000 |
| PCB protoboard | ₱1,500 |
| Breadboard | ₱600 |
| Soldering station YIHUA 982D-SE | ₱8,500 |
| 2 × Nvision 15.6" portable monitor at ₱4,199 | ₱8,398 |
| Soldering consumables (estimate) | ₱4,150 |
| Sealing and adhesives (estimate) | ₱8,100 |
| Wiring and connector consumables (estimate) | ₱4,200 |
| 2 × anti-corrosion spray at ₱500 (estimate) | ₱1,000 |
| Hand tools (estimate) | ₱5,500 |
| Power tools: heat gun, cordless drill + step bits (estimate) | ₱6,000 |
| Test equipment: multimeter, bench PSU 0-30 V 5 A, USB-C meter, NanoVNA (estimate) | ₱11,500 |
| Bench safety and ESD (estimate) | ₱4,800 |
| Labels and storage (estimate) | ₱2,300 |
| 3D printing at ASU: 6 kg × ₱5,000/kg (₱5/g estimate, PETG/ASA) | ₱30,000 |

B.1 check: 192,450 + 343,000 + 74,800 + 98,548 = ₱708,798.

### 2.6 B.2 Software Subscriptions (₱126,504)

| Line | Basis | Total |
|---|---|---:|
| ChatGPT Pro ($100 tier, 5× Plus), 1 seat, held by Lenard | $1,200/yr | ₱75,300 |
| Claude Pro × 3, annual billing ($200/seat/yr = $17/mo), held by Arnold, Daniel, Jade | $600/yr | ₱37,650 |
| 12% VAT on foreign digital services (RA 12023, since June 2025) | 12% × ₱112,950 | ₱13,554 |

Replaced: 7 seats × $240 = ₱102,816 (at 61.2) + ₱5,000 FX buffer.
Alternatives priced (with VAT, at 62.75): current 7 seats ₱118,070; Claude Max 5x + ChatGPT Pro $100 ₱168,672; Max 5x + 1-2 ChatGPT Plus ₱84-100k; Max 5x only ₱84k.

### 2.7 B.3 Cloud Infrastructure (₱68,492.88)

| Line | Basis | Total |
|---|---|---:|
| Render web service Standard (1 CPU, 2 GB) | 12 × $25 | ₱18,825.00 |
| Render PostgreSQL Basic-1gb (PITR included) | 12 × $19 | ₱14,307.00 |
| Database storage ~20 GB | 12 × $6 ($0.30/GB) | ₱4,518.00 |
| Bandwidth overage buffer | 12 × $5 ($0.15/GB) | ₱3,765.00 |
| Staging (Starter $7 + Basic-256mb $6) | 12 × $13 | ₱9,789.00 |
| Domain | $15 | ₱941.25 |
| Google Play developer registration | $25 one-time | ₱1,568.75 |
| 12% VAT on the USD lines above | 12% × ₱53,714 | ₱6,445.68 |
| FX buffer, 5% of all USD lines in B.2 and B.3 | 5% × ₱166,664 | ₱8,333.20 |

Replaced: Railway pilot 6 × $75 (₱27,540), AWS "Panay-wide" 6 × $300 (₱110,160), migration $100 (₱6,120), domain $15 (₱918) = ₱144,738, plus the AWS Activate note.
Current reality found in the repo: AqOne runs on Render's free tier (`render.yaml` plan: free); the free database `aqone-db` expires 15 Oct 2026, is deleted after 29 Oct, and the runbook says rotate by 8 Oct.
Not included (optional): Render Pro workspace $25/mo (₱18,360/yr at 61.2), Apple Developer $99/yr (₱6,059).
Hetzner was rejected for the grant year: roughly ₱15-25k/yr cheaper but no managed Postgres; Singapore is 20-40% above EU pricing, includes as little as 0.5 TB traffic on small plans, and charges €7.40/TB overage.
AWS Activate Founders now offers up to $5,000 (initial $1,000) but targets registered companies.
Render pricing reference: Starter $7, Standard $25, Pro $85; Postgres Basic-256mb $6, Basic-1gb $19, Standard-2gb $40.

### 2.8 B.4 Communication (₱48,581.80)

| Line | Basis | Total |
|---|---|---:|
| Semaphore SMS | 24,000 texts × ₱0.6272 (₱0.56 + 12% VAT); 1,000-3,000/month, midpoint 2,000 | ₱15,052.80 |
| Shore gateway data SIMs (Globe + Smart) | 2 × ₱12,000 | ₱24,000.00 |
| Pocket Wi-Fi units (estimate) | 2 × ₱2,000 | ₱4,000.00 |
| Smart Magic Data 988 + 749 + 649 (88 + 65 + 50 = 203 GB, no expiry) | | ₱2,386.00 |
| GOMO 449 × 7 (7 × 30 = 210 GB, no expiry) | | ₱3,143.00 |

Field data alternatives: monthly plan 2 SIMs × ₱1,000 × 12 = ₱24,000 + devices ₱4,000 = ₱28,000; first no-expiry version (176 + 60 GB) ₱6,874; chosen 200 GB per SIM ₱9,529.

### 2.9 B.5, B.6, EO (unchanged amounts)

| Line | Total |
|---|---:|
| Field travel: 48 trips × ₱1,250 (basis restated: no tolls; recompute with current pump prices) | ₱60,000 |
| Research dissemination travel | ₱30,000 |
| Pilot community outreach | ₱8,000 |
| Publication and documentation | ₱15,000 |
| 2 iPads × ₱35,000 | ₱70,000 |
| 2 MSI Thin 15 laptops × ₱54,995 (EO) | ₱109,990 |

### 2.10 Rejected or reverted budget changes

| Change | Figures | Outcome |
|---|---|---|
| Dell Pro Rugged 14 (Core Ultra 5, 16/512, 1,100-nit touch), IP53, MIL-STD-810H | $3,469.99 = ₱212,363.39; grand total ₱1,787,525.87 | Reverted: too expensive |
| Refurbished alternatives | Dell 5424/5420 Rugged $699-799 (≈₱43-49k); Toughbook CF-54 $549-799 (≈₱34-49k); MUNBYN IRT06 tablet $749 (≈₱46k); Dell 5414 on Ubuy ₱27,436 + shipping/VAT (≈₱31-35k landed, ≈₱37k with battery) | Not used; team will buy a laptop case instead |
| 2 × Samsung 990 EVO 1TB for the team's own Acer Nitro V 15 and Thunderobot | ₱18,359 for both | Removed: grant-funded upgrades to personally owned laptops |

### 2.11 Budget open items (not yet addressed)

- iPads (₱70,000): weakest justification; drop or reframe.
- Whether DOST allows a contingency line.
- Life vests and personal accident insurance for students at sea.
- Outreach ₱8,000 likely too low (meals, Aklanon materials).
- 2-3 test Android phones.
- Open-Meteo: free tier is non-commercial only; confirm eligibility.
- Faculty adviser honorarium and ASU indirect cost.
- Whether imported parts are priced with shipping, duties and VAT.
- Data Privacy Act compliance for fisherfolk data.
- Confirm ASU's 3D printing rate and canvass every "estimate" line.
- Firmware port from Heltec V3 (ESP32-S3) to RAK11200/RAK13300; docs still say Heltec.
- LGU/community counterpart (in kind, subject to MOA): host buoys, boat access, gateway sites, permit coordination, fishers' boats and chargers.

## 3. Reference data and sources

| Fact | Figure | Source |
|---|---|---|
| Region VI minimum wage (RBVI-29, eff. 19 Nov 2025) | ₱550 (>10 workers), ₱525 (≤10), ₱520 agri; domestic ₱6,500/mo | NWPC Region VI; Daily Guardian |
| BSP reference rate, 25 Sep 2026 | ₱62.75/USD | PesoHub |
| Semaphore SMS | ₱0.56/text ex-VAT | semaphore.co |
| Registered municipal boats (BoatR 2024) | 442,014 | Oceana Philippine Fisheries Assessment (2026) |
| Registered fisherfolk (FishR 2024) | 2,372,605 to 2,600,334 | Oceana (2026) |
| Municipal fishing vessels (2020) | 267,807; 30-47% unregistered in 2019 | Wikipedia, Municipal fisheries |
| Fisher poverty incidence | 26.2% (2018), 30.6% (2021) | Wikipedia (PSA) |
| Average municipal fisher income | ₱15,707.38/month (2018) | Wikipedia (PSA) |
| Total fisheries production value | ₱326.7B (2023); municipal capture ≈36.8% of value (2010-2023 avg) | Oceana (2026) |
| New Washington | 2nd income class; pop. 49,204 (2024); 16 barangays; revenue ₱203.2M; expenditure ₱193.3M (2024) | Wikipedia |
| LDRRMF | At least 5% of estimated regular revenue (≈₱10M for New Washington) | RA 10121 |
| Maritime accidents | 4,467 recorded by PCG, 2015-2020 | MDPI spatial analysis |
| 2026 energy crisis | Diesel >₱130/L by 24 Mar, >₱140 at peak; ended 30 Jun 2026 | Wikipedia |
| Pre-seed benchmarks (US-centric) | $250K-$1.5M rounds; $1M-$5M pre-money; 10-20% dilution; 12-18 months runway | IdeaProof |
| Claude plans | Pro $20/mo or $17/mo annual ($200/yr); Max 5x $100; Max 20x $200 | claude.com; Anthropic Help Center |
| ChatGPT plans | Go $8; Plus $20; Pro $100 (5× Plus); Pro $200 (20× Plus) | AI Pricing Guru |
| Smart Magic Data (no expiry) | 99/2GB, 149/3GB, 249/8GB, 349/16GB, 449/26GB, 549/38GB, 649/50GB, 749/65GB, 988/88GB | TeknoGadyet |
| GOMO (no expiry) | 249/15GB, 449/30GB | TeknoGadyet |
| Samsung 990 EVO 1TB retail | ₱6,079.20 (PCWorx), ₱9,500 (PC Express), both out of stock | Retailer pages |
| MSI Thin 15 B12U | 1 × M.2 Gen4 slot + 1 × 2.5" SATA bay | LaptopMedia |

## 4. Business model decisions

### 4.1 Cost vs price problem in `BUSINESS MODEL_AQONE.md`

| Item | Business model doc | New budget reality |
|---|---:|---:|
| Deployment price / cost | ₱500,000 price, ₱350,000 cost | Hardware alone ₱610,250 per municipality (3 × 64,150 + 20 × 17,150 + 2 × 37,400) |
| Additional buoy | ₱50,000 price | ₱64,150 cost |
| Annual service | ₱120,000 | Running cost ≈₱107,546 (hosting ₱68,493 + gateway SIMs ₱24,000 + SMS ₱15,053) |
| Fisher access fee | ₱0 | Pods are a per-boat cost (₱17,150) |

### 4.2 Decisions

- Customers: LGUs, fisherfolk cooperatives, insurers (PCIC and microinsurers), later passenger vessels.
- Sequence: beachhead (Aklan fishers via LGU + co-ops), replicate nationally, insurers after pilot data, passenger motorbancas before large ferries.
- Framing: "municipal waters nationwide" (15 km legal boundary), not "national waters".
- Setup at break-even (≈₱700k+ with labor), margin from recurring software, hosting and maintenance.
- Lock-in through software licensing (LGU owns hardware or leases it; software licensed, never sold), 3-year terms matching LGU terms, and direct contracting for a proprietary system.
- Payment: LGU lease ("hardware as a service") by default; outright purchase via LandBank/DBP loan as an option; installments for co-ops directly or via MFI/rural banks.
- Lease example: ₱610k hardware over 3 years ≈ ₱203k/yr before financing, service and margin.
- Programmatic ads rejected (≈₱0.5M/yr at best with 10,000 users; ads need internet; privacy and optics).
- Local sponsorships adopted: ₱60,000 per municipality per year (2 sponsors × ₱2,500/month), 15% selling cost, never on SOS or alert screens.
- Safety ethics: grace period and data export if an LGU stops paying.

### 4.3 Deal-breakers to settle before taking investment

- IP ownership: DOST-funded work through ASU likely belongs to ASU (RA 10055); a license or spin-off agreement is needed.
- Legal entity: SEC-registered corporation required to issue shares; decide AqOne vs under Better Future.
- Cap table and founder vesting (4 years, 1-year cliff).
- No double funding between DOST and investors; royalties only from commercial revenue.
- Data Privacy Act consent for any insurer data use.
- Investment terms at a competition are illustrative; finalize privately (SEC rules on public offers).

## 5. Investor model

### 5.1 Earlier iterations

**One-shot ₱7.5M for 20% (₱30M pre-money), equity only.**
Peak cash need: low ₱7.4M, base ₱4.9M.

| | Low | Base | High |
|---|---:|---:|---:|
| Paying municipalities Y5 | 24 | 47 | 76 |
| Active pods Y5 | 2,246 | 4,275 | 6,902 |
| Revenue Y5 | ₱34.8M | ₱68.6M | ₱110.2M |
| Recurring revenue Y5 | ₱11.1M | ₱21.7M | ₱34.8M |
| EBITDA Y5 | ₱5.3M | ₱22.8M | ₱44.4M |
| Exit value (2×/3×/4× revenue) | ₱70M | ₱206M | ₱441M |
| Investor multiple | 1.5× | 4.4× | 9.4× |
| IRR | ~8% | ~34% | ~57% |

Rejected as hard to defend for a pre-revenue student team.
Staged alternative discussed: ₱3M for 12-15% (₱17-22M pre-money) to reach 3 paying municipalities and ~150 pods.

**Equity-only tranches ₱3M (₱20M pre, ~13%) + ₱3M (₱40M pre, ~7%), ~19% total, ~15% after dilution:** 1.8× / 5.2× / ~11×; IRR ~18% / ~59% / ~95%.

**Royalty comparison on ₱6M (full rates from Y2):**

| Option | Terms | Low | Base | High |
|---|---|---|---|---|
| A. Equity only | ~19% | 1.8× (IRR 18%) | 5.2× (59%) | 11.2× (96%) |
| B. Royalty only | ₱1,500/pod + ₱25,000/municipality-yr, cap 2× (₱12M) | 0.75× (-10%) | 1.4× (13%) | 2.0× capped (29%) |
| C. Hybrid | 10% equity + ₱750/pod + ₱12,500/municipality-yr, cap 1× (₱6M) | 1.3× (8%) | 3.4× (45%) | 6.8× (77%) |

Option B base payouts: Y2 ₱0.3M, Y3 ₱1.07M, Y4 ₱2.46M, Y5 ₱4.72M; royalties cost the company about 7% of revenue.

**Hybrid tranched ₱3M (6%) + ₱3M (4%), before the fix:** 1.3× (IRR 9%) / 3.4× (43%) / 6.7× (75%); royalties ₱2.2M / ₱4.2M / ₱6.0M; lowest cash with investor money: low -₱2.44M, base +₱0.49M.

### 5.2 Final deal terms

| Term | Tranche 1 | Tranche 2 |
|---|---:|---:|
| Paid at | End of Y1 | End of Y2 |
| Amount | ₱3,000,000 | ₱5,000,000 |
| Post-money valuation | ₱50,000,000 | ₱75,000,000 |
| Equity issued | 6.00% | 6.67% |

- Total commitment ₱8,000,000.
- Ownership after both tranches 12.27%; after a later 20% dilution 9.81%.
- Royalty ₱750 per pod sold + ₱12,500 per paying municipality per year.
- Royalty rates scale with money paid in: half rates in Y2, full rates from Y3.
- Royalty cap 1.0× money paid in (₱8M); equity stays after the cap.
- Y1 is the DOST pilot: no investor money, no returns.

Milestones:
- Before any tranche: DOST grant approved; SEC registration; IP license or assignment with ASU; term sheet signed.
- Milestone 1 (end Y1, unlocks ₱3M): pilot live with 3 buoy nodes, 2 gateways, 18+ pods; uptime ≥95% over the last 3 months; ≥95% of SOS drill messages delivered; agreed number of active fishers; paid Y2 agreement or LOI from New Washington; measured unit costs.
- Milestone 2 (end Y2, unlocks ₱5M): 3 paying municipalities; 150+ active pods; at least 1 co-op purchase agreement; pilot LGU renews; deployment gross margin ≥35%.
- If a milestone is missed: investor may decline the next tranche and keeps what was issued; if DOST is delayed or rejected, the investor may fund the pilot directly at an agreed valuation.

### 5.3 Model inputs

| Input | Value |
|---|---:|
| Buoy relay node / nodes per municipality | ₱64,150 / 3 |
| Shore gateway / gateways per municipality | ₱37,400 / 2 |
| Installation, commissioning, training per municipality | ₱60,000 |
| Infrastructure per new municipality (company-owned) | ₱327,250 before decline |
| Boat pod cost | ₱17,150 |
| Recurring cost per active municipality per year | ₱90,000 |
| Service cost per active pod per year | ₱300 |
| Infrastructure cost decline per year | 7% |
| Pod cost decline per year | 12% |
| LGU annual subscription | ₱350,000 |
| Pod price | ₱19,900 |
| Pod service fee per year | ₱1,200 |
| Sponsorship per municipality per year / selling cost | ₱60,000 / 15% |
| Pods sold per active municipality per year (from Y2) | 50 |
| Municipality cancellation rate | 10% |
| Later round dilution before exit | 20% |
| New paying municipalities, base (Y1-Y5) | 0, 3, 8, 15, 25 |
| Company fixed costs, base (Y1-Y5) | ₱800,000; ₱3,500,000; ₱6,000,000; ₱10,000,000; ₱16,000,000 |
| Scenario pace / exit multiple | Low 0.5× / 2×; Base 1.0× / 3×; High 1.6× / 4× |

Fixed costs scale by (0.8 + 0.2 × pace).
Exit value = Y5 revenue × exit multiple.
The ₱350,000 fee is ≈3.5% of a ≈₱10M LDRRMF; the ₱19,900 pod is ≈1.3 months of fisher income.

### 5.4 Final outcomes

| Metric | Low | Base | High |
|---|---:|---:|---:|
| Paying municipalities Y5 | 24.9 | 47.2 | 75.8 |
| Active pods Y5 | 2,296 | 4,275 | 6,902 |
| Revenue Y5 | ₱37,738,880 | ₱71,392,670 | ₱114,751,250 |
| EBITDA Y5 | ₱7,380,633 | ₱25,189,137 | ₱48,289,911 |
| Deepest cash need without investor money | -₱7,352,073 | -₱4,793,999 | -₱3,449,463 |
| Lowest cash with investor money | ₱647,927 | ₱2,200,000 | ₱2,104,000 |
| Royalties to investor by Y5 | ₱2,233,475 | ₱4,181,213 | ₱6,745,563 |
| Equity value at exit | ₱7,406,884 | ₱21,018,002 | ₱45,043,691 |
| **Investor money multiple** | **1.21×** | **3.15×** | **6.47×** |
| **Investor IRR** | **5.9%** | **41.8%** | **75.5%** |

Note: "lowest cash with investor money" counts Tranche 1 at the end of Y1, but the ≈₱800k of Y1 company costs come before it arrives.

### 5.5 Base case by year

| Base | Y1 | Y2 | Y3 | Y4 | Y5 |
|---|---:|---:|---:|---:|---:|
| New municipalities | 0 | 3 | 8 | 15 | 25 |
| Active municipalities | 0 | 3 | 10.7 | 24.63 | 47.17 |
| Pods sold | 0 | 150 | 535 | 1,232 | 2,358 |
| Active pods | 0 | 150 | 685 | 1,917 | 4,275 |
| LGU subscriptions | 0 | ₱1,050,000 | ₱3,745,000 | ₱8,620,500 | ₱16,508,450 |
| Pod sales | 0 | ₱2,985,000 | ₱10,646,500 | ₱24,516,800 | ₱46,924,200 |
| Pod service | 0 | ₱180,000 | ₱822,000 | ₱2,300,400 | ₱5,130,000 |
| Sponsorships | 0 | ₱180,000 | ₱642,000 | ₱1,477,800 | ₱2,830,020 |
| Total revenue | 0 | ₱4,395,000 | ₱15,855,500 | ₱36,915,500 | ₱71,392,670 |
| Gross margin | - | 40.7% | 47.2% | 52.8% | 57.7% |
| Fixed costs | ₱800,000 | ₱3,500,000 | ₱6,000,000 | ₱10,000,000 | ₱16,000,000 |
| EBITDA | -₱800,000 | -₱1,710,800 | ₱1,485,386 | ₱9,503,344 | ₱25,189,137 |
| Equipment capex | 0 | ₱913,028 | ₱2,264,308 | ₱3,948,387 | ₱6,120,001 |
| Royalty paid | 0 | ₱56,250 | ₱535,000 | ₱1,231,875 | ₱2,358,088 |
| Cash after investor money | ₱2,200,000 | ₱4,519,923 | ₱3,206,001 | ₱7,529,083 | ₱24,240,131 |

Low case revenue by year: Y2 ₱2,930,000; Y3 ₱8,617,000; Y4 ₱19,835,300; Y5 ₱37,738,880.
High case revenue by year: Y2 ₱7,325,000; Y3 ₱25,937,500; Y4 ₱59,594,300; Y5 ₱114,751,250.

### 5.6 Stress tests (final model, one change at a time)

| Test | Lowest cash with investor money (Low / Base / High) | Multiple (Low / Base / High) | IRR (Low / Base / High) | Royalties by Y5 |
|---|---|---|---|---|
| As built | ₱0.65M / ₱2.20M / ₱2.10M | 1.21× / 3.15× / 6.47× | 6% / 42% / 76% | ₱2.2M / ₱4.2M / ₱6.7M |
| LGU fee ₱250k | -₱1.45M / ₱1.84M / ₱2.10M | 1.14× / 2.98× / 6.10× | 4% / 39% / 73% | ₱2.2M / ₱4.2M / ₱6.7M |
| Half pod adoption (25/yr) | -₱7.19M / -₱0.21M / ₱1.77M | 0.76× / 2.00× / 4.10× | -8% / 23% / 53% | ₱1.4M / ₱2.6M / ₱4.2M |
| Cancellations 20%/yr | -₱0.02M / ₱2.20M / ₱2.10M | 1.12× / 2.93× / 6.00× | 3% / 39% / 72% | ₱2.1M / ₱3.9M / ₱6.3M |
| Pod cost never falls | -₱9.88M / -₱1.58M / ₱1.62M | 1.21× / 3.15× / 6.47× | 6% / 42% / 76% | ₱2.2M / ₱4.2M / ₱6.7M |
| Fee ₱250k + half pods | -₱11.78M / -₱4.43M / -₱1.28M | 0.70× / 1.82× / 3.73× | -10% / 20% / 49% | ₱1.4M / ₱2.6M / ₱4.2M |

Takeaway: the model tolerates a lower LGU fee and higher cancellations, but pod adoption and pod cost are the weak points.
Tranche 2 at ₱6M was also tested: low-case lowest cash ₱1.65M, multiples 1.16× / 3.04× / 6.27×, so ₱5M was kept.

### 5.7 Safety levers discussed (not yet in the model)

For the company:
- Tie hiring and fixed-cost steps to milestones.
- Build pods only against paid orders (co-op or MFI financing).
- Minimum pod margin; if cost does not fall, raise price or secure an LGU/insurer co-pay.
- Royalty pause when cash falls below 3 months of costs, with carry-forward.

For investors:
- 1× liquidation preference.
- Founder vesting, 4 years with a 1-year cliff.
- Independent milestone verification (DOST/ASU reports), quarterly reporting, board observer seat.
- Company-owned leased equipment as recoverable assets.

Not captured by the yearly model: LGU payment delays of 30-90 days, Y1 company costs before Tranche 1, and IP ownership.

## 6. Next steps

1. Rotate or upgrade the Render free database before 8 Oct 2026.
2. Replace the Google Sheet contents via Import > Replace spreadsheet; tighten sharing; clean up old copies.
3. Chase an LOI from New Washington and request BFAR FishR/BoatR data for the municipality.
4. Settle the ASU IP question and the company entity before pitching investors.
5. Write a new business model doc from section 4 (the old `BUSINESS MODEL_AQONE.md` was archived on 29 Sep 2026).
6. Run your own stress tests on `AqOne_Investor_Model.xlsx` (inputs are the yellow cells).
