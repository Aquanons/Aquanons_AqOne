import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const workspaceDir = "C:\\Users\\User\\Desktop\\PersonalProjects\\00-HACKATHONS-COMPETITIONS\\00-HACKATHONS\\00-2026-FIRST-YEAR\\2026-Aquanons\\AIHackathon2026_Aquanons_AqOne";
const skillDir = "C:\\Users\\User\\.codex\\plugins\\cache\\openai-primary-runtime\\presentations\\26.909.22227\\skills\\presentations";
const buildDir = path.join(workspaceDir, ".artifacts_build", "aqone-flowchart");
const stagingDir = path.join(workspaceDir, ".codex-finalizer");
const finalPath = path.join(workspaceDir, "artifacts", "AqOne_Editable_Architecture_Flowchart_v3.pptx");
const pythonExecutable = "C:\\Users\\User\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe";

const { resolvePresentationFont, finalizePresentation } = await import(
  pathToFileURL(path.join(skillDir, "container_tools", "artifact_tool_utils.mjs")).href,
);

await fs.mkdir(buildDir, { recursive: true });
await fs.mkdir(stagingDir, { recursive: true });
await fs.mkdir(path.dirname(finalPath), { recursive: true });

const font = resolvePresentationFont();
const presentation = Presentation.create({ slideSize: { width: 1400, height: 2100 } });
const slide = presentation.slides.add();
slide.background.fill = "#FBFCFE";

const C = {
  ink: "#172033",
  muted: "#556174",
  line: "#283449",
  boundary: "#738096",
  input: "#E9EDF2",
  edge: "#D9F1F0",
  backend: "#DDE7FF",
  ai: "#E9DBFA",
  safety: "#FFD7DA",
  fisheries: "#D9F2E2",
  external: "#FFE8C5",
  output: "#D6F5FA",
  white: "#FFFFFF",
  status: "#FFF4CC",
  red: "#C73F4D",
  teal: "#1D7C7A",
  blue: "#395EB7",
  purple: "#7552A8",
  green: "#2F7D54",
};

function addText(name, text, left, top, width, height, size, color = C.ink, bold = false, align = "left") {
  const shape = slide.shapes.add({
    geometry: "textbox",
    name,
    position: { left, top, width, height },
    fill: "none",
    line: { fill: "none", width: 0 },
  });
  shape.text = text;
  shape.text.style = {
    typeface: font,
    fontSize: size,
    bold,
    color,
    alignment: align,
    verticalAlignment: "middle",
    autoFit: "shrinkText",
    insets: { top: 2, right: 3, bottom: 2, left: 3 },
  };
  return shape;
}

function addLayer(name, title, top, height, note = "") {
  const boundary = slide.shapes.add({
    geometry: "roundRect",
    name: `${name}-boundary`,
    position: { left: 28, top, width: 1344, height },
    fill: "#FFFFFF00",
    line: { style: "dashed", fill: C.boundary, width: 1.5 },
    borderRadius: 12,
  });
  boundary.sendToBack();
  addText(`${name}-title`, title, 42, top + 7, 450, 33, 22, C.ink, true);
  if (note) addText(`${name}-note`, note, 815, top + 8, 530, 30, 12, C.muted, false, "right");
  return boundary;
}

function addBox(name, title, subtitle, left, top, width, height, fill, accent = C.line, titleSize = "14pt", bodySize = "9.5pt") {
  const box = slide.shapes.add({
    geometry: "roundRect",
    name,
    position: { left, top, width, height },
    fill,
    line: { style: "solid", fill: accent, width: 1.6 },
    borderRadius: 12,
    shadow: "shadow-sm",
  });
  box.text = [
    [{ run: title, textStyle: { typeface: font, fontSize: titleSize, bold: true, color: C.ink } }],
    [{ run: subtitle, textStyle: { typeface: font, fontSize: bodySize, color: C.muted } }],
  ];
  box.text.style = {
    typeface: font,
    alignment: "center",
    verticalAlignment: "middle",
    autoFit: "shrinkText",
    insets: { top: 8, right: 9, bottom: 8, left: 9 },
  };
  return box;
}

