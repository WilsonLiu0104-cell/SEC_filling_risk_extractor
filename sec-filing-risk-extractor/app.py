"""SEC Filing Risk Extractor — Streamlit UI.

A buy-side analyst uploads (or selects) a current-period and prior-period
filing and gets back a ranked list of risk-factor changes that would matter
to someone with an existing position.

Run with:
    streamlit run app.py
"""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from src.pipeline import run_pipeline
from src.baseline import diff_baseline


SAMPLES_DIR = Path(__file__).parent / "data" / "samples"

SAMPLE_PAIRS = {
    "SVB-style 2021 → 2022 (known thesis-killer signal)": (
        "svb_style_2021_risks.txt",
        "svb_style_2022_risks.txt",
    ),
    "Routine large-cap 2023 → 2024 (cosmetic edits only)": (
        "routine_2023_risks.txt",
        "routine_2024_risks.txt",
    ),
    "Restructured ordering with one buried signal": (
        "restructured_prior_risks.txt",
        "restructured_current_risks.txt",
    ),
}


SEVERITY_COLORS = {
    "high": "#d62728",
    "medium": "#ff7f0e",
    "low": "#7f7f7f",
}

CHANGE_TYPE_BADGES = {
    "ESCALATION": "🚨",
    "DE_ESCALATION": "🟢",
    "SCOPE_EXPANSION": "📈",
    "SCOPE_REDUCTION": "📉",
    "NEW": "🆕",
    "REMOVED": "🗑️",
    "COSMETIC": "  ",
}


def _load_sample(name: str) -> tuple[str, str]:
    prior_name, current_name = SAMPLE_PAIRS[name]
    prior = (SAMPLES_DIR / prior_name).read_text(encoding="utf-8")
    current = (SAMPLES_DIR / current_name).read_text(encoding="utf-8")
    return prior, current


def _provider_from_env() -> str:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    return "mock"


# --------------------------------------------------------------------------- #
# UI
# --------------------------------------------------------------------------- #

st.set_page_config(page_title="SEC Filing Risk Extractor", layout="wide")

st.title("SEC Filing Risk Extractor")
st.caption(
    "Surfaces meaningful year-over-year changes in 10-K / 10-Q risk factors. "
    "Designed for buy-side analysts re-reviewing existing positions during earnings cycles."
)

with st.sidebar:
    st.header("Settings")

    default_provider = _provider_from_env()
    provider = st.radio(
        "Classifier provider",
        options=["mock", "anthropic"],
        index=0 if default_provider == "mock" else 1,
        help=(
            "`anthropic` calls Claude; requires ANTHROPIC_API_KEY. "
            "`mock` is a deterministic stand-in for development."
        ),
    )
    if provider == "anthropic" and not os.environ.get("ANTHROPIC_API_KEY"):
        st.warning("ANTHROPIC_API_KEY not set in environment.")

    st.divider()
    st.markdown(
        "**About:** This tool detects when a company's own characterization "
        "of a risk has shifted between consecutive filings — escalations in "
        "tone, new specific exposures, removed risks. It does **not** "
        "replace reading the filing, especially for high-conviction positions."
    )

# Input section
st.subheader("1. Provide two filings")

input_mode = st.radio(
    "Input mode",
    options=["Sample test pair", "Paste text", "Upload text files"],
    horizontal=True,
)

prior_text: str | None = None
current_text: str | None = None

if input_mode == "Sample test pair":
    sample_name = st.selectbox("Test pair", list(SAMPLE_PAIRS.keys()))
    prior_text, current_text = _load_sample(sample_name)
elif input_mode == "Paste text":
    col1, col2 = st.columns(2)
    with col1:
        prior_text = st.text_area("Prior filing — Risk Factors text", height=300)
    with col2:
        current_text = st.text_area("Current filing — Risk Factors text", height=300)
else:
    col1, col2 = st.columns(2)
    with col1:
        f1 = st.file_uploader("Prior filing (.txt)", type=["txt"])
        if f1:
            prior_text = f1.read().decode("utf-8")
    with col2:
        f2 = st.file_uploader("Current filing (.txt)", type=["txt"])
        if f2:
            current_text = f2.read().decode("utf-8")

st.divider()

run = st.button("🔍 Run analysis", type="primary", disabled=not (prior_text and current_text))

