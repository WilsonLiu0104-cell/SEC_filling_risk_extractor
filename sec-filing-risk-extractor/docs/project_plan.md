# Project Plan: SEC Filing Risk Extractor

---

## 1. Project Title

**SEC Filing Risk Extractor** — Automated material risk identification, year-over-year language shift detection, and disclosure tone scoring from 10-K and 10-Q filings.

---

## 2. Target User, Workflow, and Business Value

**The pain this addresses.** Most major investment blow-ups — Silicon Valley Bank, Wirecard, Luckin Coffee, Evergrande — had warning signs sitting in plain sight in the company's own SEC disclosures *before* the stock broke. The signals weren't hidden; they were diluted. They appeared as small but meaningful shifts in how the company characterized a known risk: a sentence escalated from "may affect" to "could materially affect," a previously minor item promoted in the ordering, a new sub-clause added quietly to a paragraph an analyst had already read four times. Buried in an 80-page document and read alongside last quarter's near-identical version, these shifts are easy to miss. Once a position is on the book, almost no one fully re-reads the Risk Factors section each quarter — they skim, look for headlines, and move on.

**Who the user is:** A buy-side equity analyst with active positions in 10–30 names. Not a lawyer, not a compliance officer — someone who has already underwritten a thesis on each name and needs to know when the underlying disclosure picture has shifted enough to warrant a re-look.

**The recurring task and decision being supported:** Each quarter, when a covered company files a new 10-Q or 10-K, the analyst needs to answer one specific question: *"Has the company's own characterization of risk meaningfully changed since I last underwrote this position, and if so, does it affect my view?"* The workflow begins when the new filing drops on EDGAR and ends with a yes/no/maybe decision: keep the position as-is, flag it for re-review, or escalate to the PM.

**Why better performance on this workflow matters:** A single missed thesis-killer signal can cost a fund hundreds of basis points. Even one early warning flagged correctly per year — say, recognizing that SVB's interest-rate-risk language had escalated meaningfully between its 2021 and 2022 10-Ks — would justify the entire workflow. The cost of a false positive (one extra hour of re-reading a filing) is small; the cost of a false negative (missing a real signal) is large and asymmetric.

---

## 3. Problem Statement and GenAI Fit

**The task:** Given a newly-filed 10-K or 10-Q paired with the company's prior-period filing, identify whether the firm's characterization of its risks has *semantically* shifted in a way that would matter to an analyst with an existing position — and surface those shifts as a ranked, decision-ready summary.

The core unit of value is not the risk extraction itself; it is the *delta detection* across two long, mostly-identical documents.

**Why language models are essential here:** This problem is where general-purpose LLMs are genuinely well-suited and where simpler tools fail decisively. The system needs to:

- Read 60–150 pages of dense, semi-structured legal-financial prose with comprehension, not just keyword matching.
- Recognize that two paragraphs with very different surface text may describe the same underlying risk (one rewritten by counsel, one by IR).
- Recognize the inverse: that two paragraphs with nearly identical text may have one quietly inserted clause that changes the risk's meaning.
- Distinguish a meaningful semantic escalation ("may impact" → "is likely to materially impact") from cosmetic editorial changes ("the Company" → "we").
- Distinguish firm-specific language from industry-standard boilerplate that appears unchanged across all peers.

These are reading-comprehension and semantic-comparison tasks. They are exactly what current LLMs are good at, and exactly what every simpler approach fails at.

**Why a simpler tool is not enough:**

- *Plain text diff* (the obvious baseline a skeptical reader would propose): produces hundreds of trivial deletions and insertions per filing pair, with no signal-to-noise filtering. A reformatted paragraph looks identical to a substantive escalation. The output is unusable without a human reading every diff.
- *Keyword search:* cannot detect *new* risk language because the analyst doesn't know in advance which keywords to look for — that is the entire problem.
- *Manual reading:* this is the current state of the world, and it is exactly what the workflow has shown does not happen reliably for active positions across an analyst's coverage. Asking the analyst to "just read more carefully" is not a system.

The narrow, specific value of GenAI here is that it can read both filings, hold them in mind together, and tell the analyst what *meaningfully* changed — collapsing a task that humans systematically skip into one they can act on in five minutes.

---

## 4. Planned System Design and Baseline

### Architecture

The app will be built in Streamlit. The user provides **two filings** — a current-period 10-Q or 10-K and the corresponding prior-period filing for the same company — by uploading PDFs or by entering CIK + accession numbers (the SEC EDGAR API will fetch them). A single-filing mode will exist as a secondary use case (initial coverage, no prior to compare against), but the primary workflow is the pair.

The system then:

