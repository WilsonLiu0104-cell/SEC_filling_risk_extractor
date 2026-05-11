"""Delta classifier.

Takes an aligned pair (current chunk + prior chunk) and asks an LLM whether
the language has changed in a way that matters. Supports two providers:

* "anthropic" — real Claude API call (requires ANTHROPIC_API_KEY env var)
* "mock"     — deterministic local stand-in keyed off detectable language cues

The mock exists so the system can be developed, tested, and demonstrated
without an API key. It is NOT a substitute for real evaluation — every
real run should use the anthropic provider. The mock's purpose is solely
to validate the architecture and pipeline plumbing.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field, asdict
from typing import Any

from .alignment import AlignedPair
from .parser import RiskFactor
from .prompts import (
    DELTA_CLASSIFIER_SYSTEM,
    DELTA_CLASSIFIER_USER_TEMPLATE,
    NEW_RISK_SYSTEM,
    NEW_RISK_USER_TEMPLATE,
    REMOVED_RISK_SYSTEM,
    REMOVED_RISK_USER_TEMPLATE,
)


@dataclass
class DeltaVerdict:
    """The classifier's verdict for a single aligned pair (or new/removed risk)."""

    risk_topic: str
    change_type: str  # ESCALATION | DE_ESCALATION | SCOPE_EXPANSION | SCOPE_REDUCTION | COSMETIC | NEW | REMOVED
    meaningful: bool
    severity: str  # high | medium | low
    rationale: str
    key_phrases_added: list[str] = field(default_factory=list)
    key_phrases_removed: list[str] = field(default_factory=list)
    similarity: float = 0.0
    reasoning_trace: str = ""  # full chain-of-thought, for audit

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------- #
# Real provider: Anthropic Claude
# --------------------------------------------------------------------------- #

def _call_anthropic(system: str, user: str, model: str = "claude-sonnet-4-5") -> str:
    """Call the Anthropic API. Returns the text body of the response."""
    try:
        from anthropic import Anthropic
    except ImportError as e:
        raise ImportError(
            "anthropic package not installed. Run: pip install anthropic"
        ) from e

    client = Anthropic()  # picks up ANTHROPIC_API_KEY from environment
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    # Concatenate all text blocks.
    return "\n".join(
        block.text for block in response.content if getattr(block, "type", "") == "text"
    )


def _extract_json_block(text: str) -> dict[str, Any]:
    """Extract the JSON object from a ```json ... ``` fenced block."""
    m = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if not m:
        # Fallback: try to find a JSON object anywhere in the text.
        m = re.search(r"(\{[^{}]*?\"change_type\".*?\})", text, re.DOTALL)
    if not m:
        raise ValueError("No JSON block found in model response.")
    return json.loads(m.group(1))


# --------------------------------------------------------------------------- #
# Mock provider: deterministic, keyed off detectable language cues
# --------------------------------------------------------------------------- #

# Patterns that signal an ESCALATION when they appear in current but not prior.
_ESCALATION_PHRASES = [
    "are likely to",
    "is likely to have a material",
    "material adverse",
    "materially adverse",
    "materially affected",
    "have materially affected",
    "is reasonably likely",
    "have resulted in",
    "has resulted in",
    "could be required",
    "may be required to take actions",
    "would result in additional",
    "would force",
    "could be substantially below",
    "substantially below",
]

# Patterns that signal SCOPE EXPANSION (new specific named exposure).
_SCOPE_EXPANSION_PHRASES = [
    "trade tensions",
    "export controls",
    "venture capital funding",
    "wholesale funding",
    "Federal Home Loan Bank",
    "FHLB",
    "held-to-maturity",
    "amortized cost",
    "deposit outflows",
    "rate movement",
]


