"""The naive baseline: plain text diff between two filings.

This is the cheapest plausible alternative to the LLM-based system. It
represents what a skeptical analyst might propose ("I don't need an AI;
just diff the two filings"). We include it so we can demonstrate
empirically that diff alone produces too much noise to be usable.

Output format: one "delta" entry per contiguous changed hunk, with the
prior and current text preserved. Every hunk is treated as potentially
meaningful — that is the entire problem with the baseline.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass


@dataclass
class DiffHunk:
    """A single contiguous changed section between two texts."""

    prior_text: str
    current_text: str
    line_range: tuple[int, int]  # in current text


def diff_baseline(prior_text: str, current_text: str) -> list[DiffHunk]:
    """Return all contiguous changed hunks between the two filing texts.

    The baseline flags every hunk as potentially meaningful — it has no
    way to distinguish cosmetic from substantive changes.
    """
    prior_lines = prior_text.splitlines()
    current_lines = current_text.splitlines()

    matcher = difflib.SequenceMatcher(None, prior_lines, current_lines, autojunk=False)
    hunks: list[DiffHunk] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        prior_chunk = "\n".join(prior_lines[i1:i2]).strip()
        current_chunk = "\n".join(current_lines[j1:j2]).strip()
        # Skip pure whitespace differences.
        if not prior_chunk and not current_chunk:
            continue
        hunks.append(DiffHunk(
            prior_text=prior_chunk,
            current_text=current_chunk,
            line_range=(j1, j2),
        ))

    return hunks


def diff_baseline_files(prior_path: str, current_path: str) -> list[DiffHunk]:
    with open(prior_path, "r", encoding="utf-8") as f:
        prior = f.read()
    with open(current_path, "r", encoding="utf-8") as f:
        current = f.read()
    return diff_baseline(prior, current)