function addPill(name, text, left, top, width, height, fill, accent) {
  const pill = slide.shapes.add({
    geometry: "roundRect",
    name,
    position: { left, top, width, height },
    fill,
    line: { style: "solid", fill: accent, width: 1.4 },
    borderRadius: "rounded-full",
  });
  pill.text = text;
  pill.text.style = {
    typeface: font,
    fontSize: 12,
    bold: true,
    color: C.ink,
    alignment: "center",
    verticalAlignment: "middle",
    autoFit: "shrinkText",
    insets: { top: 3, right: 7, bottom: 3, left: 7 },
  };
  return pill;
}

function addLane(name, title, subtitle, left, fill, accent) {
  const header = addBox(`${name}-header`, title, subtitle, left, 988, 238, 70, fill, accent, "13pt", "8.5pt");
  return { header, left, fill, accent };
}

function connect(name, from, to, options = {}) {
  const connector = slide.shapes.connect(from, to, {
    kind: options.kind ?? "elbow",
    fromSide: options.fromSide,
    toSide: options.toSide,
    line: {
      style: options.style ?? "solid",
      fill: options.color ?? C.line,
      width: options.width ?? 2,
    },
    head: options.tailArrow ? { type: "triangle", width: "sm", length: "sm" } : { type: "none" },
    tail: options.noHead ? { type: "none" } : { type: "triangle", width: "sm", length: "sm" },
  });
  connector.name = name;
  return connector;
}

function addLineLabel(name, text, left, top, width, fill = C.white) {
  const label = slide.shapes.add({
    geometry: "roundRect",
    name,
    position: { left, top, width, height: 30 },
    fill,
    line: { style: "solid", fill: "#CBD2DC", width: 0.8 },
    borderRadius: 8,
  });
  label.text = text;
  label.text.style = {
    typeface: font,
    fontSize: 9,
    bold: true,
    color: C.muted,
    alignment: "center",
    verticalAlignment: "middle",
    autoFit: "shrinkText",
    insets: { top: 2, right: 4, bottom: 2, left: 4 },
  };
  return label;
}

addText("deck-title", "AqOne Detailed Architecture", 42, 17, 880, 50, 34, C.ink, true);
addText("deck-subtitle", "Offline SOS transport, safety intelligence and responder loop", 44, 66, 980, 30, 16, C.muted);
addPill("status-summary", "SOURCE BUILT. FIELD VALIDATION PENDING", 1015, 28, 330, 44, C.status, "#D6B43C");

addLayer("inputs", "Input and Field Layer", 110, 235, "Evidence sources and human actions");
addLayer("transport", "Edge and Transport Layer", 365, 285, "Store first, forward when a path exists");
addLayer("backend", "Backend and Data Layer", 670, 235, "Provider-neutral logical architecture");
addLayer("decision", "Processing and Decision Support Layer", 925, 690, "Manual SOS remains independent of every model");
addLayer("outputs", "Output and Human Response Layer", 1635, 305, "Human authority remains explicit");

const mobileInput = addBox("input-mobile", "Fisher mobile app", "Manual SOS, GPS, timestamp, trip check-ins, optional catch logs", 50, 172, 230, 112, C.input, C.boundary);
const podInput = addBox("input-pod", "Boat pod", "Physical SOS button, GNSS, battery and radio events", 312, 172, 230, 112, C.input, C.boundary);
const sensorInput = addBox("input-sensor", "Stationary sensor buoy", "Fixed pressure, current observations and device health", 574, 172, 230, 112, C.input, C.boundary);
const externalInput = addBox("input-external", "Environmental data", "Open-Meteo weather and marine observations", 836, 172, 230, 112, C.external, "#C5872D");
const responderInput = addBox("input-responder", "Responder actions", "Acknowledge, ETA, resolution and searched sectors", 1098, 172, 230, 112, C.external, "#C5872D");