def _mock_classify_pair(pair: AlignedPair) -> DeltaVerdict:
    """Deterministic mock: inspects the text for known escalation/expansion cues."""
    current_lower = pair.current.text.lower()
    prior_lower = pair.prior.text.lower() if pair.prior else ""

    # Find escalation phrases that are NEW in current.
    new_escalations = [
        p for p in _ESCALATION_PHRASES
        if p.lower() in current_lower and p.lower() not in prior_lower
    ]
    # Find scope-expansion cues that are NEW in current.
    new_expansions = [
        p for p in _SCOPE_EXPANSION_PHRASES
        if p.lower() in current_lower and p.lower() not in prior_lower
    ]

    length_delta = len(pair.current.text) - len(pair.prior.text) if pair.prior else 0
    length_ratio = (
        len(pair.current.text) / max(1, len(pair.prior.text))
        if pair.prior else 1.0
    )

    # Decision tree.
    if new_escalations and new_expansions:
        change_type = "ESCALATION"
        meaningful = True
        severity = "high"
        rationale = (
            f"Language has been escalated with phrases like {new_escalations[:2]} "
            f"and the scope has expanded with new specific exposures including "
            f"{new_expansions[:2]}. The combination is a strong signal."
        )
    elif new_escalations:
        change_type = "ESCALATION"
        meaningful = True
        severity = "high" if len(new_escalations) >= 2 else "medium"
        rationale = (
            f"Risk language was strengthened. Newly added phrasing in the "
            f"current filing: {new_escalations[:3]}. This represents a "
            f"meaningful tonal shift, not a cosmetic edit."
        )
    elif new_expansions and length_ratio > 1.3:
        change_type = "SCOPE_EXPANSION"
        meaningful = True
        severity = "high"
        rationale = (
            f"The risk factor has been substantially expanded ({length_delta:+d} chars) "
            f"with new specific exposures named: {new_expansions[:3]}. This is "
            f"the kind of named-risk addition that warrants thesis re-review."
        )
    elif pair.similarity > 0.92:
        change_type = "COSMETIC"
        meaningful = False
        severity = "low"
        rationale = (
            f"Text is nearly identical (similarity {pair.similarity:.2f}). "
            f"Differences are limited to formatting, pronoun substitutions, "
            f"or routine numeric updates."
        )
    else:
        # Moderate similarity, no detected escalation cues — likely cosmetic
        # rewrite or routine updates. The real model would parse this in detail.
        change_type = "COSMETIC"
        meaningful = False
        severity = "low"
        rationale = (
            f"Text similarity of {pair.similarity:.2f} indicates non-trivial "
            f"editing, but no clear escalation cues were detected in the "
            f"changes. Treating as cosmetic rewrite."
        )

    return DeltaVerdict(
        risk_topic=pair.current.title,
        change_type=change_type,
        meaningful=meaningful,
        severity=severity,
        rationale=rationale,
        key_phrases_added=new_escalations + new_expansions,
        key_phrases_removed=[],
        similarity=pair.similarity,
        reasoning_trace="[mock provider — no chain-of-thought generated]",
    )


def _mock_classify_new(risk: RiskFactor) -> DeltaVerdict:
    """Mock classifier for a brand-new risk factor with no prior counterpart."""
    text_lower = risk.text.lower()
    has_specifics = any(p.lower() in text_lower for p in _SCOPE_EXPANSION_PHRASES)
    has_escalation = any(p.lower() in text_lower for p in _ESCALATION_PHRASES)
    long_enough = len(risk.text) > 400

    meaningful = (has_specifics or has_escalation) and long_enough

    return DeltaVerdict(
        risk_topic=risk.title,
        change_type="NEW",
        meaningful=meaningful,
        severity="high" if meaningful else "low",
        rationale=(
            "Newly added risk factor with substantive specific disclosure language."
            if meaningful else
            "Newly added risk factor, but appears generic or boilerplate in nature."
        ),
        key_phrases_added=[],
        key_phrases_removed=[],
        similarity=0.0,
        reasoning_trace="[mock provider]",
    )


