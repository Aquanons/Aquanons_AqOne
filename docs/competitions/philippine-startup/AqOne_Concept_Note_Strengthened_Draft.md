# Philippine Startup Challenge XI

**Team:** Aquanons  
**Product:** AqOne  
**Document:** Concept Note

## Summary

AqOne is a shared maritime communication and safety-support system for municipal and small-scale fishers beyond cellular coverage.
It combines a planned network of solar-powered LoRa buoys, a smartphone application and an operations dashboard.
When a phone enters a buoy's WiFi range, queued messages and SOS alerts can pass through the LoRa network to an internet-connected shore gateway and authorized responders.
Coverage depends on contact with deployed buoys; it is not continuous across all fishing grounds.

The software and firmware prototype supports a core SOS workflow alongside weather information, overdue-trip review and drift-based search guidance.
These decision aids support human responders, while manual SOS operates independently of the AI modules.
Physical end-to-end performance, open-water coverage and local model accuracy remain to be established through field validation.

AqOne follows an institutional business model: LGUs and relevant public-safety or fisheries institutions are prospective customers, while fishers are the primary users.
The proposed New Washington, Aklan pilot will establish technical performance, user needs, deployment and operating costs, and the conditions for a repeatable municipal service.

## Background of the problem

Municipal fishers depend on timely communication when weather deteriorates, engines fail or a vessel becomes overdue.
When cellular service is unavailable, a phone may be unable to deliver a distress message or reassure a family that a delayed boat is safe.
Responders can consequently receive an alarm late and begin searching with limited information about the vessel's last known location and time of contact.

The team's reported field interviews in New Washington identified loss of cellular contact at sea as a central concern.
The pilot will document the locations, duration and operational consequences of these gaps rather than assume uniform conditions across the municipality.
AqOne addresses this need by testing shared offshore communication points linked to a local response workflow.
It is intended to complement existing rescue services and safety equipment.

## Proposed startup solution

AqOne connects an existing smartphone to a nearby buoy over WiFi.
The buoy stores and forwards short messages over LoRa toward a shore gateway, which uses internet connectivity to reach the backend and responder dashboard.
Messages can remain queued when a link is unavailable.
The app distinguishes an SOS saved on the phone, accepted by a buoy, delivered to the backend and acknowledged by a responder, so users are not shown a later delivery state without confirmation.

The dashboard brings together distress alerts, vessel information, network status and decision-support tools.
Weather monitoring and squall research alerts support risk awareness; overdue-trip review highlights cases for verification; drift simulation suggests search areas for responder assessment.
Unvalidated squall outputs remain watch-level research guidance, and the system does not autonomously dispatch rescue assets.
These capabilities will be evaluated using local observations and supervised exercises before stronger operational claims are made.

Supporting functionality includes offline catch records and a coarse public activity view derived only from explicitly consented reports, subject to contributor thresholds and expiry.
It does not expose individual fishing positions in the public view or promise catches.
AqOne's intended contribution is safer participation in coastal livelihoods; any wider sustainability benefit will need its own evidence.

## Objectives

The primary objective is to validate the complete distress workflow in New Washington using the actual phone, buoy, radio, gateway and dashboard components.
The pilot will demonstrate an SOS from a phone without cellular service, verify backend receipt, confirm that responder acknowledgement persists after a dashboard reload, and check that handset delivery information reflects the last confirmed state.

The pilot will measure actual WiFi contact range and duration, LoRa relay performance, coverage gaps, message-delivery success and delay, node availability, power endurance and maintenance requirements.
Warning evaluation will measure receipt and handset display, including late, expired and undelivered warnings.
Supervised evaluations will assess false alerts, missed events, overdue-trip handling and drift-search containment against predefined baselines.

The commercial objective is to establish deployment and annual operating costs, gather fisher and responder feedback, and test the proposed purchasing and service arrangement with prospective institutions.
Expansion will depend on documented technical results, user adoption and a sustainable operating model.

## Target market and beneficiaries

The initial prospective customer is a coastal municipal LGU, with its Municipal Disaster Risk Reduction and Management Office as a likely day-to-day operator.
The Philippine Coast Guard, Bureau of Fisheries and Aquatic Resources and other public-safety institutions are potential partners or customers, subject to their needs, responsibilities and purchasing processes.
Pilot participation and institutional commitments will be established through direct engagement.