const phoneQueue = addBox("transport-phone", "Mobile SQLite outbox", "Persists an SOS before any network attempt\nDelivery state: SAVED", 62, 430, 238, 105, C.edge, C.teal);
const directInternet = addBox("transport-direct", "Direct internet path", "HTTPS when cellular or WiFi internet is available", 80, 557, 202, 60, C.white, C.teal, "11pt", "8pt");
const podQueue = addBox("transport-pod", "Boat pod flash queue", "Accepts before acknowledgement and retries after outages\nDelivery state: RELAYED", 350, 430, 255, 105, C.edge, C.teal);
const relay = addBox("transport-relay", "Optional relay buoy", "TTL flooding and duplicate suppression only where field tests justify it", 630, 545, 225, 76, C.edge, C.teal, "11.5pt", "8pt");
const gateway = addBox("transport-gateway", "Tall shoreline gateway", "Verifies LoAM signature, maps device identity and forwards over HTTPS", 895, 430, 255, 105, C.edge, C.teal);
const returnPath = addBox("transport-return", "Return path", "Warnings, acknowledgement and ETA when radio or internet is available", 1168, 430, 175, 105, C.white, C.teal, "11.5pt", "8pt");

connect("mobile-input-to-outbox", mobileInput, phoneQueue, { fromSide: "bottom", toSide: "top", color: C.teal });
connect("pod-input-to-queue", podInput, podQueue, { fromSide: "bottom", toSide: "top", color: C.teal });
connect("sensor-input-to-relay", sensorInput, relay, { fromSide: "bottom", toSide: "top", color: C.teal, style: "dashed" });
connect("phone-to-pod", phoneQueue, podQueue, { fromSide: "right", toSide: "left", color: C.teal, style: "dashed" });
addLineLabel("label-wifi", "WIFI HTTP", 286, 456, 76, C.white);
connect("phone-to-direct", phoneQueue, directInternet, { fromSide: "bottom", toSide: "top", color: C.teal });
connect("pod-direct-lora", podQueue, gateway, { fromSide: "right", toSide: "left", color: C.teal, style: "dashed" });
addLineLabel("label-direct-lora", "DIRECT LoRa", 660, 438, 115, C.white);
connect("pod-to-relay", podQueue, relay, { fromSide: "bottom", toSide: "left", color: C.teal, style: "dashed" });
connect("relay-to-gateway", relay, gateway, { fromSide: "right", toSide: "bottom", color: C.teal, style: "dashed" });
addLineLabel("label-optional-relay", "OPTIONAL RELAY", 714, 584, 126, C.white);
connect("gateway-return", gateway, returnPath, { fromSide: "right", toSide: "left", color: C.teal, style: "dashed", tailArrow: true });

const api = addBox("backend-api", "FastAPI application services", "Authentication and roles, validation and deduplication, SOS and sensor ingest, incident and advisory workflows", 105, 732, 760, 115, C.backend, C.blue, "16pt", "10pt");
const db = addBox("backend-db", "PostgreSQL", "SOS and responder actions\nTrips and contact events\nSensor, advisory, model and audit records", 962, 732, 315, 115, C.backend, C.blue, "16pt", "9.5pt");
const pollPill = addPill("backend-polling", "Current dashboard path: protected REST polling every 3 seconds", 310, 860, 455, 36, "#EEF3FF", C.blue);
connect("gateway-to-api", gateway, api, { fromSide: "bottom", toSide: "top", color: C.blue });
addLineLabel("label-https", "AUTHENTICATED HTTPS", 740, 636, 180, C.white);
connect("direct-to-api", directInternet, api, { fromSide: "bottom", toSide: "left", color: C.blue });
connect("external-to-api", externalInput, api, { fromSide: "bottom", toSide: "top", color: "#C5872D" });
connect("responder-to-api", responderInput, api, { fromSide: "bottom", toSide: "right", color: "#C5872D" });
connect("api-to-db", api, db, { fromSide: "right", toSide: "left", color: C.blue, tailArrow: true });

