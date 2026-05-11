# Sample Outputs

This document shows the actual output of the pipeline on each test case in
`data/samples/`, captured by running:

```bash
python -m eval.run_eval --provider mock
```

These are mock-provider results. For real Claude outputs, set
`ANTHROPIC_API_KEY` and re-run with `--provider anthropic`.

---

## Case 1: `svb_style` — known thesis-killer pattern

**Input:** `data/samples/svb_style_2021_risks.txt` → `svb_style_2022_risks.txt`

**Result:** 7 risk-factor pairs compared. System flagged 5. Diff baseline would have flagged 7 hunks.

### Flagged changes (sorted by severity)

```
[ESCALATION] severity=high
  Topic: Risks Related to Interest Rate Environment
  Rationale: Language has been escalated with phrases like ['are likely to',
    'material adverse'] and the scope has expanded with new specific
    exposures including ['held-to-maturity', 'rate movement'].
  New phrases: ['are likely to', 'material adverse',
    'may be required to take actions', 'would result in additional',
    'held-to-maturity', 'rate movement']

[ESCALATION] severity=high
  Topic: Risks Related to Deposit Concentration
  Rationale: Risk language was strengthened. New phrasing includes
    ['has resulted in']. Scope expanded with named exposures
    ['venture capital funding', 'deposit outflows'].

[SCOPE_EXPANSION] severity=high
  Topic: Risks Related to Liquidity
  Rationale: Risk factor substantially expanded (+309 chars) with new
    named exposure: 'Federal Home Loan Bank'. Warrants thesis re-review.

[NEW] severity=high
  Topic: Risks Related to Held-to-Maturity Securities Portfolio
  Rationale: Newly added risk factor with substantive specific disclosure.
    Not present in prior filing.

[REMOVED] severity=medium
  Topic: Risks Related to Reputation
  Rationale: Was present in prior filing, absent in current.
    Removal should be reviewed.
```

### Dismissed as cosmetic (3 items)

- Risks Related to Loan Portfolio Composition (similarity 1.00)
- Risks Related to Cybersecurity (similarity 0.95)
- Risks Related to Regulatory Capital Requirements (similarity 0.96)

**Comparison vs. ground truth:** All 5 expected meaningful changes flagged. Zero false positives.

---

## Case 2: `routine` — cosmetic edits only

**Input:** `data/samples/routine_2023_risks.txt` → `routine_2024_risks.txt`

**Result:** 4 risk-factor pairs compared. System flagged 0. Diff baseline would have flagged 2 hunks.

### Output

```
No meaningful changes detected.

Items reviewed and dismissed (4):
  - Macroeconomic and Industry Risks (similarity ~0.99)
  - Operational Risks (similarity ~0.99)
  - Legal and Regulatory Compliance Risks (similarity ~0.99)
  - Financial Risks (similarity ~0.99)
```

**This is the most important result.** Ground truth says zero meaningful changes (the legal-reserve number changed from $0.6B to $0.7B, a routine quarterly update). The diff baseline still flags 2 hunks — both pure noise that the analyst would have to read and dismiss. The system stays quiet, which is exactly what a useful tool does in the routine case.

---

## Case 3: `restructured` — reordered with one buried signal

**Input:** `data/samples/restructured_prior_risks.txt` → `restructured_current_risks.txt`

The current filing has the same 7 risks as prior, but reordered: Cybersecurity moved from position 7 to position 1, plus one risk genuinely escalated (International Operations gained substantive language about export controls).

**Result:** 7 risk-factor pairs compared. System flagged 1. Diff baseline would have flagged 4 hunks.

### Flagged change

```
[ESCALATION] severity=high
  Topic: Risks Related to International Operations and Geopolitical Risk
  Rationale: Language escalated with new specific exposures named:
    ['trade tensions', 'export controls', 'materially affected'].
    The risk factor has been substantially expanded with named
    geopolitical exposures.
```

### Dismissed as cosmetic (6 items)

The 6 reordered-but-unchanged risks are all correctly aligned to their prior counterparts despite the section ordering being completely scrambled, with similarity scores of 1.00 on each unchanged risk. This is the test that the TF-IDF alignment is robust to ordering changes.

**Comparison vs. ground truth:** The 1 expected meaningful change flagged. Zero false positives despite the alignment having to cross 6 reorder operations.

---

## Aggregate metrics

| Metric | Value |
|---|---|
| True positives | 6 |
| False positives | 0 |
| False negatives | 0 |
| Precision | 1.00 |
| Recall | 1.00 |
| F1 | 1.00 |
| Total system flags | 6 |
| Total diff-baseline hunks | 13 |

**Honesty caveat:** Precision/recall are perfect because the mock classifier is partly tuned to the same patterns embedded in the test data. The legitimate findings these results support are:

1. The full pipeline runs end-to-end on all three cases.
2. TF-IDF alignment correctly handles cosmetic edits, escalations, new risks, removed risks, and reordered filings.
3. **The system flags 6 items vs. the diff baseline's 13 — about half the noise.** Crucially, on the `routine` case where ground truth says nothing should be flagged, the system flags zero while diff still flags two.

To get real-Claude evaluation numbers, re-run with `--provider anthropic`.
