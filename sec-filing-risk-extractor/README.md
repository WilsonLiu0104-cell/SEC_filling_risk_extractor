# SEC Filing Risk Extractor

A small GenAI tool for one specific buy-side workflow: detecting when a company's own characterization of its risks has meaningfully shifted between two consecutive SEC filings — the kind of disclosure-language change that gets buried in 80-page documents during earnings season and that occasionally turns out to have been a thesis-killer hiding in plain sight.

Built as the final project for a graduate-level GenAI course.

---

## 1. Context, user, and problem

**Who the user is.** A buy-side equity analyst with active positions in 10–30 names. Not a lawyer, not a compliance officer — someone who has already underwritten a thesis on each name and needs to know when the underlying disclosure picture has shifted enough to warrant a re-look.

**The workflow being improved.** Each quarter, when a covered company files a new 10-Q or 10-K, the analyst has a single question to answer: *"Has the company's own characterization of risk meaningfully changed since I last underwrote this position, and if so, does it affect my view?"* The workflow begins when the new filing drops on EDGAR and ends with a yes/no/maybe decision: keep the position as-is, flag it for re-review, or escalate to the PM.

**Why this matters.** Most major investment blow-ups had warning signs sitting in plain sight in the company's own disclosures *before* the stock broke. SVB's interest-rate-risk language escalated meaningfully between its 2021 and 2022 10-Ks. Wirecard's audit-committee disclosures shifted before the collapse. The signals weren't hidden; they were diluted in 80 pages of mostly-identical text. Once a position is on the book, almost no one fully re-reads the Risk Factors section every quarter — they skim, look for headlines, and move on.

A single missed thesis-killer signal can cost a fund hundreds of basis points. Even one early warning flagged correctly per year would justify the entire workflow.

---

## 2. Solution and design

### What was built

A Streamlit app (`app.py`) backed by a small Python pipeline (`src/`) that takes two filings — a current-period 10-Q or 10-K and the corresponding prior-period filing — and produces a ranked, decision-ready summary of changes that matter.

### How it works

The pipeline has four steps:

**1. Parse.** `src/parser.py` splits each filing's Risk Factors section into individual risk-factor chunks, each with a title and body. The parser uses heading-detection heuristics that work on plain text extracted from PDF or EDGAR HTML.

**2. Align.** `src/alignment.py` pairs each current-period chunk with its closest counterpart in the prior-period filing using TF-IDF cosine similarity over character n-grams. Greedy assignment by similarity rank ensures one-to-one matching. Unmatched current chunks are flagged as **NEW**; unmatched prior chunks are flagged as **REMOVED**.

**3. Classify.** `src/classifier.py` sends each aligned pair to an LLM with a chain-of-thought prompt asking it to reason step-by-step about whether the language change is meaningful (escalation, scope expansion, de-escalation) or merely cosmetic (`"we"` → `"the Company"`, formatting, routine numeric updates). The classifier is conservative by design — when in doubt, mark cosmetic.

**4. Render.** The Streamlit app sorts results by severity, shows source text side-by-side for each flagged change, and exposes the model's chain-of-thought for audit. A separate panel shows what the diff baseline would have produced, for direct comparison.

### Key design choices

**TF-IDF for alignment, not dense embeddings.** Adjacent SEC filings of the same company are typically >70% identical text. Character-bigram TF-IDF handles this case in milliseconds with no API calls or model downloads, and on the test set it correctly aligns risks even when the filing is fully reordered (see the `restructured` test case, which scores 1.00 similarity on every unchanged risk despite a complete reshuffle of section ordering).

**Chain-of-thought prompting in the classifier.** The system prompt explicitly asks the model to reason about cosmetic vs. substantive change before producing its verdict, and the reasoning is captured and displayed in the UI. This is the auditability that makes the system usable: when the model flags a risk, the analyst can see exactly which words the model considered escalating.

**A `mock` classifier provider for development.** The system supports two providers: `anthropic` (real Claude API) and `mock` (a deterministic rule-based stand-in keyed off detectable escalation phrases like `"is likely to"` and `"material adverse"`). The mock is not a substitute for real evaluation — it exists so the pipeline can be developed, tested, and demonstrated without burning API credits. The README and the eval report are both clear about which mode produced any given result.

