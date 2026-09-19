# AqOne Architecture & Data-Flow Artifacts

This directory contains presentation decks, technical architecture diagrams, and specification documents depicting the end-to-end data flow, system topology, and AI decision-support boundaries for Project AqOne.

## Artifact Catalog

| Artifact File | Format | Description | Target Audience |
|---|---|---|---|
| [`architecture/AqOne_Aggregated_Technical_Architecture.docx`](architecture/AqOne_Aggregated_Technical_Architecture.docx) | Word DOCX (Landscape 22"x14.7") | High-resolution single-page technical architecture document. Embeds the aggregated technical flowchart with complete end-to-end swimlanes. | Technical evaluators, judges, print / PDF export |
| [`architecture/AqOne_Aggregated_Technical_Architecture.pdf`](architecture/AqOne_Aggregated_Technical_Architecture.pdf) | Adobe PDF (Landscape) | Direct standalone view of the single-page aggregated technical architecture for instant review without Office software. | All reviewers, web preview |
| [`architecture/AqOne_Aggregated_Technical_Architecture_Editable.pptx`](architecture/AqOne_Aggregated_Technical_Architecture_Editable.pptx) | PowerPoint PPTX (5200x3400 pt) | Single-slide comprehensive aggregated technical architecture built entirely from native, editable shapes, connectors, and text boxes. | Engineers, designers, pitch editors |
| [`architecture/AqOne_Editable_Architecture_Flowchart_v6_Traceable.pptx`](architecture/AqOne_Editable_Architecture_Flowchart_v6_Traceable.pptx) | PowerPoint PPTX (3 slides) | Multi-slide traceable architecture flowchart decomposing individual subsystem transitions and edge cases across distinct slides. | Deep-dive presentations, design reviews |
| [`archive/architecture/AqOne_Editable_Architecture_Flowchart_v*.pptx`](archive/architecture/) | PowerPoint PPTX | Earlier revision milestones (v1–v5) preserved for audit trail and iteration history. | Archive |
| [`competitions/enactus/AqOne_Enactus_Endorsement_Letter.docx`](competitions/enactus/AqOne_Enactus_Endorsement_Letter.docx) | Word DOCX | Official HEI head endorsement letter generated via [`tools/documents/create_endorsement_letter.py`](../tools/documents/create_endorsement_letter.py). | Competition reviewers |
| [`competitions/technical-profile/AqOne_Technical_Profile_Aquanons-1.docx`](competitions/technical-profile/AqOne_Technical_Profile_Aquanons-1.docx) | Word DOCX | Project technical profile submission document. | Competition reviewers |

---

## 5 Core Data Flows Covered

The aggregated technical architecture depicts five decoupled, independent data flows:

1. **Emergency SOS Lane (Red):** Manual distress path from fisherman (vessel phone outbox or physical pod button) across local SoftAP WiFi, signed LoRa 915 MHz, tall shore gateway, FastAPI ingest, PostgreSQL persistence, and MDRRMO SSE dashboard feed with responder acknowledge loop. Fully independent of AI models.
2. **Environmental Warning Lane (Purple):** Marine pressure, tide, current, and meteorological telemetry normalized and checked for freshness. Feeds squall nowcast and localized danger-zone GBDT models. Official LGU/PAGASA warnings strictly take precedence over model advisories.
3. **Trip Anomaly Lane (Indigo):** Departure and return tracking using causal historical filtering. Evaluates deviations against per-vessel baselines while routing sparse-baseline trips to a cold-start review queue. Alerts MDRRMO responders for manual radio/call confirmation before escalating.
4. **Drift and Search Decision Support Lane (Blue):** Triggered strictly upon confirmed emergency incidents. Ingests last known datum and ocean forcing fields, executes Monte Carlo leeway particle simulations, ranks search sectors (50%, 75%, 95% probability contours), and updates Bayesian posteriors upon negative search findings.
5. **Consented Catch Activity Lane (Green):** Voluntary fisheries catch logging with explicit consent. Stored privately and subjected to k-anonymity and coarse spatiotemporal grid aggregation. Strictly isolated from LoRa emergency mesh bandwidth.

---

## Non-Negotiable Architecture Principles

- **Manual SOS Never Depends on AI:** The core distress signaling pathway operates entirely on deterministic hardware, store-and-forward queues, and authenticated network protocols.
- **Honest Delivery States:** Every layer shows only proven delivery states (`SAVED` ➔ `RELAYED` ➔ `DELIVERED` ➔ `ACKNOWLEDGED`). Unacknowledged messages never fabricate false confirmations.
- **Human-in-the-Loop:** AI models (squall nowcasting, danger-zone rating, trip anomaly, drift prediction) provide decision support to authorized operators; they never autonomously retask responders or trigger distress alarms.
- **Privacy by Design:** Catch locations are never transmitted over open radio channels and are only exposed as coarse aggregated heatmaps after meeting privacy thresholds.

---

## Build & Generation Scripts

Source code and generator scripts used to produce these artifacts reside in [`tools/architecture/`](../tools/architecture/):

- `build_aggregated_architecture.mjs`: Node.js script using `@oai/artifact-tool` to synthesize `AqOne_Aggregated_Technical_Architecture_Editable.pptx` and `aqone-aggregated-architecture.png`.
- `build_architecture_docx.py`: Python script using `python-docx` to package the high-resolution architecture graphic into `AqOne_Aggregated_Technical_Architecture.docx`.
- `build_flowchart.mjs` & `build_traceable_flowchart.mjs`: Generators for the multi-slide traceable flowcharts (`v1`–`v6`).

To inspect full technical contracts and architecture specifications, consult [`docs/56_TECHNICAL_ARCHITECTURE_AND_DATA_FLOW_SPEC.md`](../docs/56_TECHNICAL_ARCHITECTURE_AND_DATA_FLOW_SPEC.md).
