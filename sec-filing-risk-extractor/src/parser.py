"""Filing parser.

Splits the Risk Factors section of a 10-K or 10-Q into individual risk-factor
chunks. Each chunk is a (title, body) pair that can be independently aligned
and compared against its counterpart in another filing.

The parser handles plain-text input. For PDF/HTML support, callers should
extract text first using `pdfplumber` (PDFs) or `BeautifulSoup` (EDGAR HTML)
and pass the resulting plain text into `parse_risk_factors`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


# Heading detection: a line is treated as a risk-factor heading if it's short,
# does NOT end with sentence-ending punctuation, and either starts with one of
# the common header tokens OR is followed by a blank line and then prose.
_HEADER_PREFIXES = (
    "risk", "item ", "item\u00a0", "general risk",
)
_MAX_HEADER_LEN = 200
_SENTENCE_END = (".", "?", "!", ":")


@dataclass
class RiskFactor:
    """A single risk factor extracted from a filing."""

    title: str
    body: str
    ordinal: int  # zero-indexed position within the filing

    @property
    def text(self) -> str:
        """Combined title + body, used for embedding/similarity."""
        return f"{self.title}\n\n{self.body}".strip()

    def __len__(self) -> int:
        return len(self.body)


def _looks_like_header(line: str) -> bool:
    line = line.strip()
    if not line or len(line) > _MAX_HEADER_LEN:
        return False
    if line.endswith(_SENTENCE_END):
        return False
    lower = line.lower()
    if any(lower.startswith(prefix) for prefix in _HEADER_PREFIXES):
        return True
    # Title-case heading without sentence-ending punctuation: heuristic fallback.
    # Accept if the line is mostly capitalized words.
    words = line.split()
    if 2 <= len(words) <= 15:
        cap_count = sum(1 for w in words if w[:1].isupper())
        if cap_count / len(words) >= 0.6:
            return True
    return False


def _strip_preamble(text: str) -> str:
    """Remove the preamble before the first detectable risk-factor heading.

    Many 10-Ks open Item 1A with a generic introduction ("The following risk
    factors should be carefully considered..."). That preamble belongs to no
    individual risk and confuses alignment, so we drop it.
    """
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if _looks_like_header(line):
            # Special case: skip "Item 1A. Risk Factors" itself.
            stripped = line.strip().lower()
            if stripped.startswith("item 1a") or stripped == "risk factors":
                continue
            return "\n".join(lines[i:])
    return text


def parse_risk_factors(text: str) -> list[RiskFactor]:
    """Parse a Risk Factors section into a list of (title, body) chunks.

    Args:
        text: Plain-text Risk Factors section. Typically the contents of
            Item 1A of a 10-K or 10-Q after extraction from PDF or HTML.

    Returns:
        Ordered list of RiskFactor objects, one per identified risk.
    """
    text = _strip_preamble(text)
    lines = text.splitlines()

    chunks: list[RiskFactor] = []
    current_title: str | None = None
    current_body: list[str] = []
    ordinal = 0

    def flush() -> None:
        nonlocal current_title, current_body, ordinal
        if current_title is None:
            return
        body = "\n\n".join(p.strip() for p in "\n".join(current_body).split("\n\n") if p.strip())
        if body:
            chunks.append(RiskFactor(
                title=current_title.strip(),
                body=body,
                ordinal=ordinal,
            ))
            ordinal += 1
        current_title = None
        current_body = []

    i = 0
    while i < len(lines):
        line = lines[i]
        if _looks_like_header(line):
            flush()
            current_title = line
        else:
            if current_title is not None:
                current_body.append(line)
        i += 1
    flush()

    # Drop any chunks whose body is too short to be a real risk factor.
    chunks = [c for c in chunks if len(c.body) >= 80]
    return chunks


def parse_file(path: str) -> list[RiskFactor]:
    """Convenience helper: read a text file and parse it."""
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    return parse_risk_factors(text)
