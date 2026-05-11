// Lightning presentation slide deck for SEC Filing Risk Extractor.
// 2-3 minute talk, 6 slides covering Context / Solution / Evaluation / Artifact.

const pptxgen = require("pptxgenjs");

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.author = "Wilson Liu";
pres.title = "SEC Filing Risk Extractor";

// Midnight Executive palette (navy / ice blue / white) - serious finance feel
const NAVY = "1E2761";
const ICE = "CADCFC";
const WHITE = "FFFFFF";
const ACCENT = "E63946";    // crimson for "flagged" / signal
const TEAL = "2A9D8F";      // for "matched / quiet" positive signal
const MUTED = "4A4E69";
const GREY = "8A8FA3";

// --------- Slide 1: Title ---------
const s1 = pres.addSlide();
s1.background = { color: NAVY };

s1.addText("SEC Filing Risk", {
  x: 0.6, y: 1.6, w: 9, h: 0.8,
  fontSize: 48, fontFace: "Georgia", color: WHITE, bold: true,
  margin: 0,
});
s1.addText("Extractor", {
  x: 0.6, y: 2.3, w: 9, h: 0.8,
  fontSize: 48, fontFace: "Georgia", color: ICE, bold: true, italic: true,
  margin: 0,
});

s1.addText("Surfacing thesis-killer signals buried in 10-K disclosure language", {
  x: 0.6, y: 3.4, w: 9, h: 0.5,
  fontSize: 18, fontFace: "Calibri", color: ICE,
  margin: 0,
});

s1.addText([
  { text: "Wilson Liu", options: { bold: true, color: WHITE } },
  { text: "  ·  GenAI Final Project  ·  May 2026", options: { color: ICE } },
], {
  x: 0.6, y: 4.7, w: 9, h: 0.4,
  fontSize: 12, fontFace: "Calibri",
  margin: 0,
});

// --------- Slide 2: Context / user / problem ---------
const s2 = pres.addSlide();
s2.background = { color: WHITE };

s2.addText("The problem", {
  x: 0.6, y: 0.4, w: 9, h: 0.5,
  fontSize: 28, fontFace: "Georgia", color: NAVY, bold: true,
  margin: 0,
});

s2.addText("Most blow-ups had warning signs in plain sight — diluted in 80 pages of mostly-identical text.", {
  x: 0.6, y: 1.05, w: 9, h: 0.5,
  fontSize: 15, fontFace: "Calibri", color: MUTED, italic: true,
  margin: 0,
});

// Three example callouts in cards
const examples = [
  { name: "SVB", year: "2021 → 2022", what: "Interest-rate risk language escalated quietly" },
  { name: "Wirecard", year: "Pre-collapse", what: "Audit-committee disclosures shifted" },
  { name: "Luckin", year: "Pre-restatement", what: "Revenue-recognition disclosures expanded" },
];
examples.forEach((ex, i) => {
  const x = 0.6 + i * 3.0;
  s2.addShape(pres.shapes.RECTANGLE, {
    x, y: 1.7, w: 2.7, h: 1.5,
    fill: { color: NAVY },
    line: { color: NAVY, width: 0 },
  });
  s2.addText(ex.name, {
    x: x + 0.2, y: 1.85, w: 2.3, h: 0.4,
    fontSize: 18, fontFace: "Georgia", color: WHITE, bold: true, margin: 0,
  });
  s2.addText(ex.year, {
    x: x + 0.2, y: 2.25, w: 2.3, h: 0.3,
    fontSize: 11, fontFace: "Calibri", color: ICE, margin: 0,
  });
  s2.addText(ex.what, {
    x: x + 0.2, y: 2.6, w: 2.3, h: 0.6,
    fontSize: 11, fontFace: "Calibri", color: WHITE, margin: 0,
  });
});

s2.addText("The user is a buy-side analyst with 10–30 active positions.", {
  x: 0.6, y: 3.55, w: 9, h: 0.4,
  fontSize: 14, fontFace: "Calibri", color: NAVY, bold: true, margin: 0,
});

s2.addText("Each quarter, when a covered company files a new 10-Q or 10-K, they need to answer:", {
  x: 0.6, y: 3.95, w: 9, h: 0.4,
  fontSize: 13, fontFace: "Calibri", color: MUTED, margin: 0,
});