**Course concepts integrated:**
- **RAG / chunking + embeddings** (Week 4) — used for alignment, not for retrieval. Each filing is chunked at the risk-factor level; chunks are matched across filings by character-bigram TF-IDF cosine similarity. A small labeled test confirms alignment is robust to reordering.
- **Chain-of-thought prompting** (Week 3) — the classifier prompt instructs the model to reason step-by-step before producing its structured verdict, and the reasoning trace is exposed in the UI for analyst audit.

---

## 3. Evaluation and results

### Baseline

The chosen baseline is a **plain text diff** between the two filings — what a skeptical reader would (rightly) propose first as the cheapest possible alternative. The baseline implementation is in `src/baseline.py`. Every contiguous changed hunk is treated as potentially meaningful; the baseline has no way to distinguish cosmetic from substantive changes.

### Test set

Three filing pairs in `data/samples/`, with manually annotated ground truth in `eval/ground_truth.json`. The test set is small (this is a course project) but deliberately stratified:

| Test case | Description | Expected meaningful signals |
|---|---|---:|
| `svb_style` | Models the SVB 2021→2022 case. Multiple meaningful escalations in interest rate, deposit, and liquidity language; one new risk (HTM securities); one removed risk (reputation). | 5 |
| `routine` | Routine large-cap pair. All edits are cosmetic or routine numeric updates. The system should flag nothing. | 0 |
| `restructured` | Same risk factors as prior filing but reordered, with one renamed and one substantively expanded (export-control language). Tests alignment robustness. | 1 |

Filings are synthetic but written to mirror real 10-K language patterns. The `svb_style` pair specifically embeds the kind of escalation-and-new-risk pattern visible in actual SVB filings around the 2022 deposit-base inflection.

### What was measured

For each pair:
- **System flags** — how many risk factors the system marked as meaningful changes
- **True positives, false positives, false negatives** vs. ground truth
- **Diff baseline hunk count** — how many entries the analyst would have to read using the baseline approach

### Results

```
Precision: 1.00   Recall: 1.00   F1: 1.00

| Case          | Ground truth | System flagged | Diff hunks |
|---------------|-------------:|---------------:|-----------:|
| svb_style     |            5 |              5 |          7 |
| routine       |            0 |              0 |          2 |
| restructured  |            1 |              1 |          4 |
```

<img width="2994" height="1878" alt="SEC Filing Risk Extractor" src="https://github.com/user-attachments/assets/0b8f9a0b-f1cc-4002-8812-0d9ac3823d9d" />



<img width="2994" height="1878" alt="SEC Filing Risk Extractor1" src="https://github.com/user-attachments/assets/48a19265-a699-477c-bc67-dad2d946fc43" />

**The honest reading.** A 1.00 precision/recall in mock mode is not strong evidence the real system will achieve the same. The mock classifier is keyed on the same escalation-phrase patterns embedded in the test data, which is partially circular. What the mock-mode evaluation does prove definitively:

1. The full pipeline runs end-to-end.
2. The TF-IDF alignment correctly handles cosmetic edits, escalations, new risks, removed risks, and reordered filings.
3. **The diff baseline produces measurably more entries than the LLM-based system on every case.** In the `routine` case, where ground truth says zero meaningful changes, the diff baseline still flags 2 hunks of pure noise that the analyst would have to read and dismiss.

The full per-case breakdown including verdict-type counts and side-by-side text is in [`eval/results.md`](eval/results.md).

### Where the project breaks down

- **Mock-provider results are not a substitute for real evaluation.** Re-running with `--provider anthropic` is required for a defensible precision/recall claim.
- **Test set is small and synthetic.** Three pairs of hand-written excerpts isn't enough to make a generalization claim. A production evaluation would expand to 15+ pairs across multiple industries, ideally drawn from real EDGAR filings with documented year-over-year shifts.
- **Alignment fails when both content and ordering change substantially.** TF-IDF works because adjacent filings are >70% identical. A company that completely rewrites its Risk Factors section in a single year (rare but possible) would defeat the matcher and cause spurious NEW/REMOVED flags.
- **The system reads language only, not business reality.** A company can rewrite its disclosure in a more conservative direction even as the underlying business deteriorates, or vice versa. This tool surfaces the disclosure shift; an analyst still has to decide what it means.
- **Most dangerous failure mode: false confidence.** If the system flags nothing on a filing pair, an analyst might conclude "all clear" — even though the system may have missed the signal entirely. The UI and the README both flag this explicitly.

---

## 4. Artifact snapshot

### Sample run on the SVB-style test case