if run and prior_text and current_text:
    with st.spinner("Parsing, aligning, and classifying..."):
        result = run_pipeline(prior_text, current_text, provider=provider)
        baseline_hunks = diff_baseline(prior_text, current_text)

    # Headline metrics
    st.subheader("2. Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Risk factors compared", result.num_pairs)
    c2.metric("Meaningful flags", result.num_flagged)
    c3.metric("Diff baseline hunks", len(baseline_hunks),
              help="What a plain text-diff would have flagged. Higher = more noise.")
    if result.num_pairs:
        flag_rate = result.num_flagged / result.num_pairs
        c4.metric("Flag rate", f"{flag_rate:.0%}")

    if result.num_flagged == 0:
        st.success(
            "**No meaningful changes detected.** The system reviewed all risk-factor "
            "pairs and found only cosmetic edits. Reading the full filing yourself for "
            "high-conviction positions is still recommended."
        )
    else:
        st.warning(
            f"**{result.num_flagged} risk-factor change(s) flagged for review.** "
            f"Click into each item to see the model's reasoning and the source text."
        )

    # Flagged items
    st.subheader("3. Flagged changes")
    flagged = sorted(
        result.meaningful_verdicts,
        key=lambda v: ("high", "medium", "low").index(v.severity),
    )
    if not flagged:
        st.info("Nothing flagged. See full breakdown below.")
    for v in flagged:
        badge = CHANGE_TYPE_BADGES.get(v.change_type, "")
        color = SEVERITY_COLORS.get(v.severity, "#888")
        with st.expander(
            f"{badge} **{v.risk_topic}** — {v.change_type} ({v.severity})",
            expanded=(v.severity == "high"),
        ):
            st.markdown(f"<span style='color:{color}'>**Severity:** {v.severity}</span>",
                       unsafe_allow_html=True)
            st.markdown(f"**Rationale:** {v.rationale}")
            if v.key_phrases_added:
                st.markdown("**Key phrases added in current filing:**")
                for p in v.key_phrases_added:
                    st.markdown(f"- `{p}`")
            if v.key_phrases_removed:
                st.markdown("**Key phrases removed:**")
                for p in v.key_phrases_removed:
                    st.markdown(f"- `{p}`")

            # Show source text side-by-side for matched pairs
            matched_pair = next(
                (p for p in result.alignment.pairs if p.current.title == v.risk_topic),
                None,
            )
            if matched_pair and matched_pair.prior:
                st.markdown(f"**Alignment similarity:** {matched_pair.similarity:.2f}")
                left, right = st.columns(2)
                with left:
                    st.markdown("**Prior filing:**")
                    st.text_area(" ", matched_pair.prior.text, height=240,
                                key=f"prior_{v.risk_topic}", label_visibility="collapsed")
                with right:
                    st.markdown("**Current filing:**")
                    st.text_area(" ", matched_pair.current.text, height=240,
                                key=f"curr_{v.risk_topic}", label_visibility="collapsed")
            elif v.change_type == "NEW":
                st.markdown("**New risk factor (not present in prior filing):**")
                # Find the new risk text from alignment.
                for pair in result.alignment.pairs:
                    if pair.current.title == v.risk_topic:
                        st.text_area(" ", pair.current.text, height=240,
                                    key=f"new_{v.risk_topic}", label_visibility="collapsed")
            elif v.change_type == "REMOVED":
                st.markdown("**Removed risk factor (in prior, absent in current):**")
                for r in result.alignment.removed:
                    if r.title == v.risk_topic:
                        st.text_area(" ", r.text, height=240,
                                    key=f"rem_{v.risk_topic}", label_visibility="collapsed")

            if v.reasoning_trace and provider == "anthropic":
                with st.expander("Model chain-of-thought"):
                    st.text(v.reasoning_trace)

    # Quiet items
    st.subheader("4. Items reviewed and dismissed")
    with st.expander(
        f"Show all {result.num_pairs - result.num_flagged + len(result.alignment.removed)} "
        "items the system reviewed and judged non-meaningful"
    ):
        for v in result.verdicts:
            if v.meaningful:
                continue
            badge = CHANGE_TYPE_BADGES.get(v.change_type, "  ")
            st.markdown(f"{badge} **{v.risk_topic}** — {v.change_type} (similarity {v.similarity:.2f})")
            st.caption(v.rationale)

    # Baseline comparison
    st.subheader("5. What the diff baseline would have produced")
    st.caption(
        "For comparison: this is what the analyst would see if they used a plain text-diff "
        "instead of this tool. Each hunk would need to be read individually to determine "
        "whether it's meaningful — there is no rationale and no severity."
    )
    with st.expander(f"Show {len(baseline_hunks)} diff hunks"):
        for i, hunk in enumerate(baseline_hunks, 1):
            st.markdown(f"**Hunk {i}** (current lines {hunk.line_range[0]}–{hunk.line_range[1]})")
            left, right = st.columns(2)
            with left:
                st.code(hunk.prior_text or "(empty)", language=None)
            with right:
                st.code(hunk.current_text or "(empty)", language=None)

    # Footer
    st.divider()
    st.caption(
        "⚠️ This output is for research assistance only. It is not legal advice and "
        "should not be the sole basis for investment decisions. The system reviews "
        "language changes only — it does not assess underlying business reality."
    )

elif not (prior_text and current_text):
    st.info("Provide a prior and current filing above to begin.")
