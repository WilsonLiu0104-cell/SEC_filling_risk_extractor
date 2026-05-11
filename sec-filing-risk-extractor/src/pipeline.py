"""End-to-end pipeline: parse two filings, align, classify, return results.

This module is the single entry point used by both the Streamlit app and
the evaluation harness, so they exercise exactly the same code path.
"""

from __future__ import annotations

from dataclasses import dataclass

from .alignment import align, AlignmentResult
from .classifier import (
    DeltaVerdict,
    classify_pair,
    classify_new,
    classify_removed,
)
from .parser import parse_risk_factors


@dataclass
class PipelineResult:
    """Full result of running the LLM-based pipeline on a filing pair."""

    alignment: AlignmentResult
    verdicts: list[DeltaVerdict]  # one per current chunk + removed chunks

    @property
    def meaningful_verdicts(self) -> list[DeltaVerdict]:
        return [v for v in self.verdicts if v.meaningful]

    @property
    def num_pairs(self) -> int:
        return len(self.alignment.pairs)

    @property
    def num_flagged(self) -> int:
        return len(self.meaningful_verdicts)


def run_pipeline(
    prior_text: str,
    current_text: str,
    provider: str = "mock",
) -> PipelineResult:
    """Parse → align → classify on a pair of filing texts."""
    prior_chunks = parse_risk_factors(prior_text)
    current_chunks = parse_risk_factors(current_text)

    alignment = align(current_chunks, prior_chunks)

    verdicts: list[DeltaVerdict] = []
    for pair in alignment.pairs:
        verdicts.append(classify_pair(pair, provider=provider))
    for removed in alignment.removed:
        verdicts.append(classify_removed(removed, provider=provider))

    return PipelineResult(alignment=alignment, verdicts=verdicts)