1. **Parses and chunks** each filing by section header (Item 1A for Risk Factors, Item 7 for MD&A), splitting each identified risk factor into its own chunk.
2. **Aligns risk factors across the two filings** using embedding similarity. Each current-period risk chunk is matched to its semantically nearest prior-period counterpart (or flagged as new if no match exceeds a similarity threshold; symmetrically, any prior-period risk with no current match is flagged as removed).
3. **Runs a chain-of-thought comparison pass** on each aligned pair, prompting the model to reason step-by-step about whether the language has *meaningfully* shifted (escalation, de-escalation, scope expansion, new sub-clause) versus cosmetic edits, before assigning a delta score and a short rationale.
4. **Filters by materiality and boilerplate flags** so the analyst sees only the changes that matter — not 80 minor edits.
5. **Produces a structured output**: a ranked delta table (risk name, change type, delta score, rationale, source text from both filings side-by-side), plus a tone score for the filing pair indicating overall direction of disclosure shift.

### Course Concepts Integrated

**1. RAG — Chunking, Embeddings, Semantic Alignment (Week 4)**
The 10-K Risk Factors section will be chunked at the individual risk-factor level (each distinct risk paragraph or cluster of paragraphs under a sub-header becomes one chunk). Chunks from both filings will be embedded using `text-embedding-3-small` (OpenAI) or an equivalent and stored in FAISS. Rather than top-k retrieval against a user query, embeddings here serve a more specific purpose: pairing each current-period risk chunk with its semantically nearest counterpart in the prior-period filing. Alignment quality will be tested explicitly using a small set of manually-aligned filing pairs as ground truth.

**2. Chain-of-Thought Prompting (Week 3)**
For each aligned chunk pair, the system prompt will instruct the model to first reason step-by-step about whether the change is cosmetic (formatting, "the Company" → "we") or substantive (new exposure, escalated qualifier, expanded scope), before producing a final delta classification. This scratchpad reasoning will be captured and shown in the UI as an expandable "model reasoning" panel beside each flagged delta, so the analyst can audit *why* the system flagged a change as meaningful — and override it if not.

### Baseline

The baseline is what a skeptical reader would (rightly) propose first: a **plain text diff** between the two filings, with optional GPT-summarization of each individual diff hunk. No chunk alignment, no semantic comparison, no boilerplate filtering — the analyst gets the raw output of `diff` plus a one-line summary of each change. This represents the cheapest possible version of "use a tool to find what changed," and the central hypothesis of the project is that this baseline produces too much noise to be usable, while the LLM-based system surfaces a small number of meaningful signals.

### The App

The user opens the Streamlit app and provides two filings — either by uploading PDFs or by entering CIK + accession numbers for EDGAR retrieval. The app processes the pair and renders: (1) a ranked **delta table** showing only the risk factors where language has meaningfully changed, with side-by-side current/prior text and a model-generated rationale for each flag; (2) a **new/removed risks** panel showing items present in one filing but not the other; (3) an overall **disclosure direction score** (more conservative / unchanged / more aggressive) with rationale; and (4) an expandable model-reasoning panel for every flagged item, so the analyst can audit and dismiss false positives. All outputs can be exported as a CSV or markdown summary suitable for pasting into a research note.

---

## 5. Evaluation Plan

**What success looks like:** Given a filing pair where a known meaningful change occurred (e.g., SVB 2021→2022 interest-rate risk language), the system surfaces that change in its top flagged deltas. Given a filing pair with only cosmetic edits, the system flags few or no deltas. The system's signal-to-noise ratio is materially better than the diff baseline.

**What will be measured:**
- **Delta detection recall:** Of the meaningful changes a human analyst would flag in a filing pair, what fraction does the system surface in its top-N output? This is the primary metric.
- **Delta detection precision:** Of the changes the system flags, what fraction does a human reviewer agree are meaningful (not cosmetic)? This captures noise.
- **Alignment accuracy:** Of the current-period risks paired by embedding similarity to a prior-period counterpart, what fraction are correctly paired (vs. matched to the wrong risk or incorrectly flagged as new)?
- **Direction score calibration:** Does the system's overall disclosure-direction score (more/less conservative) directionally agree with human assessment across the test set?
- **Latency and cost** per filing pair end-to-end.

**Test set:** 10–15 filing pairs sourced from public SEC EDGAR. The set will be deliberately stratified into three buckets: (a) known-signal pairs where a documented meaningful change exists (SVB 2021→2022, Wirecard pre-collapse, a few others identifiable from post-mortems and press coverage); (b) routine pairs from large-cap names where most quarter-over-quarter changes should be cosmetic; (c) edge cases including a filing pair where the company restructured its Risk Factors ordering between periods. Ground truth labels for "meaningful change" will be manually annotated by me and cross-checked by a model-as-judge for consistency.

**Baseline comparison:** The same test set will be run through both the LLM alignment + CoT system and the diff baseline. The two will be compared on precision and recall of meaningful-change detection. The hypothesis: the diff baseline will have high recall but very low precision (everything flagged, signal lost in noise); the LLM system will trade some recall for substantially higher precision and a usable output.

---

## 6. Example Inputs and Failure Cases

### Example Inputs

1. **SVB Financial Group 10-K (FY2021 vs. FY2022):** The headline known-signal case. Expected output: meaningful escalation in interest rate risk and liquidity-related language flagged in the top deltas; overall direction score shifted toward more conservative. If the system fails on this pair, the project has not delivered.

