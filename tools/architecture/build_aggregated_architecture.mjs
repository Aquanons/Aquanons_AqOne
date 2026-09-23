import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const workspaceDir = path.resolve(__dirname, "..", "..");
const skillDir = process.env.CODEX_PRESENTATION_SKILL_DIR || "";
const buildDir = path.join(workspaceDir, ".artifacts_build", "aqone-flowchart");
const stagingDir = path.join(workspaceDir, ".codex-finalizer");
const finalPath = path.join(workspaceDir, "artifacts", "architecture", "AqOne_Aggregated_Technical_Architecture_Editable.pptx");
const pythonExecutable = process.env.PYTHON_EXECUTABLE || process.env.PYTHON || "python";

if (!skillDir) {
  throw new Error("CODEX_PRESENTATION_SKILL_DIR environment variable is required to execute this generator.");
}

const { resolvePresentationFont, finalizePresentation } = await import(
  pathToFileURL(path.join(skillDir, "container_tools", "artifact_tool_utils.mjs")).href,
);

await fs.mkdir(buildDir, { recursive: true });
await fs.mkdir(stagingDir, { recursive: true });
await fs.mkdir(path.dirname(finalPath), { recursive: true });

const font = resolvePresentationFont();
const W = 5200;
const H = 3400;
const deck = Presentation.create({ slideSize: { width: W, height: H } });
const slide = deck.slides.add();

const C = {
  bg: "#F7F9FC",
  ink: "#142033",
  muted: "#5B6678",
  line: "#24334A",
  white: "#FFFFFF",
  sos: "#C7374A",
  sosFill: "#FFE1E5",
  env: "#7251AA",
  envFill: "#EDE2FA",
  trip: "#5357B4",
  tripFill: "#E6E7FF",
  drift: "#345EAF",
  driftFill: "#E1ECFF",
  fish: "#2C7A50",
  fishFill: "#DEF3E7",
  edge: "#177A78",
  edgeFill: "#D9F1F0",
  backend: "#365DB5",
  backendFill: "#DDE7FF",
  output: "#177E8D",
  outputFill: "#D7F4F8",
  external: "#B6791C",
  externalFill: "#FFEAC8",
  neutralFill: "#EEF2F6",
  branchFill: "#FFF8E8",
};

slide.background.fill = C.bg;