s2.addShape(pres.shapes.RECTANGLE, {
  x: 0.6, y: 4.45, w: 8.8, h: 0.7,
  fill: { color: ICE },
  line: { color: ICE, width: 0 },
});
s2.addText('"Has this company\'s own characterization of risk meaningfully changed since I underwrote this position?"', {
  x: 0.8, y: 4.45, w: 8.4, h: 0.7,
  fontSize: 14, fontFace: "Georgia", color: NAVY, italic: true, valign: "middle",
  margin: 0,
});

// --------- Slide 3: Solution and design ---------
const s3 = pres.addSlide();
s3.background = { color: WHITE };

s3.addText("Solution and design", {
  x: 0.6, y: 0.4, w: 9, h: 0.5,
  fontSize: 28, fontFace: "Georgia", color: NAVY, bold: true,
  margin: 0,
});

s3.addText("Streamlit app that takes two filings and returns a ranked, decision-ready summary of meaningful changes.", {
  x: 0.6, y: 1.05, w: 9, h: 0.5,
  fontSize: 14, fontFace: "Calibri", color: MUTED,
  margin: 0,
});

// Pipeline boxes with arrows
const pipeline = [
  { label: "PARSE", desc: "Risk Factors → chunks" },
  { label: "ALIGN", desc: "TF-IDF cosine\npairing" },
  { label: "CLASSIFY", desc: "Claude + chain-of-thought\nverdict per pair" },
  { label: "RANK", desc: "Sorted by severity\nwith rationale" },
];
const pipeY = 1.85;
const boxW = 2.05;
const gap = 0.18;
const startX = 0.6;
pipeline.forEach((step, i) => {
  const x = startX + i * (boxW + gap);
  s3.addShape(pres.shapes.RECTANGLE, {
    x, y: pipeY, w: boxW, h: 1.5,
    fill: { color: WHITE },
    line: { color: NAVY, width: 1.5 },
  });
  s3.addText(step.label, {
    x: x + 0.05, y: pipeY + 0.15, w: boxW - 0.1, h: 0.4,
    fontSize: 14, fontFace: "Calibri", color: NAVY, bold: true,
    align: "center", margin: 0,
  });
  s3.addText(step.desc, {
    x: x + 0.05, y: pipeY + 0.6, w: boxW - 0.1, h: 0.85,
    fontSize: 11, fontFace: "Calibri", color: MUTED, align: "center", margin: 0,
  });
  if (i < pipeline.length - 1) {
    s3.addShape(pres.shapes.LINE, {
      x: x + boxW + 0.01, y: pipeY + 0.75,
      w: gap - 0.02, h: 0,
      line: { color: GREY, width: 1.5 },
    });
  }
});

// Course concepts
s3.addText("Course concepts integrated", {
  x: 0.6, y: 3.7, w: 9, h: 0.4,
  fontSize: 16, fontFace: "Georgia", color: NAVY, bold: true,
  margin: 0,
});

const concepts = [
  {
    label: "RAG: chunking + embeddings",
    detail: "TF-IDF char-bigram alignment of current chunks → prior counterparts. Robust to reordering.",
  },
  {
    label: "Chain-of-thought",
    detail: "Classifier reasons step-by-step before producing structured verdict. Trace exposed in UI for audit.",
  },
];
concepts.forEach((c, i) => {
  const x = 0.6 + i * 4.5;
  s3.addShape(pres.shapes.RECTANGLE, {
    x, y: 4.2, w: 4.3, h: 1.0,
    fill: { color: ICE },
    line: { color: ICE, width: 0 },
  });
  s3.addText(c.label, {
    x: x + 0.15, y: 4.27, w: 4.0, h: 0.35,
    fontSize: 13, fontFace: "Calibri", color: NAVY, bold: true, margin: 0,
  });
  s3.addText(c.detail, {
    x: x + 0.15, y: 4.6, w: 4.0, h: 0.6,
    fontSize: 11, fontFace: "Calibri", color: MUTED, margin: 0,
  });
});

// --------- Slide 4: Evaluation and results ---------
const s4 = pres.addSlide();
s4.background = { color: WHITE };

s4.addText("Evaluation: system vs. plain-diff baseline", {
  x: 0.6, y: 0.4, w: 9, h: 0.5,
  fontSize: 26, fontFace: "Georgia", color: NAVY, bold: true,
  margin: 0,
});

