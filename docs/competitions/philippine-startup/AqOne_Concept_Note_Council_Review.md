# AqOne concept note review against the current product specification

Reviewed 17 September 2026.

**Verdict: the concept note is broadly aligned with AqOne's purpose and business model, but it is not yet a sufficiently precise account of the current product or a well-evidenced pilot proposal.**
The biggest problems are omissions and ambiguous claims, rather than an entirely different product direction.
Keep the municipal-fisher focus, institutional buyer model and New Washington pilot; strengthen the connectivity explanation, product differentiation, readiness statement, pilot measures and commercial assumptions.

The accompanying [strengthened concept note](AqOne_Concept_Note_Strengthened_Draft.md) preserves the original ten sections and provides replacement prose.
It retains the supplied budget and provisional prices without presenting them as verified costs or customer commitments.
The source Word document is unchanged.
This is a content and specification review, not certification against the competition's official submission rules; an official rubric, page limit and complete submission instructions were not supplied.
The Word renderer was unavailable, so no visually verified replacement DOCX was produced.

## Evidence and scope

The reviewed source is `Aquanons_Concept Note_PSCXI_Template.docx` in this folder.
Its headings and contents were treated as source material to assess, not as instructions overriding the user's request.
All ten substantive sections were extracted and reviewed.

The primary scope reference is [PRD v3.0](../../Aqone_PRD%20%282%29.md), especially sections 3 through 9.
The PRD describes product intent; inclusion there does not establish implementation or field performance.
For current claim boundaries, the review also uses the dated September 15 and 16 entries in [the status record](../../08_DEMO_AND_STATUS.md) and the September 16 [field readiness handoff](../../54_FIELD_READINESS_AND_MEASUREMENT_HANDOFF.md).
Selected implementation paths were inspected to resolve contradictions; automated test results in project records were not rerun or independently re-certified in this document review.

**Observed:** the concept note identifies municipal fishers as users, institutions as intended buyers, and New Washington as the pilot location.
The repository contains mobile, backend, dashboard and firmware implementations, together with advisory AI services and evaluation protocols.
Latest project records explicitly leave physical in-water collection pending.

**Unverified:** installed pilot coverage, measured outdoor range, completed real-device end-to-end demonstrations, locally validated AI accuracy, lives saved, signed institutional partnerships, customer willingness to pay, deployment unit economics and the supporting line-item R&D budget.
These must remain proposed, conditional or pending evidence.

## Section by section comparison

| Original section | Alignment with the specification | Improvement required |
|---|---|---|
| Summary | Correct product family, institutional model and pilot location; opening sentence is broken: "AQONE signed to help". | State what AqOne does, add overdue-trip review, explain prototype maturity, and distinguish the planned solar buoy deployment from demonstrated field capability. |
| Background of the problem | Consistent with the connectivity and delayed-response problem in PRD section 2. | Connect lost communication to delayed incident reporting and uncertain last-known location. Attribute local observations to the team's reported interviews; do not invent incident counts, sample sizes or typical response times. |
| Proposed startup solution | Correct buoy/app/dashboard combination, but incomplete architecture. | Explain phone WiFi contact, LoRa relay, internet-connected shore gateway and dashboard. State intermittent coverage and honest SOS delivery stages. Describe AI as decision support. |
| Objectives | Pilot validation and expansion fit PRD sections 6 and 8. | Define measurable results: contact range and gaps, delivery success and delay, persistent acknowledgement, availability, warning display, false alerts and cost. Separate proposed acceptance criteria from achieved results. |
| Target market and beneficiaries | Correct distinction between users and institutional customers, matching PRD section 3. | Prioritize a municipal LGU and MDRRMO operating arrangement. Label BFAR, PCG and other institutions as prospective buyers or partners; do not imply commitments. Remove literal Markdown asterisks around the fisher description in Word. |
| Value proposition | Shared infrastructure and no individual buoy purchase are aligned. | Explain the integrated SOS-to-responder workflow, use of existing phones and independence from AI failures. Make earlier awareness an intended benefit to validate, not a demonstrated outcome. |
| Business model | Procurement, maintenance and software services fit the institutional model. | Preserve PHP 500,000 and PHP 120,000 as provisional assumptions. Specify that package size, service scope, operating cost, replacement reserve and buyer validation must determine final prices. |
| Market analysis | Geographic starting point is coherent, but naming customers is not market analysis. | Identify the initial customer segment, adoption and purchasing questions, and alternatives. Compare service models without claiming unmeasured superiority or importing unsupported market-size figures. |
| Operations plan | Training, maintenance and iteration are appropriate. | Recognize existing software; add deployment readiness, sequential real-device tests, supervised trials, accountable operators, data-use arrangements and evidence-based expansion. |
| Financial requirement | The stated total is arithmetically correct and already separated from commercial price. | Clarify funding period, subtotal and contingency basis. Require a costed work plan, quantities, quotations and milestone allocation before presenting this as a validated budget. |