function textBox(name, text, left, top, width, height, size, color = C.ink, bold = false, align = "left", fill = "none") {
  const shape = slide.shapes.add({
    geometry: "textbox",
    name,
    position: { left, top, width, height },
    fill,
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
    insets: { top: 2, right: 6, bottom: 2, left: 6 },
  };
  return shape;
}

function shapeBox(name, geometry, title, subtitle, left, top, width, height, fill, color, options = {}) {
  const shape = slide.shapes.add({
    geometry,
    name,
    position: { left, top, width, height },
    fill,
    line: { style: options.dashed ? "dashed" : "solid", fill: color, width: options.lineWidth ?? 2.4 },
    shadow: options.shadow === false ? "shadow-none" : "shadow-sm",
  });
  shape.text = subtitle
    ? [
        [{ run: title, textStyle: { typeface: font, fontSize: options.titleSize ?? "18pt", bold: true, color: C.ink } }],
        [{ run: subtitle, textStyle: { typeface: font, fontSize: options.bodySize ?? "12pt", color: C.muted } }],
      ]
    : title;
  shape.text.style = {
    typeface: font,
    fontSize: options.titleSize ?? 18,
    bold: !subtitle,
    color: C.ink,
    alignment: "center",
    verticalAlignment: "middle",
    autoFit: "shrinkText",
    insets: { top: 10, right: 12, bottom: 10, left: 12 },
  };
  return shape;
}

const process = (name, title, subtitle, left, top, width, height, fill, color, options = {}) =>
  shapeBox(name, "roundRect", title, subtitle, left, top, width, height, fill, color, options);
const data = (name, title, subtitle, left, top, width, height, fill, color, options = {}) =>
  shapeBox(name, "parallelogram", title, subtitle, left, top, width, height, fill, color, options);
const decision = (name, title, left, top, width, height, fill, color, options = {}) =>
  shapeBox(name, "diamond", title, "", left, top, width, height, fill, color, { ...options, titleSize: options.titleSize ?? 16, shadow: false });
const terminator = (name, title, left, top, width, height, fill, color, options = {}) =>
  shapeBox(name, "ellipse", title, "", left, top, width, height, fill, color, { ...options, titleSize: options.titleSize ?? 16, shadow: false });
const store = (name, title, subtitle, left, top, width, height, fill, color, options = {}) =>
  shapeBox(name, "can", title, subtitle, left, top, width, height, fill, color, options);

function connector(name, from, to, color, options = {}) {
  const c = slide.shapes.connect(from, to, {
    kind: options.kind ?? "straight",
    fromSide: options.fromSide,
    toSide: options.toSide,
    line: { style: options.dashed ? "dashed" : "solid", fill: color, width: options.width ?? 3.2 },
    head: { type: "none" },
    tail: { type: "triangle", width: "sm", length: "sm" },
  });
  c.name = name;
  c.bringToFront();
  return c;
}

function routeLabel(name, text, left, top, width, color, align = "center") {
  return textBox(name, text, left, top, width, 34, 12.5, color, true, align);
}

function lane(y, title, subtitle, color, fill) {
  const band = slide.shapes.add({
    geometry: "roundRect",
    name: `${title}-lane`,
    position: { left: 28, top: y, width: 5144, height: 520 },
    fill: C.white,
    line: { style: "solid", fill: color, width: 2 },
    shadow: "shadow-none",
  });
  band.sendToBack();
  const tag = slide.shapes.add({
    geometry: "roundRect",
    name: `${title}-tag`,
    position: { left: 48, top: y + 22, width: 220, height: 88 },
    fill,
    line: { style: "solid", fill: color, width: 2 },
    shadow: "shadow-none",
  });
  tag.text = title;
  tag.text.style = { typeface: font, fontSize: 19, bold: true, color, alignment: "center", verticalAlignment: "middle", autoFit: "shrinkText", insets: { top: 6, right: 8, bottom: 6, left: 8 } };
  textBox(`${title}-subtitle`, subtitle, 54, y + 116, 205, 92, 11.5, C.muted, false, "center");
}

function phaseBand(name, label, left, width, fill) {
  const band = slide.shapes.add({
    geometry: "rect",
    name,
    position: { left, top: 188, width, height: 70 },
    fill,
    line: { style: "solid", fill: "#CAD2DD", width: 1 },
    shadow: "shadow-none",
  });
  band.sendToBack();
  textBox(`${name}-label`, label, left + 5, 200, width - 10, 42, 14, C.muted, true, "center");
}

function dotConnector(name, label, left, top, color) {
  const dot = slide.shapes.add({
    geometry: "ellipse",
    name,
    position: { left, top, width: 48, height: 48 },
    fill: C.white,
    line: { style: "solid", fill: color, width: 2.2 },
    shadow: "shadow-none",
  });
  dot.text = label;
  dot.text.style = { typeface: font, fontSize: 11, bold: true, color, alignment: "center", verticalAlignment: "middle", insets: { top: 1, right: 1, bottom: 1, left: 1 } };
  return dot;
}

// Page header and architectural bands.
textBox("title", "AqOne Aggregated Technical Architecture", 54, 30, 3300, 80, 52, C.ink, true);
textBox("subtitle", "Offline SOS transport, safety intelligence, storage, privacy controls and human response", 58, 108, 3800, 46, 23, C.muted);
const status = process("status", "CURRENT IMPLEMENTATION", "Software paths tested locally; public deployment and field validation remain pending", 3950, 48, 1160, 98, "#FFF4CC", "#C39A13", { titleSize: "15pt", bodySize: "11pt", shadow: false });

phaseBand("phase-source", "SOURCE AND DATA", 290, 820, "#F2F5F8");
phaseBand("phase-edge", "EDGE DEVICE", 1110, 820, "#EDF8F7");
phaseBand("phase-transport", "TRANSPORT", 1930, 820, "#F3F8F8");
phaseBand("phase-backend", "INGRESS AND STORAGE", 2750, 820, "#EEF3FF");
phaseBand("phase-decision", "PROCESSING AND DECISION", 3570, 820, "#F5F0FB");
phaseBand("phase-output", "OUTPUT AND HUMAN ACTION", 4390, 770, "#EAF9FB");

// Lane 1: Emergency SOS.
const y1 = 280;
lane(y1, "EMERGENCY SOS", "Manual distress path\nIndependent of every AI model", C.sos, C.sosFill);
const sStart = terminator("s-start", "Fisher presses SOS\nor pod button", 310, y1 + 175, 260, 110, C.sosFill, C.sos);
const sPayload = data("s-payload", "SOS payload", "local_id, vessel_id, time, GPS, note", 620, y1 + 165, 300, 130, C.sosFill, C.sos);
const sInternet = decision("s-internet", "Internet\navailable?", 970, y1 + 150, 240, 160, C.branchFill, C.sos);
const sDirectPost = process("s-direct-post", "Direct HTTPS", "POST /api/sos", 1260, y1 + 28, 260, 104, C.backendFill, C.backend, { titleSize: "16pt", bodySize: "11pt", shadow: false });
const sDirectOut = dotConnector("s-direct-out", "S1", 1550, y1 + 56, C.backend);
const sPodReach = decision("s-pod-reach", "Boat pod\nreachable?", 1260, y1 + 150, 240, 160, C.branchFill, C.sos);
const sOutbox = store("s-outbox", "Phone SQLite outbox", "State: SAVED; retry later", 1250, y1 + 348, 270, 118, C.neutralFill, C.sos, { titleSize: "15pt", bodySize: "10.5pt", shadow: false });
const sRetryEnd = terminator("s-retry-end", "Wait for a valid path", 1555, y1 + 366, 235, 82, C.neutralFill, C.sos, { titleSize: 13 });
const sPodQueue = process("s-pod-queue", "Boat pod queues first", "Flash queue; state: RELAYED", 1580, y1 + 165, 285, 130, C.edgeFill, C.edge);
const sLora = decision("s-lora", "Direct LoRa\nreaches shore?", 1915, y1 + 150, 240, 160, C.branchFill, C.edge);
const sRelay = process("s-relay", "Optional relay buoy", "TTL and seen-set forwarding", 1920, y1 + 348, 285, 118, C.edgeFill, C.edge, { dashed: true, titleSize: "15pt", bodySize: "10.5pt", shadow: false });
const sGateway = process("s-gateway", "Tall shore gateway", "Verify HMAC; map identity", 2250, y1 + 165, 285, 130, C.edgeFill, C.edge);
const sHttps = data("s-https", "Authenticated HTTPS", "Signed frame becomes ingest request", 2580, y1 + 165, 285, 130, C.backendFill, C.backend);
const sDirectIn = dotConnector("s-direct-in", "S1", 2665, y1 + 76, C.backend);
const sBackend = process("s-backend", "FastAPI intake", "Validate, deduplicate, persist", 2910, y1 + 165, 285, 130, C.backendFill, C.backend);
const sStore = store("s-store", "PostgreSQL", "SOS, delivery state, audit trail", 3240, y1 + 155, 285, 150, C.backendFill, C.backend);
const sDashboard = process("s-dashboard", "MDRRMO dashboard", "Protected REST poll every 3 seconds", 3570, y1 + 165, 300, 130, C.outputFill, C.output);
const sAck = process("s-ack", "Responder acknowledges", "ETA, note and response status", 3915, y1 + 165, 300, 130, C.externalFill, C.external);
const sReturn = decision("s-return", "Return path\navailable?", 4260, y1 + 150, 240, 160, C.branchFill, C.output);
const sAckData = data("s-ack-data", "Ack + ETA", "Phone state: ACKNOWLEDGED", 4550, y1 + 62, 300, 130, C.outputFill, C.output);
const sLastState = data("s-last-state", "Last proven phone state", "No invented delivery or acknowledgement", 4550, y1 + 320, 300, 130, C.neutralFill, C.output, { titleSize: "15pt", bodySize: "10.5pt" });
const sEnd = terminator("s-end", "Incident response continues", 4890, y1 + 82, 245, 90, C.outputFill, C.output, { titleSize: 13 });
const sNoReturnEnd = terminator("s-no-return-end", "Reconcile later", 4890, y1 + 340, 245, 90, C.neutralFill, C.output, { titleSize: 13 });

connector("s-1", sStart, sPayload, C.sos, { fromSide: "right", toSide: "left" });
connector("s-2", sPayload, sInternet, C.sos, { fromSide: "right", toSide: "left" });
connector("s-yes-internet", sInternet, sDirectPost, C.backend, { fromSide: "top", toSide: "left", kind: "elbow" });
connector("s-direct-id", sDirectPost, sDirectOut, C.backend, { fromSide: "right", toSide: "left" });
connector("s-no-internet", sInternet, sPodReach, C.sos, { fromSide: "right", toSide: "left" });
connector("s-no-pod", sPodReach, sOutbox, C.sos, { fromSide: "bottom", toSide: "top" });
connector("s-retry", sOutbox, sRetryEnd, C.sos, { fromSide: "right", toSide: "left", dashed: true });
connector("s-yes-pod", sPodReach, sPodQueue, C.sos, { fromSide: "right", toSide: "left" });
connector("s-queue-lora", sPodQueue, sLora, C.edge, { fromSide: "right", toSide: "left" });
connector("s-yes-lora", sLora, sGateway, C.edge, { fromSide: "right", toSide: "left", dashed: true });
connector("s-no-lora", sLora, sRelay, C.edge, { fromSide: "bottom", toSide: "top", dashed: true });
connector("s-relay-gateway", sRelay, sGateway, C.edge, { fromSide: "right", toSide: "bottom", kind: "elbow", dashed: true });
connector("s-gateway-https", sGateway, sHttps, C.backend, { fromSide: "right", toSide: "left" });
connector("s-https-backend", sHttps, sBackend, C.backend, { fromSide: "right", toSide: "left" });
connector("s-direct-continue", sDirectIn, sBackend, C.backend, { fromSide: "right", toSide: "top", kind: "elbow" });
connector("s-backend-store", sBackend, sStore, C.backend, { fromSide: "right", toSide: "left" });
connector("s-store-dashboard", sStore, sDashboard, C.sos, { fromSide: "right", toSide: "left" });
connector("s-dashboard-ack", sDashboard, sAck, C.sos, { fromSide: "right", toSide: "left" });
connector("s-ack-return", sAck, sReturn, C.output, { fromSide: "right", toSide: "left" });
connector("s-return-yes", sReturn, sAckData, C.output, { fromSide: "right", toSide: "left", kind: "elbow" });
connector("s-return-no", sReturn, sLastState, C.output, { fromSide: "bottom", toSide: "left", kind: "elbow", dashed: true });
connector("s-ack-end", sAckData, sEnd, C.output, { fromSide: "right", toSide: "left" });
connector("s-last-end", sLastState, sNoReturnEnd, C.output, { fromSide: "right", toSide: "left", dashed: true });

routeLabel("s-l1", "WiFi HTTP", 1490, y1 + 126, 120, C.sos);
routeLabel("s-l2", "Signed LoAM", 2165, y1 + 126, 100, C.edge);
routeLabel("s-l3", "YES", 1080, y1 + 78, 70, C.backend);
routeLabel("s-l4", "NO", 1188, y1 + 195, 60, C.sos);
routeLabel("s-l5", "NO", 1354, y1 + 315, 60, C.sos);
routeLabel("s-l6", "YES", 1496, y1 + 195, 70, C.sos);
routeLabel("s-l7", "YES", 2158, y1 + 195, 70, C.edge);
routeLabel("s-l8", "NO", 2020, y1 + 315, 60, C.edge);
routeLabel("s-l9", "YES", 4462, y1 + 82, 70, C.output);
routeLabel("s-l10", "NO", 4385, y1 + 315, 60, C.output);
textBox("s-id-note", "S1 continues the direct internet path without crossing the offline path", 2440, y1 + 20, 560, 40, 11.5, C.backend, true, "center");

// Lane 2: Environmental warning.
const y2 = 820;
lane(y2, "ENVIRONMENTAL WARNING", "Sensor and forecast inputs\nAdvisory only", C.env, C.envFill);
const eStart = terminator("e-start", "Sensor cadence or\ndashboard refresh", 310, y2 + 175, 260, 110, C.envFill, C.env);
const eInput = data("e-input", "Environmental inputs", "Pressure, current, health, weather, marine", 620, y2 + 160, 320, 140, C.envFill, C.env);
const eNormalize = process("e-normalize", "Ingest and normalize", "Attach source, time and location", 990, y2 + 165, 285, 130, C.backendFill, C.backend);
const eQuality = decision("e-quality", "Fresh and\nreliable?", 1320, y2 + 150, 240, 160, C.branchFill, C.env);
const eStale = data("e-stale", "Unknown or stale", "Do not claim a safe condition", 1310, y2 + 348, 280, 118, C.neutralFill, C.env, { titleSize: "15pt", bodySize: "10.5pt" });
const eStaleEnd = terminator("e-stale-end", "Wait for better data", 1625, y2 + 366, 235, 82, C.neutralFill, C.env, { titleSize: 13 });
const eSquall = process("e-squall", "Backend squall nowcast", "Pressure and forecast features", 1640, y2 + 80, 300, 120, C.envFill, C.env, { titleSize: "16pt", bodySize: "11pt" });
const eDanger = process("e-danger", "Browser danger-zone GBDT", "Local map features", 1640, y2 + 250, 300, 120, C.envFill, C.env, { titleSize: "16pt", bodySize: "11pt" });
const eCombine = process("e-combine", "Combine model evidence", "Keep source and age visible", 1990, y2 + 165, 300, 130, C.envFill, C.env);
const eOfficial = decision("e-official", "Official or human\nwarning exists?", 2340, y2 + 150, 260, 160, C.branchFill, C.env);
const ePrecedence = process("e-precedence", "Use official or human warning", "Overrides model advisory", 2660, y2 + 72, 310, 120, C.externalFill, C.external, { titleSize: "15pt", bodySize: "10.5pt" });
const eCandidate = process("e-candidate", "Model advisory candidate", "No autonomous emergency action", 2660, y2 + 280, 310, 120, C.envFill, C.env, { titleSize: "15pt", bodySize: "10.5pt" });
const ePublish = process("e-publish", "Publish advisory", "Record source, age, confidence", 3030, y2 + 165, 300, 130, C.backendFill, C.backend);
const eStore = store("e-store", "PostgreSQL", "Telemetry and advisories", 3380, y2 + 155, 280, 150, C.backendFill, C.backend);
const eOutput = data("e-output", "Warning payload", "Risk, source, age, confidence, location", 3710, y2 + 160, 320, 140, C.outputFill, C.output);
const eSurface = process("e-surface", "Mobile and dashboard", "Authorized users review context", 4080, y2 + 165, 300, 130, C.outputFill, C.output);
const eEnd = terminator("e-end", "Human decides action", 4430, y2 + 175, 260, 110, C.outputFill, C.output);

connector("e-1", eStart, eInput, C.env, { fromSide: "right", toSide: "left" });
connector("e-2", eInput, eNormalize, C.env, { fromSide: "right", toSide: "left" });
connector("e-3", eNormalize, eQuality, C.env, { fromSide: "right", toSide: "left" });
connector("e-no", eQuality, eStale, C.env, { fromSide: "bottom", toSide: "top", dashed: true });
connector("e-stale-end-link", eStale, eStaleEnd, C.env, { fromSide: "right", toSide: "left", dashed: true });
connector("e-yes-top", eQuality, eSquall, C.env, { fromSide: "right", toSide: "left", kind: "elbow" });
connector("e-yes-bottom", eQuality, eDanger, C.env, { fromSide: "right", toSide: "left", kind: "elbow" });
connector("e-squall-combine", eSquall, eCombine, C.env, { fromSide: "right", toSide: "top", kind: "elbow" });
connector("e-danger-combine", eDanger, eCombine, C.env, { fromSide: "right", toSide: "bottom", kind: "elbow" });
connector("e-combine-official", eCombine, eOfficial, C.env, { fromSide: "right", toSide: "left" });
connector("e-official-yes", eOfficial, ePrecedence, C.external, { fromSide: "right", toSide: "left", kind: "elbow" });
connector("e-official-no", eOfficial, eCandidate, C.env, { fromSide: "right", toSide: "left", kind: "elbow" });
connector("e-precedence-publish", ePrecedence, ePublish, C.external, { fromSide: "right", toSide: "top", kind: "elbow" });
connector("e-candidate-publish", eCandidate, ePublish, C.env, { fromSide: "right", toSide: "bottom", kind: "elbow" });
connector("e-publish-store", ePublish, eStore, C.backend, { fromSide: "right", toSide: "left" });
connector("e-store-output", eStore, eOutput, C.output, { fromSide: "right", toSide: "left" });
connector("e-output-surface", eOutput, eSurface, C.output, { fromSide: "right", toSide: "left" });
connector("e-surface-end", eSurface, eEnd, C.output, { fromSide: "right", toSide: "left" });
routeLabel("e-yes", "YES", 1570, y2 + 136, 70, C.env);
routeLabel("e-no-label", "NO", 1410, y2 + 315, 60, C.env);
routeLabel("e-off-yes", "YES", 2588, y2 + 98, 70, C.external);
routeLabel("e-off-no", "NO", 2588, y2 + 322, 60, C.env);

// Lane 3: Trip anomaly.
const y3 = 1360;
lane(y3, "TRIP ANOMALY", "Per-vessel deviation signal\nRequires responder verification", C.trip, C.tripFill);
const tStart = terminator("t-start", "Active or open trip", 310, y3 + 175, 260, 110, C.tripFill, C.trip);
const tInput = data("t-input", "Trip evidence", "Contact events, route, duration, trip history", 620, y3 + 160, 320, 140, C.tripFill, C.trip);
const tFilter = process("t-filter", "Causal history filter", "Exclude future and candidate-trip leakage", 990, y3 + 165, 300, 130, C.tripFill, C.trip);
const tBaseline = decision("t-baseline", "Enough personal\nbaseline?", 1340, y3 + 150, 240, 160, C.branchFill, C.trip);
const tCold = process("t-cold", "Cold-start review queue", "Ask for human verification", 1325, y3 + 348, 280, 118, C.neutralFill, C.trip, { titleSize: "15pt", bodySize: "10.5pt", shadow: false });
const tColdEnd = terminator("t-cold-end", "No automated claim", 1640, y3 + 366, 235, 82, C.neutralFill, C.trip, { titleSize: 13 });
const tProfile = process("t-profile", "Build per-vessel profile", "Personal route and duration behavior", 1650, y3 + 165, 300, 130, C.tripFill, C.trip);
const tDeviation = decision("t-deviation", "Deviation exceeds\nthreshold?", 2000, y3 + 150, 250, 160, C.branchFill, C.trip);
const tContinue = terminator("t-continue", "Continue monitoring", 2000, y3 + 366, 250, 82, C.neutralFill, C.trip, { titleSize: 13 });
const tCase = process("t-case", "Create anomaly case", "Evidence, confidence and reason", 2310, y3 + 165, 300, 130, C.tripFill, C.trip);
const tStore = store("t-store", "PostgreSQL", "Trip state and anomaly case", 2660, y3 + 155, 280, 150, C.backendFill, C.backend);
const tReview = process("t-review", "Responder review", "Call, radio check, context review", 2990, y3 + 165, 300, 130, C.externalFill, C.external);
const tEscalate = decision("t-escalate", "Escalate as\nincident?", 3340, y3 + 150, 240, 160, C.branchFill, C.trip);
const tDismiss = terminator("t-dismiss", "Dismiss or monitor case", 3330, y3 + 366, 270, 82, C.neutralFill, C.trip, { titleSize: 13 });
const tDatum = data("t-datum", "Confirmed incident datum", "Last fix, time, object class; connector D1", 3630, y3 + 160, 340, 140, C.driftFill, C.drift);
const tEnd = terminator("t-end", "Pass to drift lane", 4020, y3 + 175, 250, 110, C.driftFill, C.drift);

connector("t-1", tStart, tInput, C.trip, { fromSide: "right", toSide: "left" });
connector("t-2", tInput, tFilter, C.trip, { fromSide: "right", toSide: "left" });
connector("t-3", tFilter, tBaseline, C.trip, { fromSide: "right", toSide: "left" });
connector("t-no-base", tBaseline, tCold, C.trip, { fromSide: "bottom", toSide: "top", dashed: true });
connector("t-cold-end-link", tCold, tColdEnd, C.trip, { fromSide: "right", toSide: "left", dashed: true });
connector("t-yes-base", tBaseline, tProfile, C.trip, { fromSide: "right", toSide: "left" });
connector("t-profile-dev", tProfile, tDeviation, C.trip, { fromSide: "right", toSide: "left" });
connector("t-dev-no", tDeviation, tContinue, C.trip, { fromSide: "bottom", toSide: "top", dashed: true });
connector("t-dev-yes", tDeviation, tCase, C.trip, { fromSide: "right", toSide: "left" });
connector("t-case-store", tCase, tStore, C.backend, { fromSide: "right", toSide: "left" });
connector("t-store-review", tStore, tReview, C.external, { fromSide: "right", toSide: "left" });
connector("t-review-escalate", tReview, tEscalate, C.trip, { fromSide: "right", toSide: "left" });
connector("t-escalate-no", tEscalate, tDismiss, C.trip, { fromSide: "bottom", toSide: "top", dashed: true });
connector("t-escalate-yes", tEscalate, tDatum, C.drift, { fromSide: "right", toSide: "left" });
connector("t-datum-end", tDatum, tEnd, C.drift, { fromSide: "right", toSide: "left" });
routeLabel("t-b-no", "NO", 1430, y3 + 315, 60, C.trip);
routeLabel("t-b-yes", "YES", 1580, y3 + 195, 70, C.trip);
routeLabel("t-d-no", "NO", 2100, y3 + 315, 60, C.trip);
routeLabel("t-d-yes", "YES", 2250, y3 + 195, 70, C.trip);
routeLabel("t-e-no", "NO", 3430, y3 + 315, 60, C.trip);
routeLabel("t-e-yes", "YES", 3575, y3 + 195, 70, C.drift);

// Lane 4: Drift and search.
const y4 = 1900;
lane(y4, "DRIFT AND SEARCH", "Decision support after confirmed incident\nNo autonomous dispatch", C.drift, C.driftFill);
const dStart = terminator("d-start", "Confirmed SOS or D1 case", 310, y4 + 175, 270, 110, C.driftFill, C.drift);
const dDatum = data("d-datum", "Incident datum", "Last fix, time, object class", 630, y4 + 160, 300, 140, C.driftFill, C.drift);
const dForcing = process("d-forcing", "Load environmental forcing", "Wind, current and coastline", 980, y4 + 165, 300, 130, C.driftFill, C.drift);
const dCurrent = decision("d-current", "Live current\nsupport?", 1330, y4 + 150, 240, 160, C.branchFill, C.drift);
const dObserved = process("d-observed", "Use observed current field", "Time and location aligned", 1630, y4 + 72, 300, 120, C.driftFill, C.drift, { titleSize: "15pt", bodySize: "10.5pt" });
const dDegraded = process("d-degraded", "Mark degraded mode", "Assumption-conditioned output", 1630, y4 + 280, 300, 120, C.neutralFill, C.drift, { titleSize: "15pt", bodySize: "10.5pt", shadow: false });
const dMonte = process("d-monte", "Monte Carlo leeway", "Particle paths and land stranding", 1980, y4 + 165, 300, 130, C.driftFill, C.drift);
const dGrid = data("d-grid", "Search probability", "Grid plus 50, 75 and 95 percent contours", 2330, y4 + 160, 330, 140, C.driftFill, C.drift);
const dRank = process("d-rank", "Rank search sectors", "Coverage priority and uncertainty", 2710, y4 + 165, 300, 130, C.driftFill, C.drift);
const dNegative = decision("d-negative", "Negative search\nevidence?", 3060, y4 + 150, 250, 160, C.branchFill, C.drift);
const dPlan = data("d-plan", "Current search plan", "Ranked sectors and confidence", 3380, y4 + 72, 300, 120, C.outputFill, C.output, { titleSize: "15pt", bodySize: "10.5pt" });
const dPosterior = process("d-posterior", "Update posterior", "Condition on searched area and time", 3380, y4 + 280, 300, 120, C.driftFill, C.drift, { titleSize: "15pt", bodySize: "10.5pt" });
const dRevised = data("d-revised", "Revised search plan", "Updated contours and sector order", 3730, y4 + 280, 300, 120, C.outputFill, C.output, { titleSize: "15pt", bodySize: "10.5pt" });
const dStore = store("d-store", "PostgreSQL", "Incident, model run, search evidence", 4080, y4 + 155, 300, 150, C.backendFill, C.backend);
const dSurface = process("d-surface", "Responder map", "Human reviews and directs search", 4430, y4 + 165, 300, 130, C.outputFill, C.output);
const dEnd = terminator("d-end", "Search plan remains advisory", 4780, y4 + 175, 300, 110, C.outputFill, C.output);

connector("d-1", dStart, dDatum, C.drift, { fromSide: "right", toSide: "left" });
connector("d-2", dDatum, dForcing, C.drift, { fromSide: "right", toSide: "left" });
connector("d-3", dForcing, dCurrent, C.drift, { fromSide: "right", toSide: "left" });
connector("d-current-yes", dCurrent, dObserved, C.drift, { fromSide: "right", toSide: "left", kind: "elbow" });
connector("d-current-no", dCurrent, dDegraded, C.drift, { fromSide: "right", toSide: "left", kind: "elbow", dashed: true });
connector("d-observed-monte", dObserved, dMonte, C.drift, { fromSide: "right", toSide: "top", kind: "elbow" });
connector("d-degraded-monte", dDegraded, dMonte, C.drift, { fromSide: "right", toSide: "bottom", kind: "elbow", dashed: true });
connector("d-monte-grid", dMonte, dGrid, C.drift, { fromSide: "right", toSide: "left" });
connector("d-grid-rank", dGrid, dRank, C.drift, { fromSide: "right", toSide: "left" });
connector("d-rank-negative", dRank, dNegative, C.drift, { fromSide: "right", toSide: "left" });
connector("d-negative-no", dNegative, dPlan, C.output, { fromSide: "right", toSide: "left", kind: "elbow" });
connector("d-negative-yes", dNegative, dPosterior, C.drift, { fromSide: "right", toSide: "left", kind: "elbow" });
connector("d-posterior-revised", dPosterior, dRevised, C.output, { fromSide: "right", toSide: "left" });
connector("d-plan-store", dPlan, dStore, C.backend, { fromSide: "right", toSide: "top", kind: "elbow" });
connector("d-revised-store", dRevised, dStore, C.backend, { fromSide: "right", toSide: "bottom", kind: "elbow" });
connector("d-store-surface", dStore, dSurface, C.output, { fromSide: "right", toSide: "left" });
connector("d-surface-end", dSurface, dEnd, C.output, { fromSide: "right", toSide: "left" });
routeLabel("d-c-yes", "YES", 1560, y4 + 98, 70, C.drift);
routeLabel("d-c-no", "NO", 1560, y4 + 322, 60, C.drift);
routeLabel("d-n-no", "NO", 3310, y4 + 98, 60, C.output);
routeLabel("d-n-yes", "YES", 3310, y4 + 322, 70, C.drift);

// Lane 5: Consented catch activity.
const y5 = 2440;
lane(y5, "CONSENTED CATCH ACTIVITY", "Optional fisheries purpose\nNever sent over LoRa", C.fish, C.fishFill);
const fStart = terminator("f-start", "User opts in", 310, y5 + 175, 250, 110, C.fishFill, C.fish);
const fToken = decision("f-token", "Valid vessel\ndevice token?", 610, y5 + 150, 250, 160, C.branchFill, C.fish);
const fReject = terminator("f-reject", "Reject request", 610, y5 + 366, 250, 82, C.neutralFill, C.fish, { titleSize: 13 });
const fInput = data("f-input", "Catch log", "Species, weight, time, coarse place, consent", 920, y5 + 160, 330, 140, C.fishFill, C.fish);
const fValidate = process("f-validate", "Validate and store", "Separate fisheries domain", 1300, y5 + 165, 300, 130, C.backendFill, C.backend);
const fStore = store("f-store", "PostgreSQL", "Private catch record and consent", 1650, y5 + 155, 300, 150, C.backendFill, C.backend);
const fConsent = decision("f-consent", "Consent to coarse\nactivity sharing?", 2000, y5 + 150, 260, 160, C.branchFill, C.fish);
const fPrivate = terminator("f-private", "Keep private record only", 2000, y5 + 366, 260, 82, C.neutralFill, C.fish, { titleSize: 13 });
const fAggregate = process("f-aggregate", "Coarse aggregation", "Recent time window and broad grid cell", 2320, y5 + 165, 310, 130, C.fishFill, C.fish);
const fThreshold = decision("f-threshold", "Independent reporter\nthreshold met?", 2680, y5 + 150, 270, 160, C.branchFill, C.fish);
const fWithhold = data("f-withhold", "Cell withheld", "Insufficient independent reports", 2680, y5 + 348, 270, 118, C.neutralFill, C.fish, { titleSize: "15pt", bodySize: "10.5pt" });
const fWithholdEnd = terminator("f-withhold-end", "Retry after more reports", 3000, y5 + 366, 270, 82, C.neutralFill, C.fish, { titleSize: 13 });
const fCell = data("f-cell", "Coarse activity cell", "Recent activity; no exact vessel position", 3010, y5 + 160, 330, 140, C.fishFill, C.fish);
const fApi = process("f-api", "Public REST output", "Privacy-filtered activity only", 3390, y5 + 165, 300, 130, C.backendFill, C.backend);
const fSurface = process("f-surface", "Mobile and LGU/BFAR view", "No guaranteed catch claim", 3740, y5 + 165, 320, 130, C.outputFill, C.output);
const fEnd = terminator("f-end", "Optional fisheries insight", 4110, y5 + 175, 280, 110, C.outputFill, C.output);

connector("f-1", fStart, fToken, C.fish, { fromSide: "right", toSide: "left" });
connector("f-token-no", fToken, fReject, C.fish, { fromSide: "bottom", toSide: "top", dashed: true });
connector("f-token-yes", fToken, fInput, C.fish, { fromSide: "right", toSide: "left" });
connector("f-input-validate", fInput, fValidate, C.fish, { fromSide: "right", toSide: "left" });
connector("f-validate-store", fValidate, fStore, C.backend, { fromSide: "right", toSide: "left" });
connector("f-store-consent", fStore, fConsent, C.fish, { fromSide: "right", toSide: "left" });
connector("f-consent-no", fConsent, fPrivate, C.fish, { fromSide: "bottom", toSide: "top", dashed: true });
connector("f-consent-yes", fConsent, fAggregate, C.fish, { fromSide: "right", toSide: "left" });
connector("f-aggregate-threshold", fAggregate, fThreshold, C.fish, { fromSide: "right", toSide: "left" });
connector("f-threshold-no", fThreshold, fWithhold, C.fish, { fromSide: "bottom", toSide: "top", dashed: true });
connector("f-withhold-end-link", fWithhold, fWithholdEnd, C.fish, { fromSide: "right", toSide: "left", dashed: true });
connector("f-threshold-yes", fThreshold, fCell, C.fish, { fromSide: "right", toSide: "left" });
connector("f-cell-api", fCell, fApi, C.backend, { fromSide: "right", toSide: "left" });
connector("f-api-surface", fApi, fSurface, C.output, { fromSide: "right", toSide: "left" });
connector("f-surface-end", fSurface, fEnd, C.output, { fromSide: "right", toSide: "left" });
routeLabel("f-t-no", "NO", 700, y5 + 315, 60, C.fish);
routeLabel("f-t-yes", "YES", 850, y5 + 195, 70, C.fish);
routeLabel("f-c-no", "NO", 2100, y5 + 315, 60, C.fish);
routeLabel("f-c-yes", "YES", 2260, y5 + 195, 70, C.fish);
routeLabel("f-th-no", "NO", 2790, y5 + 315, 60, C.fish);
routeLabel("f-th-yes", "YES", 2950, y5 + 195, 70, C.fish);

// Legend and architectural constraints.
const legendY = 2995;
textBox("legend-title", "FLOWCHART LEGEND", 54, legendY + 8, 310, 42, 18, C.ink, true);
terminator("legend-oval", "Start / end", 360, legendY + 2, 210, 58, C.white, C.line, { titleSize: 12 });
process("legend-process", "Process", "", 610, legendY + 2, 210, 58, C.white, C.line, { titleSize: 12, shadow: false });
decision("legend-decision", "Decision", 860, legendY - 3, 140, 68, C.white, C.line, { titleSize: 11 });
data("legend-data", "Data input / output", "", 1040, legendY + 2, 245, 58, C.white, C.line, { titleSize: 11, shadow: false });
store("legend-store", "Data store", "", 1325, legendY - 2, 200, 66, C.white, C.line, { titleSize: "11pt", bodySize: "8pt", shadow: false });
const legendDot = dotConnector("legend-dot", "S1", 1570, legendY + 7, C.backend);
textBox("legend-dot-label", "Matched connector IDs continue a route without a crossing", 1628, legendY - 1, 555, 66, 12, C.muted);
textBox("legend-lines", "Solid: active software path    Dashed: optional, unavailable or field-dependent path", 2200, legendY + 2, 1000, 58, 13, C.muted, true, "center");

const statement = process("principles", "NON-NEGOTIABLE ARCHITECTURE RULES", "Manual SOS never depends on AI. Delivery states reflect evidence. Models advise authorized humans. Catch sharing stays optional and coarse.", 3260, legendY - 2, 1880, 74, "#FFF9EB", "#C18A20", { titleSize: "14pt", bodySize: "11pt", shadow: false });

textBox("footer", "AqOne technical architecture | Source of record: repository contracts and current implementation | One page, native editable PowerPoint shapes", 54, 3305, 5090, 42, 12.5, C.muted, false, "center");

slide.speakerNotes.textFrame.setText(
  "Sources: docs/00_START_HERE.md; docs/02_LOAM_PACKET_SPEC.md; docs/03_PHONE_BUOY_WIFI.md; docs/04_INGEST_API.md; docs/05_PUBLIC_API.md; docs/06_DELIVERY_STATES.md; docs/07_SCOPE_OUT.md; docs/17_AI_EXPLAINED_SIMPLY.md; docs/45_AI_PROSPECTIVE_EVALUATION_AND_CLAIMS.md; docs/55_HYBRID_TRANSPORT_ARCHITECTURE_DECISION.md; Aqone_PRD (2).md; current backend, mobile, gateway and firmware implementation. The diagram distinguishes active software paths from optional or field-dependent paths."
);

const candidatePath = path.join(stagingDir, "aqone-aggregated-architecture-candidate.pptx");
await (await PresentationFile.exportPptx(deck)).save(candidatePath);
const preview = await deck.export({ slide, format: "png", scale: 0.75 });
const previewPath = path.join(buildDir, "aqone-aggregated-architecture.png");
await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));
const layout = await slide.export({ format: "layout" });
await fs.writeFile(path.join(buildDir, "aqone-aggregated-architecture.layout.json"), await layout.text());

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
  layoutArgs: ["--expected-slide-size-emu", "49530000,32385000", "--validate-heading-fit"],
  fontPolicy: { basis: "design", families: [font] },
  verifyArtifactToolImport: true,
  receiptPath: path.join(stagingDir, "AqOne_Aggregated_Technical_Architecture_Editable.validation.json"),
});

console.log(JSON.stringify({ finalPath, previewPath, font, result }, null, 2));