Running `python -m eval.run_eval --provider mock` against the `svb_style` pair produces:

```
ESCALATION   high     Risks Related to Interest Rate Environment
  Language has been escalated with phrases like ['are likely to',
  'material adverse'] and the scope has expanded with new specific
  exposures including ['venture capital funding', 'wholesale funding'].

ESCALATION   high     Risks Related to Deposit Concentration
  Risk language was strengthened. Newly added phrasing in the current
  filing: ['has resulted in']. This represents a meaningful tonal
  shift, not a cosmetic edit.

SCOPE_EXPANSION  high  Risks Related to Liquidity
  The risk factor has been substantially expanded (+309 chars) with
  new specific exposures named: ['Federal Home Loan Bank', 'wholesale
  funding']. This is the kind of named-risk addition that warrants
  thesis re-review.

NEW          high     Risks Related to Held-to-Maturity Securities Portfolio
  Newly added risk factor with substantive specific disclosure language.

REMOVED      medium   Risks Related to Reputation
  Risk factor was present in prior filing but is absent in current.

[3 cosmetic items reviewed and dismissed silently]
```

The same input through the diff baseline produces 7 contiguous changed hunks, each of which the analyst would have to read in full to determine whether it's meaningful. The baseline has no rationale, no severity, and no way to know that one of the changes (the HTM addition) is structurally a brand-new risk factor.

### How the Streamlit UI presents this

The app shows headline metrics at the top (number of risks compared, number flagged, baseline hunks for comparison), then a sorted list of flagged changes — each item expandable to show the model's rationale, the key phrases it identified, and the prior/current text side-by-side. A separate collapsible panel below shows every item the system reviewed and dismissed, so the analyst can audit the silent dismissals if they want to. At the bottom, a panel renders the diff-baseline output for direct contrast.

---

## Setup and usage

### Requirements

Python 3.10 or later.

```bash
git clone <this-repo>
cd sec-filing-risk-extractor
pip install -r requirements.txt
```

### Running the app

```bash
streamlit run app.py
```

Open the URL Streamlit prints (typically `http://localhost:8501`), pick one of the three sample test pairs from the dropdown, and click **Run analysis**.

To use the real Claude classifier instead of the mock provider, set the API key first:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
streamlit run app.py
```

The app will detect the key and default to the `anthropic` provider; you can still toggle back to `mock` in the sidebar.

### Running the evaluation

```bash
# Mock provider (no API key needed)
python -m eval.run_eval

# Real Claude provider
export ANTHROPIC_API_KEY=sk-ant-...
python -m eval.run_eval --provider anthropic
```

Either run rewrites `eval/results.md` with per-case results, baseline comparison, and an honest caveat block describing what the run does and does not prove.

### Bringing your own filings

The simplest path is to extract Item 1A (Risk Factors) text from your two filings into plain `.txt` files, then upload them through the Streamlit "Upload text files" mode. PDF text extraction (via `pdfplumber`) and live EDGAR fetching (via `src/edgar.py`) are also supported but require additional setup — see `src/edgar.py` for the EDGAR path, which expects an `EDGAR_USER_AGENT` environment variable per SEC's rate-limit policy.

---

## Repository layout

```
sec-filing-risk-extractor/
├── app.py                    # Streamlit UI
├── requirements.txt
├── .env.example
├── README.md                 # this file
├── src/
│   ├── parser.py             # filing → risk-factor chunks
│   ├── alignment.py          # TF-IDF pairing across filings
│   ├── classifier.py         # LLM delta classifier (anthropic + mock)
│   ├── prompts.py            # all prompts in one place
│   ├── baseline.py           # plain text-diff baseline
│   ├── edgar.py              # SEC EDGAR fetcher (optional path)
│   └── pipeline.py           # end-to-end orchestrator
├── data/samples/             # synthetic test filings
├── eval/
│   ├── ground_truth.json     # manually labeled deltas
│   ├── run_eval.py           # evaluation harness
│   └── results.md            # auto-generated results report
└── docs/
    └── project_plan.md       # original project plan submitted Week 4
```

---

## Disclaimers

This tool is for research assistance only. It is not legal advice and should not be the sole basis for any investment decision. The system reviews disclosure language only — it does not assess underlying business reality. Every flag is the model's interpretation of textual change, and every silent dismissal is also the model's judgment; both are fallible. For high-conviction positions, no automated tool replaces reading the filing.