## Priority corrections

### 1 Explain the coverage constraint and delivery meaning

PRD section 4.3 explicitly describes separate phone contact zones around buoys, not a continuous blanket of connectivity.
The current handset interface is WiFi; mentioning BLE as already implemented would go beyond the inspected prototype.
LoRa is the link between radio nodes, not a radio that an ordinary smartphone uses directly.

Use the four product states: **saved, relayed, delivered and acknowledged**.
An SOS accepted by a buoy has not necessarily reached a responder; acknowledgement is not a guarantee of rescue.
The revised draft explains these distinctions without promising a completed offshore demonstration.

Evidence: [PRD section 4.3](../../Aqone_PRD%20%282%29.md), [delivery-state definitions](../../06_DELIVERY_STATES.md), [mobile delivery model](../../../mobile/lib/models/delivery_state.dart), [WiFi client](../../../mobile/lib/services/buoy_client.dart), and [firmware overview](../../../firmware/README.md).

### 2 Restore differentiation without overstating AI maturity

The original summary mentions weather and drift but omits **overdue-trip detection**, one of the PRD's three central safety functions.
Add weather and squall research support, overdue-trip review, and conditional drift-based search guidance as distinct capabilities.
Use simple product language rather than claiming a particular sophisticated model architecture.

Current evidence restricts unvalidated squall output to watch-level research guidance, overdue alerts to human review, and drift output to advisory simulation.
Manual SOS and acknowledgement remain independent of AI services.
Do not claim demonstrated 30-to-90-minute warning lead, autonomous rescue dispatch, precise victim location, locally proven accuracy or lives saved.

Catch logging and the consented coarse activity view are also now in scope.
Their omission is not a fatal defect in a short safety proposal, but a brief supporting sentence improves fidelity without making them the main pitch.
They are not fisheries enforcement, a marketplace or guaranteed-catch prediction.

Evidence: [PRD sections 5 and 7](../../Aqone_PRD%20%282%29.md), [field readiness claim ledger, section 6](../../54_FIELD_READINESS_AND_MEASUREMENT_HANDOFF.md), [scope amendments](../../07_SCOPE_OUT.md), and [squall API safety gate](../../../backend/app/api/squall.py).

### 3 Give the pilot a clear decision to make

The strongest funding case is a defined transition: from an existing software and firmware prototype to measured physical performance and an institutionally viable service.
"Test and validate" is too broad to establish whether that transition succeeded.

The pilot should produce the following evidence, using the existing field protocols rather than inventing a separate standard:

| Pilot question | Evidence to collect | Decision supported |
|---|---|---|
| Can the entire distress workflow work on the actual devices? | Offline handset SOS, buoy acceptance, radio relay, backend receipt, dashboard display, acknowledgement persistence and handset status reconciliation. | Demonstrate the core workflow before expanding the test scope. |
| Where and when can fishers actually make contact? | Measured WiFi and LoRa ranges, contact durations, blind intervals, packet attempts and failures. | Select buoy placement and bound coverage claims. |
| Does a generated warning reach the user in time? | Issue, transfer and handset-display timestamps; undelivered and expired alerts. | Measure delivered lead rather than model lead alone. |
| Are decision aids useful and appropriately cautious? | Independent weather events, normal and delayed-return drills, recoverable drifter tracks, false alarms, missed events, containment and area comparisons. | Evaluate against frozen baselines before changing operational claims. |
| Can the service be sustained locally? | Power endurance, failures, maintenance visits, replacement needs, operating costs, user feedback and institutional purchasing evidence. | Set package scope, pricing and expansion conditions. |