const lane1 = addLane("lane-sos", "Manual SOS", "AI-independent emergency path", 50, C.safety, C.red);
const lane2 = addLane("lane-weather", "Environmental warning", "Squall and marine danger", 310, C.ai, C.purple);
const lane3 = addLane("lane-trip", "Trip anomaly", "Overdue verification support", 570, C.ai, C.purple);
const lane4 = addLane("lane-drift", "Drift and search", "Physics-based decision support", 830, C.ai, C.purple);
const lane5 = addLane("lane-catch", "Consented catch activity", "Separate optional data purpose", 1090, C.fisheries, C.green);

const sos1 = addBox("sos-validate", "Validate and deduplicate", "Accept distress even before vessel registration", lane1.left, 1080, 238, 86, C.safety, C.red, "12pt", "8pt");
const sos2 = addBox("sos-persist", "Persist incident", "Backend becomes authority for DELIVERED", lane1.left, 1190, 238, 86, C.safety, C.red, "12pt", "8pt");
const sos3 = addBox("sos-dispatch", "Responder workflow", "Acknowledge, ETA, reply and resolution", lane1.left, 1300, 238, 86, C.safety, C.red, "12pt", "8pt");
const sosOut = addPill("sos-result", "DELIVERED / ACKNOWLEDGED", lane1.left + 7, 1420, 224, 46, C.safety, C.red);

const weather1 = addBox("weather-quality", "Quality and freshness gate", "Reject stale, missing or insufficient observations", lane2.left, 1080, 238, 86, C.ai, C.purple, "12pt", "8pt");
const weather2 = addBox("weather-models", "Two distinct models", "Backend squall nowcast\nBrowser danger-zone GBDT", lane2.left, 1190, 238, 86, C.ai, C.purple, "12pt", "8pt");
const weather3 = addBox("weather-advisory", "Advisory candidate", "Shows source, age, confidence and limitations", lane2.left, 1300, 238, 86, C.ai, C.purple, "12pt", "8pt");
const weatherOut = addPill("weather-result", "WARNING CANDIDATE", lane2.left + 7, 1420, 224, 46, C.ai, C.purple);

const trip1 = addBox("trip-history", "Contact and trip history", "Only observations at or before decision time", lane3.left, 1080, 238, 86, C.ai, C.purple, "12pt", "8pt");
const trip2 = addBox("trip-profile", "Per-vessel profile", "Compares duration and route against that vessel", lane3.left, 1190, 238, 86, C.ai, C.purple, "12pt", "8pt");
const trip3 = addBox("trip-case", "Verification and escalation", "Silence alone never proves distress", lane3.left, 1300, 238, 86, C.ai, C.purple, "12pt", "8pt");
const tripOut = addPill("trip-result", "RESPONDER REVIEW", lane3.left + 7, 1420, 224, 46, C.ai, C.purple);

const drift1 = addBox("drift-datum", "Confirmed incident datum", "Last reliable fix, object class, wind, current and coastline", lane4.left, 1080, 238, 86, C.ai, C.purple, "12pt", "8pt");
const drift2 = addBox("drift-model", "Monte Carlo leeway", "Particle paths with land stranding and uncertainty", lane4.left, 1190, 238, 86, C.ai, C.purple, "12pt", "8pt");
const drift3 = addBox("drift-search", "Search posterior update", "Negative search evidence shifts remaining probability", lane4.left, 1300, 238, 86, C.ai, C.purple, "12pt", "8pt");
const driftOut = addPill("drift-result", "SEARCH CONTOURS 50 / 75 / 95%", lane4.left + 7, 1420, 224, 46, C.ai, C.purple);

const catch1 = addBox("catch-consent", "Explicitly consented logs", "Safety access never depends on participation", lane5.left, 1080, 238, 86, C.fisheries, C.green, "12pt", "8pt");
const catch2 = addBox("catch-privacy", "Privacy aggregation", "Coarse cells and minimum independent reporters", lane5.left, 1190, 238, 86, C.fisheries, C.green, "12pt", "8pt");
const catch3 = addBox("catch-activity", "Recent activity surface", "No guaranteed catch and no exact public locations", lane5.left, 1300, 238, 86, C.fisheries, C.green, "12pt", "8pt");
const catchOut = addPill("catch-result", "COARSE ACTIVITY", lane5.left + 7, 1420, 224, 46, C.fisheries, C.green);