Municipal and small-scale fishers are the primary users.
The shared infrastructure reduces the need for each participating fisher to acquire a dedicated boat-mounted communication device, while still requiring access to a compatible, powered phone and opportunities to connect with a buoy.
Families may benefit from check-ins, and responders from timestamped information and a common incident view.
Onboarding and training will test whether the service is practical for the intended users.

## Value proposition

AqOne combines shared offshore communication points with a traceable SOS-to-responder workflow.
Its proposed advantage is the ability to serve multiple fishers through institution-funded infrastructure, using their existing phones rather than requiring an individual buoy or dedicated boat device for every user.
Routine messaging and weather access provide reasons to use the app outside emergencies, while recorded contacts can support overdue-trip review.

For responders, the intended value is earlier awareness, clearer delivery status and better information for assessing a case and planning a search.
These benefits will be measured during the pilot, not assumed from software demonstrations.
The service supports professional judgement and existing response procedures; it does not guarantee message reception, continuous connectivity or rescue.

## Business model

AqOne proposes an institutional model based on deployment contracts, recurring maintenance and software services, and additional coverage contracts where expansion is justified.
The institution would fund the agreed infrastructure and service package, enabling participating fishers to use the shared safety network without individually purchasing its core buoy infrastructure.

The initial commercial assumptions are PHP 500,000 per municipal deployment and PHP 120,000 annually for service and maintenance.
These figures are provisional, not validated quotations.
Final pricing will depend on buoy and gateway quantities, site conditions, installation, connectivity, support, maintenance and replacement provisions.
The pilot will establish costs and test institutional willingness to purchase before the team commits to a standard package or claims commercial viability.

## Market analysis

The first market to validate is coastal municipalities with communication gaps affecting small-scale fishers and a local office able to operate and maintain the service.
New Washington provides the initial setting for interviews, route and coverage assessment, supervised deployment and institutional purchasing discussions.
Expansion to other Aklan municipalities and coastal areas will depend on similar demonstrated needs and operating capacity.

Existing arrangements include cellular messaging where coverage exists, marine radio and dedicated distress equipment.
AqOne's proposed distinction is institution-funded buoy connectivity integrated with a local incident dashboard and advisory search support.
The pilot will compare practical coverage, user requirements, responder integration and total operating cost rather than assume AqOne is a universal replacement or the lowest-cost option.
Market validation will establish the number of suitable participating institutions and fishers, the relevant decision makers, budget availability and evidence of willingness to adopt.

## Operations plan

The team will build on the existing software and firmware prototype while resolving the physical deployment requirements with participating institutions.
Preparations will define sites, permissions, moorings, gateway connectivity, power arrangements, maintenance responsibility and participant training.
Pilot agreements will also define authorized access to vessel and incident information, permitted uses and retention responsibilities.
The service is intended for fisher safety, not fisheries enforcement or surveillance.

Testing will progress through verified backend availability, radio communication, buoy-to-backend transmission, phone-to-buoy delivery, and dashboard acknowledgement before broader field trials.
Supervised open-water exercises will record actual ranges, contact gaps, failures and operating conditions using the existing field-evaluation protocols.
AI outputs will remain advisory, and exercises will use appropriate safety support and clearly identified test incidents.

After commissioning, the operating arrangement will cover network monitoring, software updates, inspections, repairs, troubleshooting and support.
The team will review performance and costs with participating fishers and responders before recommending expansion.
Future deployment commitments will be based on measured service capability and agreed responsibilities.

## Financial requirement

The proposed one-year research and development requirement is **PHP 808,448.55**.
The supplied allocation comprises PHP 180,000.00 for personal services, PHP 424,966.00 for maintenance and other operating expenses, and PHP 164,985.00 for equipment, giving a subtotal of PHP 769,951.00.
A five-percent contingency of PHP 38,497.55 brings the request to the stated total.

The funding is intended to support development, prototype and field work, personnel, supplies, equipment, software, cloud services, communications, travel and related project expenses.
A detailed costed work plan will specify quantities, supporting quotations, milestone allocations and the resources needed for safe field evaluation.
This R&D request is separate from the provisional deployment price and annual service fee; the pilot will establish the evidence required to refine both.