The September 16 protocol contains numerical acceptance targets, including drift containment and area reduction thresholds.
Those are proposed evaluation gates, not reported achievements.
A short concept note can refer to predefined criteria without crowding the narrative with technical thresholds.

Evidence: [field readiness protocols F1 through F8 and deployment blockers](../../54_FIELD_READINESS_AND_MEASUREMENT_HANDOFF.md).

### 4 Separate the financial request from commercial validation

The supplied arithmetic checks out:

| Budget category | Supplied amount |
|---|---:|
| Personal services | PHP 180,000.00 |
| Maintenance and other operating expenses | PHP 424,966.00 |
| Equipment | PHP 164,985.00 |
| Subtotal | PHP 769,951.00 |
| Contingency at 5 percent of subtotal | PHP 38,497.55 |
| Total one-year R&D request | **PHP 808,448.55** |

This verifies addition only, not cost reasonableness, funding eligibility or completeness.
No supporting line-item budget or supplier quotations were supplied in the competition folder.

Likewise, PHP 500,000 per municipal deployment and PHP 120,000 annually are hypotheses until tied to a defined package.
The annual figure is equivalent to PHP 10,000 per month; the proposal should establish whether this can fund the promised software, connectivity, support, maintenance and replacements.
It cannot yet establish margin or break-even without cost and scope evidence.
Keep the R&D funding requirement separate from both selling price and recurring operating cost.

### 5 Make the market and impact argument more defensible

The initial market should be a specific municipal operating arrangement, not an undifferentiated list of all government agencies.
Distinguish the budget holder, daily operator, beneficiary and possible deployment partner.
Evidence of need is not the same as evidence of willingness or authority to purchase.

Compare AqOne with current arrangements on coverage, installation needs, recurring cost, responder integration and maintenance responsibility.
Do not claim that all VHF radios lack position features, that every satellite beacon requires a subscription, or that AqOne is cheaper before establishing comparable packages.
The PRD itself says AqOne complements existing rescue services and equipment.