def _mock_classify_removed(risk: RiskFactor) -> DeltaVerdict:
    """Mock classifier for a removed risk factor."""
    return DeltaVerdict(
        risk_topic=risk.title,
        change_type="REMOVED",
        meaningful=True,
        severity="medium",
        rationale=(
            "Risk factor was present in prior filing but is absent in current. "
            "Removal of disclosed risks should be reviewed — could indicate "
            "resolution, materiality reassessment, or editorial cleanup."
        ),
        key_phrases_added=[],
        key_phrases_removed=[],
        similarity=0.0,
        reasoning_trace="[mock provider]",
    )


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def classify_pair(pair: AlignedPair, provider: str = "mock") -> DeltaVerdict:
    """Classify a single aligned pair. NEW pairs (no prior) get the new-risk path."""
    if pair.status == "NEW" or pair.prior is None:
        return classify_new(pair.current, provider=provider)

    if provider == "mock":
        return _mock_classify_pair(pair)

    if provider == "anthropic":
        user = DELTA_CLASSIFIER_USER_TEMPLATE.format(
            topic=pair.current.title,
            prior_text=pair.prior.text,
            current_text=pair.current.text,
        )
        full_response = _call_anthropic(DELTA_CLASSIFIER_SYSTEM, user)
        try:
            data = _extract_json_block(full_response)
        except ValueError:
            # Hard fallback if the model returned malformed output.
            return DeltaVerdict(
                risk_topic=pair.current.title,
                change_type="COSMETIC",
                meaningful=False,
                severity="low",
                rationale="Model output could not be parsed; defaulting to non-meaningful.",
                similarity=pair.similarity,
                reasoning_trace=full_response[:1000],
            )
        return DeltaVerdict(
            risk_topic=pair.current.title,
            change_type=data.get("change_type", "COSMETIC"),
            meaningful=bool(data.get("meaningful", False)),
            severity=data.get("severity", "low"),
            rationale=data.get("rationale", ""),
            key_phrases_added=list(data.get("key_phrases_added", [])),
            key_phrases_removed=list(data.get("key_phrases_removed", [])),
            similarity=pair.similarity,
            reasoning_trace=full_response,
        )

    raise ValueError(f"Unknown provider: {provider}")


def classify_new(risk: RiskFactor, provider: str = "mock") -> DeltaVerdict:
    """Classify a brand-new risk factor."""
    if provider == "mock":
        return _mock_classify_new(risk)
    if provider == "anthropic":
        user = NEW_RISK_USER_TEMPLATE.format(topic=risk.title, current_text=risk.text)
        full_response = _call_anthropic(NEW_RISK_SYSTEM, user)
        try:
            data = _extract_json_block(full_response)
        except ValueError:
            return DeltaVerdict(
                risk_topic=risk.title,
                change_type="NEW",
                meaningful=True,
                severity="medium",
                rationale="Model output could not be parsed; flagging conservatively.",
                reasoning_trace=full_response[:1000],
            )
        return DeltaVerdict(
            risk_topic=risk.title,
            change_type="NEW",
            meaningful=bool(data.get("meaningful", True)),
            severity=data.get("severity", "medium"),
            rationale=data.get("rationale", ""),
            reasoning_trace=full_response,
        )
    raise ValueError(f"Unknown provider: {provider}")


def classify_removed(risk: RiskFactor, provider: str = "mock") -> DeltaVerdict:
    """Classify a removed risk factor."""
    if provider == "mock":
        return _mock_classify_removed(risk)
    if provider == "anthropic":
        user = REMOVED_RISK_USER_TEMPLATE.format(topic=risk.title, prior_text=risk.text)
        full_response = _call_anthropic(REMOVED_RISK_SYSTEM, user)
        try:
            data = _extract_json_block(full_response)
        except ValueError:
            return DeltaVerdict(
                risk_topic=risk.title,
                change_type="REMOVED",
                meaningful=True,
                severity="medium",
                rationale="Model output could not be parsed; flagging conservatively.",
                reasoning_trace=full_response[:1000],
            )
        return DeltaVerdict(
            risk_topic=risk.title,
            change_type="REMOVED",
            meaningful=bool(data.get("meaningful", True)),
            severity=data.get("severity", "medium"),
            rationale=data.get("rationale", ""),
            reasoning_trace=full_response,
        )
    raise ValueError(f"Unknown provider: {provider}")