s4.addText("3 stratified test cases. Ground truth manually labeled.", {
  x: 0.6, y: 1.0, w: 9, h: 0.4,
  fontSize: 13, fontFace: "Calibri", color: MUTED, italic: true,
  margin: 0,
});

// Results table
const tableData = [
  [
    { text: "Test case", options: { fill: { color: NAVY }, color: WHITE, bold: true, fontSize: 12 } },
    { text: "Description", options: { fill: { color: NAVY }, color: WHITE, bold: true, fontSize: 12 } },
    { text: "Ground truth", options: { fill: { color: NAVY }, color: WHITE, bold: true, fontSize: 12, align: "center" } },
    { text: "System flagged", options: { fill: { color: NAVY }, color: WHITE, bold: true, fontSize: 12, align: "center" } },
    { text: "Diff hunks", options: { fill: { color: NAVY }, color: WHITE, bold: true, fontSize: 12, align: "center" } },
  ],
  [
    { text: "svb_style", options: { bold: true, color: NAVY } },
    { text: "Known thesis-killer pattern", options: { color: MUTED, fontSize: 11 } },
    { text: "5", options: { align: "center", bold: true, color: NAVY } },
    { text: "5", options: { align: "center", bold: true, color: TEAL } },
    { text: "7", options: { align: "center", color: GREY } },
  ],
  [
    { text: "routine", options: { bold: true, color: NAVY } },
    { text: "Cosmetic edits only — should be quiet", options: { color: MUTED, fontSize: 11 } },
    { text: "0", options: { align: "center", bold: true, color: NAVY } },
    { text: "0", options: { align: "center", bold: true, color: TEAL } },
    { text: "2", options: { align: "center", color: ACCENT, bold: true } },
  ],
  [
    { text: "restructured", options: { bold: true, color: NAVY } },
    { text: "Reordered + 1 buried signal", options: { color: MUTED, fontSize: 11 } },
    { text: "1", options: { align: "center", bold: true, color: NAVY } },
    { text: "1", options: { align: "center", bold: true, color: TEAL } },
    { text: "4", options: { align: "center", color: GREY } },
  ],
];

s4.addTable(tableData, {
  x: 0.6, y: 1.55, w: 8.8,
  colW: [1.4, 3.2, 1.4, 1.4, 1.4],
  rowH: [0.4, 0.45, 0.45, 0.45],
  border: { pt: 1, color: "DADADA" },
  fontFace: "Calibri", fontSize: 12,
});

// Key insight callout
s4.addShape(pres.shapes.RECTANGLE, {
  x: 0.6, y: 3.85, w: 8.8, h: 1.3,
  fill: { color: ICE },
  line: { color: ICE, width: 0 },
});
s4.addText("The most important comparison is the 'routine' row.", {
  x: 0.85, y: 3.95, w: 8.3, h: 0.4,
  fontSize: 14, fontFace: "Calibri", color: NAVY, bold: true, margin: 0,
});
s4.addText("Ground truth says zero meaningful changes. Diff still flags 2 hunks of pure noise that the analyst has to read and dismiss. The LLM-based system stays quiet — which is exactly what a useful tool does in the routine case.", {
  x: 0.85, y: 4.35, w: 8.3, h: 0.75,
  fontSize: 12, fontFace: "Calibri", color: MUTED, margin: 0,
});

// Honesty footer
s4.addText("Mock-mode results shown. Real-Claude run requires API key — see README for `--provider anthropic` reproduction steps.", {
  x: 0.6, y: 5.25, w: 8.8, h: 0.3,
  fontSize: 9, fontFace: "Calibri", color: GREY, italic: true, margin: 0,
});

// --------- Slide 5: Artifact snapshot ---------
const s5 = pres.addSlide();
s5.background = { color: WHITE };

s5.addText("Artifact snapshot — SVB case output", {
  x: 0.6, y: 0.4, w: 9, h: 0.5,
  fontSize: 26, fontFace: "Georgia", color: NAVY, bold: true,
  margin: 0,
});

s5.addText("What the analyst sees in the Streamlit UI for the svb_style test case:", {
  x: 0.6, y: 1.0, w: 9, h: 0.35,
  fontSize: 12, fontFace: "Calibri", color: MUTED, italic: true,
  margin: 0,
});