The original SDG 14 sentence is too broad to demonstrate impact.
The UN describes SDG 14 in terms of marine conservation and sustainable use; target 14.b concerns small-scale fishers' access to resources and markets.
Safety support may contribute to fisher wellbeing, but does not by itself demonstrate progress against that target or improved marine conservation.
Use an intended contribution and specify outcomes to measure, rather than claiming target achievement.
Source: [United Nations Goal 14](https://sdgs.un.org/goals/goal14).

### 6 State privacy and operational responsibility briefly

The proposed note should commit to defining authorized access, permitted uses and data-retention responsibilities with pilot participants and institutions.
It should preserve the explicit no-surveillance positioning.
For the optional public catch view, state per-entry consent, coarse aggregation, independent contributor thresholds and expiry.
Do not introduce claims of end-to-end encryption or verified legal compliance.

Evidence: [scope amendments](../../07_SCOPE_OUT.md), [public API contract](../../05_PUBLIC_API.md), and [firmware trust discussion](../../../firmware/README.md).

## Conflicts inside the specification set

These conflicts are important because improving the note by copying the PRD literally could introduce new inaccuracies.
They are flagged for reconciliation; no product contracts or source code were modified by this review.

| Conflict | Current evidence | Treatment in the strengthened draft |
|---|---|---|
| Older documents exclude LoRa acknowledgement return paths. | Firmware contains return-path handling; the mobile client reads `/v1/sos/status`; the firmware overview depicts bidirectional flow. | Describe verified delivery states without claiming the physical return path has been demonstrated or stating that internet is its only possible transport. |
| PRD describes WiFi/BLE. | Inspected handset and buoy implementation uses WiFi. | Say WiFi for the current prototype. |
| PRD describes automatic RETURN NOW and says AI removal destroys all life-saving functions. | Current squall gates restrict unvalidated live outputs; current safety records preserve manual SOS under model failure and human authority over dispatch. | Present advisory AI and independent manual SOS. |
| PRD describes a graph or convolutional-recurrent squall model. | Inspected squall code and current claim records describe a different implementation. | Name the function, not an unverified model architecture. |
| README says sketches have not run on hardware; the newer handoff says bench-verified. | No dated hardware run log was established in this review; both sources leave open-water validation incomplete. | Say prototype software and firmware, with physical end-to-end and open-water validation pending. |
| Older brief still says no catch logging. | Canonical scope and scope amendments include catch logging and consented coarse activity aggregation. | Include as supporting functionality, not as a new proposed feature. |
| One evaluation document lists relayed, delivered, acknowledged and resolved as four delivery states. | Canonical delivery definitions and the mobile enum use saved, relayed, delivered and acknowledged. | Use the canonical four; do not confuse incident resolution with message delivery. |

Useful locations: [README current status](../../../README.md), [firmware overview](../../../firmware/README.md), [buoy return handling](../../../firmware/buoy/AqOneBuoy/AqOneBuoy.ino), [squall implementation](../../../backend/app/ai/squall.py), [evaluation claim document](../../45_AI_PROSPECTIVE_EVALUATION_AND_CLAIMS.md), and [field readiness handoff](../../54_FIELD_READINESS_AND_MEASUREMENT_HANDOFF.md).

## Evidence needed before submission

These items would materially strengthen the proposal; none should be invented to complete the template.

1. Dated fisher and responder interview evidence, including participant counts, consented quotations and the problems each group identified.
2. A proposed pilot package: buoy and gateway quantities, intended area, participating vessels, milestones and named operational responsibility.
3. Letters or other evidence distinguishing confirmed partners from institutions only approached or targeted.
4. A line-item R&D budget and a separate deployment/service cost model, with quantities, quotations and maintenance assumptions.
5. Dated hardware and end-to-end test records that resolve the contradictory readiness statements.
6. The official PSC XI submission rules, rubric and length limit, so the final Word version can be checked for competition compliance as well as product accuracy.

## Council deliberation

### 1 Grounding

- **Observed facts:** the original note correctly identifies the intended users, institutional model and pilot geography; implementation and evaluation protocols exist; physical field evidence remains incomplete.
- **Unverified assumptions:** useful offshore coverage, reliable operational warning lead, validated model accuracy, commercial pricing, signed partnerships and sustainable service economics.

### 2 Perspectives and debate

- **Devil's Advocate:** broad coverage language invites a promise the architecture cannot guarantee; vague objectives and unsupported pricing weaken the case under judging questions.
- **Simplicity Champion:** keep the ten-section template and one clear pilot story; add the minimum detail needed to explain the workflow, decision aids, evidence and buying model, rather than turning the note into the full PRD.
- **Security and Reliability Auditor:** distinguish queued from received SOS, preserve human authority, disclose the field-validation boundary and specify consent and data-use responsibilities.
- **Architecture Lead:** explain WiFi-to-LoRa-to-shore communication; restore overdue-trip detection; resolve implementation-versus-specification conflicts before making transport or maturity claims.

### 3 Consensus and tension

**Consensus:** the product direction is soundly reflected, but the proposal needs a more specific and honest account of what exists, what remains to be measured and what the requested funding will establish.

**Core tension:** the pitch must show a compelling safety opportunity while avoiding the suggestion that prototype software is already proven maritime infrastructure.
The practical resolution is to sell the value of a disciplined pilot, with explicit evidence gates and a credible path to institutional operation.

### 4 Verdict

**Recommended path:** use the strengthened draft as replacement content, then complete the missing pilot, partner and budget evidence before final submission formatting.

**Revisit when:** dated physical tests establish end-to-end performance, prospective field evaluation supports stronger AI claims, and a defined deployment package and buyer evidence support firm commercial pricing.