2. **Apple 10-K (FY2023 vs. FY2024):** A large-cap routine case. Expected output: most changes flagged as cosmetic; possibly one or two genuine deltas around AI regulatory risk or supply-chain concentration language. Tests whether the system stays quiet when it should.

3. **A mid-cap semiconductor name 10-K (two consecutive years):** Tests performance on a less-covered name where model pre-training knowledge is less likely to contaminate results. Drawn from my equity research coverage area.

4. **A 10-Q vs. prior 10-Q for the same company:** Tests handling of shorter quarterly filings, which have fewer risk factors and less language churn between periods.

5. **A filing pair where the company restructured its Risk Factors ordering between periods:** Stress-tests the embedding-based alignment step, which cannot rely on positional matching.

### Anticipated Failure Cases

1. **Alignment failure when section structure changes:** If a company restructures its Risk Factors ordering or merges/splits items between filings, embedding-based pairing may match the wrong items and produce spurious "new risk" or "removed risk" flags. This is the most likely structural failure mode.

2. **False negatives on subtle language escalation:** A genuinely meaningful change like "may impact" → "is likely to materially impact" sits inside an otherwise unchanged paragraph. The model may classify the chunk as cosmetically edited and miss the signal — which is exactly the kind of failure this tool is supposed to prevent.

3. **False positives from heavily-lawyered companies:** Some companies rewrite their Risk Factors language every year as a matter of disclosure policy rather than because anything substantive changed. The system may flag dozens of cosmetic re-writings as meaningful deltas, producing exactly the noise the project is trying to avoid.

4. **Context length and cost overflow on very long filings:** Some 10-K filings exceed 200 risk-factor chunks. Running CoT comparison on every aligned pair becomes expensive. A pre-filter to cheaply discard near-identical pairs before the expensive reasoning pass will likely be needed.

---

## 7. Risks and Governance

**Where the system could fail:**
- Hallucinated delta descriptions not grounded in actual filing text
- Embedding alignment errors that cause real changes to be hidden inside spuriously-paired chunks
- False positives from cosmetic re-writes flagged as meaningful, training the analyst to ignore future flags ("alert fatigue")
- False negatives that look like genuine "all clear" signals when the system has actually missed something

**The most important risk — false confidence:**
Because this tool is framed as catching thesis-killer signals, the most dangerous failure mode is *not* a noisy output. It is a clean output. An analyst who runs the system on a filing pair, sees no flagged deltas, and concludes "nothing material has changed" may be more confident than they would have been after a manual skim — even though the system may have missed the signal entirely. The system must be designed and presented in a way that does not encourage this misreading: outputs should always be framed as "what the system found," never as "what is there to find."

**Where it should not be trusted:**
- As a substitute for reading the filing on names where the analyst has high conviction or large position size
- As a sole basis for any portfolio action; outputs must be reviewed by a human before acting
- As a legal compliance tool — this is not a substitute for counsel review
- For cross-company comparison (the disclosure direction score is meaningful only within one company over time)

**Controls and governance:**
- Every flagged delta will display the source text from both filings side-by-side, so the analyst can verify the model's interpretation against ground truth in one click
- The model's chain-of-thought reasoning will be exposed for every flag, so the analyst can audit *why* the system made the call
- Alignment confidence scores will be displayed; low-confidence pairings will be visually flagged so the analyst knows to look manually
- The UI will explicitly state what the system did *not* do (e.g., "Reviewed 47 of 47 risk factor pairs; flagged 3 as meaningfully changed") so absence of flags is interpreted correctly
- A prominent disclaimer will frame the tool as research assistance only, never as a basis for action

**Data and cost concerns:**
- All filings are public SEC EDGAR documents — no privacy concerns
- API costs will be managed by using a cheaper model (e.g. Claude Haiku) for the embedding/alignment pass and reserving the stronger model for CoT delta classification on aligned pairs that pass a similarity threshold
- A cost-per-filing-pair benchmark will be documented in the evaluation appendix

---

## 8. Plan for the Week 6 Check-In

By the Week 6 check-in, I expect to have:

**App (running):**
- A functional Streamlit app that accepts two filings (PDF upload or CIK input), parses and chunks the Risk Factors section of each, and produces an embedding-based alignment between current-period and prior-period risks.
- The chain-of-thought delta-classification pass implemented and producing structured output for each aligned pair.
- Side-by-side current/prior text display in the UI for each flagged delta.

**Evaluation (in place):**
- A manually labeled test set of at least 5 filing pairs, including the SVB 2021→2022 pair as the headline known-signal case and 3–4 routine large-cap pairs as control.
- A rubric defined for delta detection precision/recall and alignment accuracy.
- A model-as-judge prompt written and validated on 2–3 examples for consistency.

**Baseline comparison:**
- The diff baseline implemented and runnable on the same filing pairs.
- A preliminary precision/recall comparison table on the SVB pair plus at least two routine pairs.

**Not yet complete by Week 6:**
- Full 15-pair test set (5 will be labeled by check-in)
- Disclosure direction score calibration across the full test set
- Cost benchmarking across filing sizes
- Polished UI and export functionality