const verdicts = [
  { tag: "ESCALATION", sev: "high", topic: "Interest Rate Environment", note: "'may' → 'are likely to'; new explicit Fed-rate language", color: ACCENT },
  { tag: "ESCALATION", sev: "high", topic: "Deposit Concentration", note: "New language: VC funding decline → deposit outflows", color: ACCENT },
  { tag: "SCOPE EXPANSION", sev: "high", topic: "Liquidity", note: "+309 chars; FHLB advances, securities sale at loss", color: ACCENT },
  { tag: "NEW", sev: "high", topic: "Held-to-Maturity Securities Portfolio", note: "Brand-new risk factor, not in prior filing", color: ACCENT },
  { tag: "REMOVED", sev: "med", topic: "Reputation", note: "Was in prior, absent in current", color: MUTED },
];

verdicts.forEach((v, i) => {
  const y = 1.5 + i * 0.55;
  s5.addShape(pres.shapes.RECTANGLE, {
    x: 0.6, y, w: 0.12, h: 0.45,
    fill: { color: v.color },
    line: { color: v.color, width: 0 },
  });
  s5.addText(v.tag, {
    x: 0.85, y, w: 1.5, h: 0.25,
    fontSize: 10, fontFace: "Calibri", color: v.color, bold: true, margin: 0,
  });
  s5.addText(v.topic, {
    x: 0.85, y: y + 0.22, w: 4.5, h: 0.25,
    fontSize: 13, fontFace: "Calibri", color: NAVY, bold: true, margin: 0,
  });
  s5.addText(v.note, {
    x: 5.4, y: y + 0.07, w: 4.0, h: 0.4,
    fontSize: 11, fontFace: "Calibri", color: MUTED, valign: "middle", margin: 0,
  });
});

// Bottom note
s5.addShape(pres.shapes.RECTANGLE, {
  x: 0.6, y: 4.35, w: 8.8, h: 0.85,
  fill: { color: NAVY },
});
s5.addText("3 cosmetic items reviewed and silently dismissed.", {
  x: 0.85, y: 4.42, w: 8.4, h: 0.35,
  fontSize: 12, fontFace: "Calibri", color: WHITE, bold: true, margin: 0,
});
s5.addText("Each flagged item expandable in the UI to show side-by-side prior/current text and the model's chain-of-thought.", {
  x: 0.85, y: 4.78, w: 8.4, h: 0.35,
  fontSize: 11, fontFace: "Calibri", color: ICE, margin: 0,
});

// --------- Slide 6: Where it breaks down ---------
const s6 = pres.addSlide();
s6.background = { color: NAVY };

s6.addText("Where the project breaks down", {
  x: 0.6, y: 0.5, w: 9, h: 0.6,
  fontSize: 28, fontFace: "Georgia", color: WHITE, bold: true,
  margin: 0,
});

s6.addText("Honesty matters more than the demo.", {
  x: 0.6, y: 1.15, w: 9, h: 0.4,
  fontSize: 14, fontFace: "Calibri", color: ICE, italic: true,
  margin: 0,
});

const limits = [
  {
    title: "Mock results aren't real evaluation",
    body: "The mock classifier is keyed on the same patterns I embedded in the test data. 1.00 precision in mock mode is partially circular.",
  },
  {
    title: "Test set is small and synthetic",
    body: "3 hand-written pairs. Production evaluation would expand to 15+ pairs across industries with real EDGAR filings.",
  },
  {
    title: "Reads language, not business reality",
    body: "A company can rewrite disclosure conservatively even as the business deteriorates. The tool flags shifts; the analyst still has to interpret them.",
  },
  {
    title: "The most dangerous failure: false confidence",
    body: "If the system flags nothing, an analyst might conclude 'all clear' — even though the system may have missed it. The UI explicitly frames outputs as 'what we found,' not 'what is there to find.'",
    accent: true,
  },
];

limits.forEach((lim, i) => {
  const y = 1.65 + i * 0.85;
  s6.addText(lim.title, {
    x: 0.6, y, w: 8.8, h: 0.3,
    fontSize: 14, fontFace: "Calibri",
    color: lim.accent ? ACCENT : WHITE, bold: true, margin: 0,
  });
  s6.addText(lim.body, {
    x: 0.6, y: y + 0.3, w: 8.8, h: 0.5,
    fontSize: 11, fontFace: "Calibri", color: ICE, margin: 0,
  });
});

// --- Save ---
pres.writeFile({ fileName: "/home/claude/sec-filing-risk-extractor/slides/presentation.pptx" })
  .then((file) => console.log(`Wrote: ${file}`));
