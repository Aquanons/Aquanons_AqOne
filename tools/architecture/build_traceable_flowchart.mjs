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
const finalPath = path.join(workspaceDir, "artifacts", "architecture", "AqOne_Editable_Architecture_Flowchart_v6_Traceable.pptx");
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
const deck = Presentation.create({ slideSize: { width: 1600, height: 900 } });

const C = {
  bg: "#FBFCFE",
  ink: "#172033",
  muted: "#5B6677",
  line: "#2F3A4D",
  edge: "#D9F1F0",
  edgeLine: "#177A78",
  backend: "#DDE7FF",
  backendLine: "#365DB5",
  ai: "#E9DBFA",
  aiLine: "#7552A8",
  safety: "#FFD7DA",
  safetyLine: "#C73F4D",
  output: "#D6F5FA",
  outputLine: "#188090",
  external: "#FFE8C5",
  externalLine: "#C5872D",
  fisheries: "#D9F2E2",
  fisheriesLine: "#2F7D54",
  slateBand: "#F2F5F8",
  white: "#FFFFFF",
  status: "#FFF4CC",
  returnLine: "#345DB3",
};

function addText(slide, name, text, left, top, width, height, size, color = C.ink, bold = false, align = "left") {
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

function addTitle(slide, title, subtitle, page) {
  addText(slide, `title-${page}`, title, 54, 24, 980, 48, 34, C.ink, true);
  addText(slide, `subtitle-${page}`, subtitle, 56, 72, 1120, 30, 16, C.muted);
  const marker = slide.shapes.add({
    geometry: "roundRect",
    name: `page-marker-${page}`,
    position: { left: 1398, top: 30, width: 142, height: 42 },
    fill: C.status,
    line: { style: "solid", fill: "#D4B23C", width: 1.2 },
    borderRadius: "rounded-full",
  });
  marker.text = `${page} OF 3`;
  marker.text.style = { typeface: font, fontSize: 12, bold: true, color: C.ink, alignment: "center", verticalAlignment: "middle" };
}

function addBand(slide, name, title, top, height, fill, lineColor) {
  const band = slide.shapes.add({
    geometry: "roundRect",
    name,
    position: { left: 42, top, width: 1516, height },
    fill,
    line: { style: "solid", fill: lineColor, width: 1.2 },
    borderRadius: 12,
  });
  band.sendToBack();
  addText(slide, `${name}-label`, title, 58, top + 8, 250, 28, 17, lineColor, true);
  return band;
}

function addBox(slide, name, title, subtitle, left, top, width, height, fill, lineColor, options = {}) {
  const box = slide.shapes.add({
    geometry: "roundRect",
    name,
    position: { left, top, width, height },
    fill,
    line: { style: "solid", fill: lineColor, width: options.lineWidth ?? 1.6 },
    borderRadius: options.radius ?? 12,
    shadow: options.shadow === false ? "shadow-none" : "shadow-sm",
  });
  box.text = [
    [{ run: title, textStyle: { typeface: font, fontSize: options.titleSize ?? "15pt", bold: true, color: C.ink } }],
    [{ run: subtitle, textStyle: { typeface: font, fontSize: options.bodySize ?? "9.5pt", color: C.muted } }],
  ];
  box.text.style = {
    typeface: font,
    alignment: "center",
    verticalAlignment: "middle",
    autoFit: "shrinkText",
    insets: { top: 7, right: 8, bottom: 7, left: 8 },
  };
  return box;
}

function addPill(slide, name, text, left, top, width, fill, lineColor, size = 11) {
  const pill = slide.shapes.add({
    geometry: "roundRect",
    name,
    position: { left, top, width, height: 34 },
    fill,
    line: { style: "solid", fill: lineColor, width: 1.2 },
    borderRadius: "rounded-full",
  });
  pill.text = text;
  pill.text.style = { typeface: font, fontSize: size, bold: true, color: C.ink, alignment: "center", verticalAlignment: "middle", autoFit: "shrinkText", insets: { top: 2, right: 6, bottom: 2, left: 6 } };
  return pill;
}

function addStep(slide, box, number, color) {
  const dot = slide.shapes.add({
    geometry: "ellipse",
    name: `step-${number}`,
    position: { left: box.position.left - 15, top: box.position.top - 14, width: 40, height: 40 },
    fill: color,
    line: { style: "solid", fill: C.white, width: 2 },
  });
  dot.text = String(number);
  dot.text.style = { typeface: font, fontSize: 12.5, bold: true, color: C.white, alignment: "center", verticalAlignment: "middle", autoFit: "shrinkText", insets: { top: 1, right: 1, bottom: 1, left: 1 } };
  return dot;
}

function connect(slide, name, from, to, options = {}) {
  const connector = slide.shapes.connect(from, to, {
    kind: options.kind ?? "straight",
    fromSide: options.fromSide,
    toSide: options.toSide,
    line: { style: options.style ?? "solid", fill: options.color ?? C.line, width: options.width ?? 2.4 },
    head: options.bidirectional ? { type: "triangle", width: "sm", length: "sm" } : { type: "none" },
    tail: { type: "triangle", width: "sm", length: "sm" },
  });
  connector.name = name;
  connector.bringToFront();
  return connector;
}

function addRouteLabel(slide, name, text, left, top, width, color) {
  return addText(slide, name, text, left, top, width, 26, 10.5, color, true, "center");
}

function addFooter(slide, page) {
  addText(slide, `footer-left-${page}`, "All shapes and connectors are editable PowerPoint objects", 54, 852, 600, 26, 10.5, C.muted);
  addText(slide, `footer-right-${page}`, "Solid line: software path   Dashed line: optional or hardware path awaiting field verification", 770, 852, 770, 26, 10.5, C.muted, false, "right");
}

const slide1 = deck.slides.add();
slide1.background.fill = C.bg;
addTitle(slide1, "AqOne System Data Paths", "Separate tracks for SOS uplink, optional relay, direct internet and responder return", 1);

addBand(slide1, "uplink-band", "Primary SOS uplink", 120, 230, "#FFF8F8", C.safetyLine);
const s1Phone = addBox(slide1, "s1-phone", "Fisher phone", "SQLite outbox\nState: SAVED", 72, 200, 205, 105, C.safety, C.safetyLine);
const s1Pod = addBox(slide1, "s1-pod", "Boat pod", "Flash queue\nState: RELAYED", 355, 200, 205, 105, C.edge, C.edgeLine);
const s1Gateway = addBox(slide1, "s1-gateway", "Shore gateway", "Signature verification\nInternet bridge", 690, 200, 205, 105, C.edge, C.edgeLine);
const s1Backend = addBox(slide1, "s1-backend", "FastAPI and PostgreSQL", "Validate, deduplicate, persist\nState: DELIVERED", 1025, 200, 225, 105, C.backend, C.backendLine);
const s1Dashboard = addBox(slide1, "s1-dashboard", "MDRRMO dashboard", "Displays SOS\nResponder authority", 1330, 200, 205, 105, C.output, C.outputLine);
connect(slide1, "s1-uplink-1", s1Phone, s1Pod, { fromSide: "right", toSide: "left", color: C.safetyLine });
connect(slide1, "s1-uplink-2", s1Pod, s1Gateway, { fromSide: "right", toSide: "left", color: C.safetyLine, style: "dashed" });
connect(slide1, "s1-uplink-3", s1Gateway, s1Backend, { fromSide: "right", toSide: "left", color: C.safetyLine });
connect(slide1, "s1-uplink-4", s1Backend, s1Dashboard, { fromSide: "right", toSide: "left", color: C.safetyLine });
addRouteLabel(slide1, "s1-label-wifi", "LOCAL WIFI HTTP", 275, 166, 82, C.safetyLine);
addRouteLabel(slide1, "s1-label-lora", "DIRECT LoRa", 565, 166, 120, C.safetyLine);
addRouteLabel(slide1, "s1-label-https", "AUTHENTICATED HTTPS", 888, 166, 138, C.safetyLine);
addRouteLabel(slide1, "s1-label-poll", "REST POLLING", 1242, 166, 88, C.safetyLine);

addBand(slide1, "relay-band", "Optional relay route", 372, 130, "#F4FBFA", C.edgeLine);
const s1RelayPod = addBox(slide1, "s1-relay-pod", "Boat pod", "Direct link unavailable", 355, 414, 205, 66, C.edge, C.edgeLine, { titleSize: "12pt", bodySize: "8pt", shadow: false });
const s1Relay = addBox(slide1, "s1-relay", "Relay buoy", "TTL and seen-set forwarding", 690, 414, 205, 66, C.edge, C.edgeLine, { titleSize: "12pt", bodySize: "8pt", shadow: false });
const s1RelayGateway = addBox(slide1, "s1-relay-gateway", "Shore gateway", "Receives relayed frame", 1025, 414, 225, 66, C.edge, C.edgeLine, { titleSize: "12pt", bodySize: "8pt", shadow: false });
connect(slide1, "s1-relay-1", s1RelayPod, s1Relay, { fromSide: "right", toSide: "left", color: C.edgeLine, style: "dashed" });
connect(slide1, "s1-relay-2", s1Relay, s1RelayGateway, { fromSide: "right", toSide: "left", color: C.edgeLine, style: "dashed" });
addRouteLabel(slide1, "s1-relay-caption-1", "LoRa", 585, 386, 58, C.edgeLine);
addRouteLabel(slide1, "s1-relay-caption-2", "LoRa", 920, 386, 58, C.edgeLine);

addBand(slide1, "internet-band", "Direct internet route", 524, 105, "#F7F9FF", C.backendLine);
const s1InternetPhone = addBox(slide1, "s1-internet-phone", "Fisher phone", "Internet available", 72, 559, 205, 52, C.backend, C.backendLine, { titleSize: "11pt", bodySize: "7.5pt", shadow: false });
const s1InternetBackend = addBox(slide1, "s1-internet-backend", "FastAPI", "Direct SOS ingest", 1025, 559, 225, 52, C.backend, C.backendLine, { titleSize: "11pt", bodySize: "7.5pt", shadow: false });
connect(slide1, "s1-internet-route", s1InternetPhone, s1InternetBackend, { fromSide: "right", toSide: "left", color: C.backendLine });
addRouteLabel(slide1, "s1-internet-label", "HTTPS WHEN INTERNET IS AVAILABLE", 548, 531, 240, C.backendLine);

addBand(slide1, "return-band", "Responder return path", 652, 175, "#F5F8FF", C.returnLine);
const returnXs = [1330, 1025, 690, 355, 72];
const returnTitles = ["Dashboard", "Backend", "Gateway", "Boat pod", "Fisher phone"];
const returnSubs = ["Acknowledge and ETA", "Persist response", "Queue downlink", "Cache for phone", "State: ACKNOWLEDGED"];
const returnBoxes = returnTitles.map((title, index) => addBox(slide1, `s1-return-${index}`, title, returnSubs[index], returnXs[index], 708, index === 1 ? 225 : 205, 70, C.output, C.returnLine, { titleSize: "12pt", bodySize: "8pt", shadow: false }));
for (let i = 0; i < returnBoxes.length - 1; i += 1) {
  connect(slide1, `s1-return-link-${i}`, returnBoxes[i], returnBoxes[i + 1], { fromSide: "left", toSide: "right", color: C.returnLine, style: i >= 1 ? "dashed" : "solid" });
}
addRouteLabel(slide1, "s1-return-1", "WRITE", 1250, 674, 70, C.returnLine);
addRouteLabel(slide1, "s1-return-2", "BACKHAUL", 905, 674, 100, C.returnLine);
addRouteLabel(slide1, "s1-return-3", "LoRa DOWNLINK", 565, 674, 120, C.returnLine);
addRouteLabel(slide1, "s1-return-4", "LOCAL STATUS", 278, 674, 82, C.returnLine);
addFooter(slide1, 1);

slide1.speakerNotes.textFrame.setText("Sources: README.md; docs/55_HYBRID_TRANSPORT_ARCHITECTURE_DECISION.md; docs/06_DELIVERY_STATES.md; docs/04_INGEST_API.md; docs/05_PUBLIC_API.md.");

const slide2 = deck.slides.add();
slide2.background.fill = C.bg;
addTitle(slide2, "SOS Delivery and Acknowledgement", "Numbered sequence with separate uplink and return tracks", 2);

addBand(slide2, "s2-uplink-band", "Uplink to responders", 125, 310, "#FFF8F8", C.safetyLine);
const topX = [70, 370, 670, 970, 1270];
const topTitles = ["Phone saves SOS", "Pod queues SOS", "Gateway verifies", "Backend commits", "Dashboard displays"];
const topSubs = [
  "Write to SQLite before network attempt",
  "Accept before phone acknowledgement",
  "Verify signature and device identity",
  "Deduplicate and persist the incident",
  "Protected polling refreshes the feed",
];
const topBoxes = topTitles.map((title, index) => {
  const box = addBox(slide2, `s2-top-${index}`, title, topSubs[index], topX[index], 215, 230, 112, index === 0 ? C.safety : index < 3 ? C.edge : index === 3 ? C.backend : C.output, index === 0 ? C.safetyLine : index < 3 ? C.edgeLine : index === 3 ? C.backendLine : C.outputLine);
  addStep(slide2, box, index + 1, C.safetyLine);
  return box;
});
const uplinkLabels = ["LOCAL WIFI HTTP", "SIGNED LoAM FRAME", "AUTHENTICATED HTTPS", "REST POLLING"];
for (let i = 0; i < topBoxes.length - 1; i += 1) {
  connect(slide2, `s2-top-link-${i}`, topBoxes[i], topBoxes[i + 1], { fromSide: "right", toSide: "left", color: C.safetyLine, style: i === 1 ? "dashed" : "solid" });
  addRouteLabel(slide2, `s2-top-label-${i}`, uplinkLabels[i], topX[i] + 225, 173, 80, C.safetyLine);
}
addPill(slide2, "s2-state-saved", "SAVED", 105, 350, 160, C.safety, C.safetyLine);
addPill(slide2, "s2-state-relayed", "RELAYED", 405, 350, 160, C.edge, C.edgeLine);
addPill(slide2, "s2-state-delivered", "DELIVERED", 1005, 350, 160, C.backend, C.backendLine);

addBand(slide2, "s2-return-band", "Responder action and return", 468, 325, "#F5F8FF", C.returnLine);
const bottomX = [1270, 970, 670, 370, 70];
const bottomTitles = ["Responder acknowledges", "Backend stores response", "Gateway sends downlink", "Pod exposes status", "Phone reconciles"];
const bottomSubs = [
  "ETA, note and responder status",
  "Acknowledgement becomes authoritative",
  "Queue response when a radio path exists",
  "Phone reads cached acknowledgement",
  "Show ACKNOWLEDGED only after evidence",
];
const bottomBoxes = bottomTitles.map((title, index) => {
  const box = addBox(slide2, `s2-bottom-${index}`, title, bottomSubs[index], bottomX[index], 568, 230, 112, index === 0 ? C.external : index === 1 ? C.backend : index < 4 ? C.edge : C.output, index === 0 ? C.externalLine : index === 1 ? C.backendLine : index < 4 ? C.edgeLine : C.outputLine);
  addStep(slide2, box, index + 6, C.returnLine);
  return box;
});
connect(slide2, "s2-transition", topBoxes[4], bottomBoxes[0], { fromSide: "bottom", toSide: "top", color: C.returnLine, kind: "straight" });
for (let i = 0; i < bottomBoxes.length - 1; i += 1) {
  connect(slide2, `s2-bottom-link-${i}`, bottomBoxes[i], bottomBoxes[i + 1], { fromSide: "left", toSide: "right", color: C.returnLine, style: i >= 1 ? "dashed" : "solid" });
}
const returnLabels = ["PERSIST", "BACKHAUL", "LoRa DOWNLINK", "LOCAL STATUS"];
for (let i = 0; i < returnLabels.length; i += 1) {
  addRouteLabel(slide2, `s2-return-label-${i}`, returnLabels[i], bottomX[i + 1] + 226, 526, 74, C.returnLine);
}
addPill(slide2, "s2-state-ack", "ACKNOWLEDGED", 105, 712, 160, C.output, C.outputLine);
addText(slide2, "s2-honesty", "If no return path exists, the handset keeps its last proven state. It never invents delivery or acknowledgement.", 345, 722, 930, 36, 13, C.muted, true, "center");
addFooter(slide2, 2);
slide2.speakerNotes.textFrame.setText("Sources: docs/06_DELIVERY_STATES.md; docs/03_PHONE_BUOY_WIFI.md; docs/04_INGEST_API.md; backend/app/api/sos.py; firmware/buoy/AqOneBuoy/AqOneBuoy.ino.");

const slide3 = deck.slides.add();
slide3.background.fill = C.bg;
addTitle(slide3, "AqOne Processing Pipelines", "Each pipeline has its own lane, arrow color and output surface", 3);

const columnXs = [240, 500, 760, 1020, 1280];
const columnTitles = ["INPUT", "QUALITY AND PREPARATION", "MODEL OR CORE LOGIC", "DECISION WORKFLOW", "OUTPUT"];
for (let i = 0; i < columnTitles.length; i += 1) {
  addText(slide3, `s3-col-${i}`, columnTitles[i], columnXs[i], 114, i === 4 ? 245 : 215, 28, 11, C.muted, true, "center");
}

const lanes = [
  {
    key: "sos", y: 160, title: "MANUAL SOS", color: C.safetyLine, fill: C.safety,
    nodes: [
      ["Phone or pod SOS", "Human-triggered distress"],
      ["Validate and deduplicate", "Emergency intake remains unconditional"],
      ["Persist incident", "AI does not gate delivery"],
      ["Responder acknowledgement", "ETA, note and resolution"],
      ["Dashboard and phone", "Delivery state evidence"],
    ],
  },
  {
    key: "weather", y: 292, title: "ENVIRONMENTAL WARNING", color: C.aiLine, fill: C.ai,
    nodes: [
      ["Pressure and weather", "Fixed buoys plus Open-Meteo"],
      ["Quality and freshness", "Reject stale or insufficient input"],
      ["Squall and danger models", "Backend and browser inference"],
      ["Advisory review", "Official and human warnings take precedence"],
      ["Mobile and dashboard", "Warning with source and age"],
    ],
  },
  {
    key: "trip", y: 424, title: "TRIP ANOMALY", color: "#5B5CB8", fill: "#E4E3FA",
    nodes: [
      ["Contacts and trip history", "Routine vessel observations"],
      ["Causal history filter", "No future or candidate leakage"],
      ["Per-vessel profile", "Duration and route comparison"],
      ["Verification and escalation", "Silence alone does not prove distress"],
      ["Responder review queue", "Evidence and confidence"],
    ],
  },
  {
    key: "drift", y: 556, title: "DRIFT AND SEARCH", color: "#5361A8", fill: "#E1E7FA",
    nodes: [
      ["Confirmed incident", "Last reliable fix and object class"],
      ["Environmental forcing", "Wind, current and coastline"],
      ["Monte Carlo leeway", "Particle paths and uncertainty"],
      ["Search posterior update", "Negative search evidence"],
      ["Search contours", "50, 75 and 95 percent zones"],
    ],
  },
  {
    key: "catch", y: 688, title: "CONSENTED CATCH ACTIVITY", color: C.fisheriesLine, fill: C.fisheries,
    nodes: [
      ["Consented catch log", "Separate optional purpose"],
      ["Auth and validation", "Safety access remains independent"],
      ["Privacy aggregation", "Coarse cells and reporter threshold"],
      ["Recent activity surface", "No guaranteed catch claim"],
      ["Mobile and LGU view", "No exact public positions"],
    ],
  },
];

for (const lane of lanes) {
  const band = slide3.shapes.add({
    geometry: "roundRect",
    name: `s3-${lane.key}-band`,
    position: { left: 42, top: lane.y - 10, width: 1516, height: 112 },
    fill: "#FFFFFF",
    line: { style: "solid", fill: lane.color, width: 1 },
    borderRadius: 10,
  });
  band.sendToBack();
  addText(slide3, `s3-${lane.key}-title`, lane.title, 58, lane.y + 20, 155, 46, 14, lane.color, true, "left");
  const boxes = lane.nodes.map((node, index) => addBox(slide3, `s3-${lane.key}-${index}`, node[0], node[1], columnXs[index], lane.y + 4, index === 4 ? 235 : 210, 82, index === 4 ? C.output : lane.fill, index === 4 ? C.outputLine : lane.color, { titleSize: "11.5pt", bodySize: "7.7pt", shadow: false }));
  for (let i = 0; i < boxes.length - 1; i += 1) {
    connect(slide3, `s3-${lane.key}-link-${i}`, boxes[i], boxes[i + 1], { fromSide: "right", toSide: "left", color: lane.color, width: 2.2 });
  }
}

addText(slide3, "s3-boundary", "Manual SOS stays operational when every model is unavailable. Model outputs support authorized human decisions.", 300, 815, 1000, 30, 13, C.ink, true, "center");
addFooter(slide3, 3);
slide3.speakerNotes.textFrame.setText("Sources: docs/Aqone_PRD (2).md; docs/17_AI_EXPLAINED_SIMPLY.md; docs/45_AI_PROSPECTIVE_EVALUATION_AND_CLAIMS.md; docs/07_SCOPE_OUT.md.");

const candidatePath = path.join(stagingDir, "aqone-traceable-flowchart-candidate.pptx");
await (await PresentationFile.exportPptx(deck)).save(candidatePath);
for (let i = 0; i < deck.slides.items.length; i += 1) {
  const slide = deck.slides.items[i];
  const preview = await deck.export({ slide, format: "png", scale: 0.7 });
  await fs.writeFile(path.join(buildDir, `traceable-slide-${i + 1}.png`), new Uint8Array(await preview.arrayBuffer()));
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(path.join(buildDir, `traceable-slide-${i + 1}.layout.json`), await layout.text());
}

const result = await finalizePresentation({
  explicitTotalSlideCount: 3,
  requiredNativeTableOwnerSlides: [],
  requiredNativeChartOwnerSlides: [],
  workspaceDir,
  candidatePath,
  finalPath,
  pythonExecutable,
  integrityValidatorPath: path.join(skillDir, "container_tools", "inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(skillDir, "container_tools", "inspect_presentation_layout_geometry.py"),
  layoutArgs: ["--expected-slide-size-emu", "15240000,8572500", "--validate-heading-fit"],
  fontPolicy: { basis: "design", families: [font] },
  verifyArtifactToolImport: true,
  receiptPath: path.join(stagingDir, "AqOne_Editable_Architecture_Flowchart_v6_Traceable.validation.json"),
});

console.log(JSON.stringify({ finalPath, font, result }, null, 2));
