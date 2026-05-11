# Evaluation Results

**Provider:** `mock`
**Test cases:** 3

## Summary

| Metric | Value |
|---|---|
| True positives | 6 |
| False positives | 0 |
| False negatives | 0 |
| **Precision** | **1.00** |
| **Recall** | **1.00** |
| **F1** | **1.00** |
| Items flagged by system | 6 |
| Items flagged by diff baseline | 13 |

## Per-case results

### `svb_style` — known_signal

- Expected meaningful signals: **5**
- System flagged: **5** (TP=5, FP=0, FN=0)
- Diff baseline hunks: **7**
- Verdict breakdown: ESCALATION=2, SCOPE_EXPANSION=1, COSMETIC=3, NEW=1, REMOVED=1

**Correctly flagged:**
- Risks Related to Interest Rate Environment [ESCALATION]
- Risks Related to Deposit Concentration [ESCALATION]
- Risks Related to Liquidity [SCOPE_EXPANSION]
- Risks Related to Held-to-Maturity Securities Portfolio [NEW]
- Risks Related to Reputation [REMOVED]

### `routine` — routine_no_signal

- Expected meaningful signals: **0**
- System flagged: **0** (TP=0, FP=0, FN=0)
- Diff baseline hunks: **2**
- Verdict breakdown: COSMETIC=4

### `restructured` — edge_case_alignment

- Expected meaningful signals: **1**
- System flagged: **1** (TP=1, FP=0, FN=0)
- Diff baseline hunks: **4**
- Verdict breakdown: COSMETIC=6, ESCALATION=1

**Correctly flagged:**
- Risks Related to International Operations and Geopolitical Risk [ESCALATION]

## System vs. baseline

The diff baseline produces one entry per contiguous changed text hunk. Every entry would need to be read by the analyst to determine whether it's meaningful — that is the entire problem with using diff as the workflow.

| Case | Ground truth signals | System flagged | Diff hunks |
|---|---:|---:|---:|
| svb_style | 5 | 5 | 7 |
| routine | 0 | 0 | 2 |
| restructured | 1 | 1 | 4 |

**The most important comparison is in the `routine` case.** Ground truth says zero meaningful changes. The diff baseline flags 2 hunks anyway — both are pure noise (routine numeric updates and a comma). Each one has to be read by the analyst to be dismissed. The LLM-based system stays quiet, which is exactly what a useful tool does in the routine case.

## ⚠️ Mock-mode caveat

These results were generated using the **mock** classifier, a deterministic rule-based stand-in for the real Claude API. The mock detects a hand-crafted list of escalation phrases (`is likely to`, `material adverse`, etc.) and scope-expansion cues. It exists to validate the pipeline plumbing without burning API credits during development.

**A 1.00 precision/recall in mock mode is not evidence that the real system will achieve the same.** The mock is partially specified against the same test cases it is being evaluated on, which is circular. The legitimate things that the mock-mode evaluation does prove are:

- The full pipeline (parse → align → classify → report) runs end-to-end on all three test cases.
- The TF-IDF alignment correctly handles cosmetic edits, escalations, new risks, removed risks, and reordered filings.
- The diff baseline produces measurably more entries than the LLM-based system on every case, including pure noise on the routine case.

**To get real evaluation numbers, re-run with `--provider anthropic`** (requires `ANTHROPIC_API_KEY`). The baseline-vs-system count comparison above is real either way; only the precision/recall breakdown depends on the classifier provider.
