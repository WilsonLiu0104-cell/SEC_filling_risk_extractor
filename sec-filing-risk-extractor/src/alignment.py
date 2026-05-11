"""Risk-factor alignment via TF-IDF cosine similarity.

The task: given chunks parsed from two filings (current period vs prior),
pair each current-period chunk with its semantically nearest prior-period
counterpart. Chunks with no high-similarity match are flagged as NEW (added
in the current filing). Prior chunks that no current chunk paired to are
flagged as REMOVED.

We use TF-IDF rather than dense embeddings because risk-factor pairs across
adjacent filings are typically near-duplicates (often >70% identical text).
TF-IDF on character n-grams handles this case extremely well, runs in
milliseconds, and requires no API calls or model downloads — keeping the
dependency surface and cost small. The downside is that TF-IDF cannot match
risks that have been substantially rewritten, but that is rare in practice.
"""

from __future__ import annotations

from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .parser import RiskFactor


# Pairs with similarity below this are considered a non-match (i.e., the
# current chunk has no real counterpart in the prior filing). Tuned for
# character-bigram TF-IDF on filing-style prose.
ALIGNMENT_THRESHOLD = 0.30


@dataclass
class AlignedPair:
    """A current-period chunk paired with its prior-period counterpart, if any."""

    current: RiskFactor
    prior: RiskFactor | None
    similarity: float
    status: str  # "MATCHED" or "NEW"


@dataclass
class AlignmentResult:
    """Full output of alignment: matched pairs, new risks, and removed risks."""

    pairs: list[AlignedPair]
    removed: list[RiskFactor]  # Prior chunks that no current chunk paired to


def align(
    current_chunks: list[RiskFactor],
    prior_chunks: list[RiskFactor],
    threshold: float = ALIGNMENT_THRESHOLD,
) -> AlignmentResult:
    """Pair each current chunk with its closest prior chunk.

    Uses character-bigram TF-IDF (which handles minor word changes and
    word-order shifts well) and greedy assignment by similarity rank.

    Args:
        current_chunks: Risk factors from the newer filing.
        prior_chunks: Risk factors from the older filing.
        threshold: Minimum cosine similarity required to call something a match.

    Returns:
        AlignmentResult with pairs (one per current chunk) and removed risks.
    """
    if not current_chunks:
        return AlignmentResult(pairs=[], removed=list(prior_chunks))

    if not prior_chunks:
        # Everything in current is new.
        return AlignmentResult(
            pairs=[
                AlignedPair(current=c, prior=None, similarity=0.0, status="NEW")
                for c in current_chunks
            ],
            removed=[],
        )

    # Combined corpus so the IDF is consistent across both sides.
    corpus = [c.text for c in current_chunks] + [p.text for p in prior_chunks]
    vectorizer = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(3, 5),
        min_df=1,
        sublinear_tf=True,
    )
    vectors = vectorizer.fit_transform(corpus)

    n_current = len(current_chunks)
    current_vecs = vectors[:n_current]
    prior_vecs = vectors[n_current:]
    sim_matrix = cosine_similarity(current_vecs, prior_vecs)

    # Greedy assignment: sort all (current_idx, prior_idx) pairs by similarity
    # descending, take each as a match if both sides are still free.
    candidates = []
    for ci in range(len(current_chunks)):
        for pi in range(len(prior_chunks)):
            candidates.append((sim_matrix[ci][pi], ci, pi))
    candidates.sort(reverse=True)

    current_assigned: dict[int, tuple[int, float]] = {}
    prior_assigned: set[int] = set()

    for sim, ci, pi in candidates:
        if sim < threshold:
            break
        if ci in current_assigned or pi in prior_assigned:
            continue
        current_assigned[ci] = (pi, sim)
        prior_assigned.add(pi)

    pairs: list[AlignedPair] = []
    for ci, current in enumerate(current_chunks):
        if ci in current_assigned:
            pi, sim = current_assigned[ci]
            pairs.append(AlignedPair(
                current=current,
                prior=prior_chunks[pi],
                similarity=float(sim),
                status="MATCHED",
            ))
        else:
            pairs.append(AlignedPair(
                current=current,
                prior=None,
                similarity=0.0,
                status="NEW",
            ))

    removed = [
        prior_chunks[pi]
        for pi in range(len(prior_chunks))
        if pi not in prior_assigned
    ]

    return AlignmentResult(pairs=pairs, removed=removed)