for (const [prefix, nodes, accent] of [
  ["sos", [sos1, sos2, sos3, sosOut], C.red],
  ["weather", [weather1, weather2, weather3, weatherOut], C.purple],
  ["trip", [trip1, trip2, trip3, tripOut], C.purple],
  ["drift", [drift1, drift2, drift3, driftOut], C.purple],
  ["catch", [catch1, catch2, catch3, catchOut], C.green],
]) {
  for (let i = 0; i < nodes.length - 1; i += 1) {
    connect(`${prefix}-flow-${i + 1}`, nodes[i], nodes[i + 1], { fromSide: "bottom", toSide: "top", color: accent, width: 1.8 });
  }
}

connect("api-to-sos", api, lane1.header, { fromSide: "bottom", toSide: "top", color: C.red });
connect("api-to-weather", api, lane2.header, { fromSide: "bottom", toSide: "top", color: C.purple });
connect("api-to-trip", api, lane3.header, { fromSide: "bottom", toSide: "top", color: C.purple });
connect("api-to-drift", api, lane4.header, { fromSide: "bottom", toSide: "top", color: C.purple });
connect("api-to-catch", api, lane5.header, { fromSide: "bottom", toSide: "top", color: C.green });
connect("sos-header-to-flow", lane1.header, sos1, { fromSide: "bottom", toSide: "top", color: C.red, width: 1.8 });
connect("weather-header-to-flow", lane2.header, weather1, { fromSide: "bottom", toSide: "top", color: C.purple, width: 1.8 });
connect("trip-header-to-flow", lane3.header, trip1, { fromSide: "bottom", toSide: "top", color: C.purple, width: 1.8 });
connect("drift-header-to-flow", lane4.header, drift1, { fromSide: "bottom", toSide: "top", color: C.purple, width: 1.8 });
connect("catch-header-to-flow", lane5.header, catch1, { fromSide: "bottom", toSide: "top", color: C.green, width: 1.8 });

addPill("decision-boundary", "MODEL OUTPUTS ADVISE; AUTHORIZED PEOPLE DECIDE", 420, 1530, 560, 42, C.status, "#D6B43C");
addText("decision-caveat", "Squall calibration is synthetic. Drift awaits live buoy current telemetry. Catch workflow remains a pilot foundation.", 260, 1575, 880, 28, 11, C.muted, false, "center");

const mobileOutput = addBox("output-mobile", "Fisher mobile app", "Delivery states and responder ETA\nWarnings and forecast freshness\nOptional coarse activity", 85, 1710, 340, 145, C.output, C.teal, "16pt", "10pt");
const dashboardOutput = addBox("output-dashboard", "MDRRMO / PCG dashboard", "Live SOS and acknowledgement\nOverdue review and drift contours\nNetwork and feed freshness", 530, 1710, 340, 145, C.output, C.teal, "16pt", "10pt");
const lguOutput = addBox("output-lgu", "LGU / BFAR aggregated view", "Consented coarse catch activity\nNo identifiable safety trip trails\nPilot workflow not field validated", 975, 1710, 340, 145, C.output, C.teal, "16pt", "10pt");

connect("sos-to-dashboard", sosOut, dashboardOutput, { fromSide: "bottom", toSide: "top", color: C.red });
connect("weather-to-mobile", weatherOut, mobileOutput, { fromSide: "bottom", toSide: "top", color: C.purple });
connect("trip-to-dashboard", tripOut, dashboardOutput, { fromSide: "bottom", toSide: "top", color: C.purple });
connect("drift-to-dashboard", driftOut, dashboardOutput, { fromSide: "bottom", toSide: "top", color: C.purple });
connect("catch-to-lgu", catchOut, lguOutput, { fromSide: "bottom", toSide: "top", color: C.green });
connect("catch-to-mobile", catchOut, mobileOutput, { fromSide: "bottom", toSide: "top", color: C.green, style: "dashed" });
connect("dashboard-to-mobile", dashboardOutput, mobileOutput, { fromSide: "left", toSide: "right", color: C.teal, style: "dashed" });
addLineLabel("label-return-user", "ACK, ETA AND WARNINGS WHEN A RETURN PATH EXISTS", 335, 1868, 410, C.white);
addPill("authority-pill", "Responder acknowledgement creates ACKNOWLEDGED. Resolution remains a separate incident state.", 315, 1888, 770, 40, "#EEF8FA", C.teal);

addText("legend-title", "Legend", 42, 1964, 110, 28, 17, C.ink, true);
const swatches = [
  ["legend-hardware", "Field / edge", C.edge, C.teal, 155],
  ["legend-backend", "Backend / data", C.backend, C.blue, 315],
  ["legend-ai", "Model / simulation", C.ai, C.purple, 490],
  ["legend-safety", "Emergency", C.safety, C.red, 690],
  ["legend-external", "External / human", C.external, "#C5872D", 835],
  ["legend-output", "Output", C.output, C.teal, 1035],
  ["legend-fisheries", "Fisheries", C.fisheries, C.green, 1165],
];
for (const [name, label, fill, accent, left] of swatches) {
  slide.shapes.add({ geometry: "ellipse", name: `${name}-dot`, position: { left, top: 2005, width: 24, height: 24 }, fill, line: { style: "solid", fill: accent, width: 1 } });
  addText(`${name}-label`, label, left + 29, 1997, 145, 40, 10.5, C.ink, false);
}
addText("legend-lines", "Solid: implemented software path     Dashed: hardware, optional or return path awaiting field verification", 155, 2040, 860, 28, 10.5, C.muted);
addText("legend-status", "Current status: software is locally tested; public deployment, real-device LoRa range and local field-model validation remain pending.", 805, 2038, 535, 35, 10, C.muted, false, "right");

slide.speakerNotes.textFrame.setText([
  "AqOne architecture sources:",
  "README.md, current status and implemented versus unverified paths.",
  "docs/55_HYBRID_TRANSPORT_ARCHITECTURE_DECISION.md, active boat-pod and direct-to-shore topology.",
  "docs/06_DELIVERY_STATES.md, saved, relayed, delivered and acknowledged authorities.",
  "docs/Aqone_PRD (2).md, canonical product and AI scope.",
  "docs/17_AI_EXPLAINED_SIMPLY.md, squall, trip anomaly, drift and browser danger-zone implementation.",
  "web/js/dashboard/dashboard-live-sos.js, current three-second REST polling behavior.",
].join("\n"));

const candidatePath = path.join(stagingDir, "aqone-flowchart-candidate.pptx");
await (await PresentationFile.exportPptx(presentation)).save(candidatePath);
const preview = await presentation.export({ slide, format: "png", scale: 0.7 });
await fs.writeFile(path.join(buildDir, "aqone-flowchart-preview.png"), new Uint8Array(await preview.arrayBuffer()));
const layout = await slide.export({ format: "layout" });
await fs.writeFile(path.join(buildDir, "aqone-flowchart.layout.json"), await layout.text());

const result = await finalizePresentation({
  explicitTotalSlideCount: 1,
  requiredNativeTableOwnerSlides: [],
  requiredNativeChartOwnerSlides: [],
  workspaceDir,
  candidatePath,
  finalPath,
  pythonExecutable,
  integrityValidatorPath: path.join(skillDir, "container_tools", "inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(skillDir, "container_tools", "inspect_presentation_layout_geometry.py"),
  layoutArgs: [
    "--expected-slide-size-emu", "13335000,20002500",
    "--validate-heading-fit",
  ],
  fontPolicy: { basis: "design", families: [font] },
  verifyArtifactToolImport: true,
  receiptPath: path.join(stagingDir, "AqOne_Editable_Architecture_Flowchart_v3.validation.json"),
});

console.log(JSON.stringify({ finalPath, previewPath: path.join(buildDir, "aqone-flowchart-preview.png"), font, result }, null, 2));
