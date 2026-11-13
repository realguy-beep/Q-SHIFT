"""20k root-stratified bootstrap of the twelve-candidate selection ranking."""
from __future__ import annotations

from math import lcm
from typing import Sequence

import numpy as np

from .protocol import CANDIDATE_IDS, CONDITIONS, SELECTION_RANK_BOOTSTRAP_REPLICATES
from .selection import SelectionRootScore, _validate_root_scores, selection_scores


def selection_rank_bootstrap(
    records: Sequence[SelectionRootScore], rng: np.random.Generator,
) -> dict[str, object]:
    if not isinstance(rng, np.random.Generator):
        raise TypeError("rng must be a caller-supplied selection-rank Generator.")
    by_condition = _validate_root_scores(records)
    denominators = [by_condition[c][r].shots for c in CONDITIONS for r in range(8)]
    common_denominator = lcm(*denominators)
    scaled = np.empty((6, 8, 12), dtype=np.int64)
    for ci, condition in enumerate(CONDITIONS):
        for ri in range(8):
            row = by_condition[condition][ri]
            scale = common_denominator // row.shots
            for ji, candidate in enumerate(CANDIDATE_IDS):
                scaled[ci, ri, ji] = row.errors_by_candidate[candidate] * scale

    rank_counts = np.zeros((12, 12), dtype=np.int64)  # candidate × one-based rank
    top_tie_counts = np.zeros(12, dtype=np.int64)
    any_tie_replicates = 0
    condition_index = np.arange(6, dtype=np.int64)[None, :, None]
    remaining = SELECTION_RANK_BOOTSTRAP_REPLICATES
    while remaining:
        count = min(256, remaining)
        indices = rng.integers(0, 8, size=(count, 6, 8), dtype=np.int8)
        sampled = scaled[condition_index, indices, :]  # [replicate, condition, root, candidate]
        totals = sampled.sum(axis=(1, 2), dtype=np.int64)
        order = np.argsort(totals, axis=1, kind="stable")
        rows = np.arange(count)[:, None]
        ranks = np.empty_like(order)
        ranks[rows, order] = np.arange(1, 13, dtype=np.int8)[None, :]
        for candidate_i in range(12):
            rank_counts[candidate_i] += np.bincount(ranks[:, candidate_i], minlength=13)[1:13]
        minima = totals.min(axis=1, keepdims=True)
        tied_for_best = totals == minima
        top_tie_counts += tied_for_best.sum(axis=0)
        any_tie_replicates += int(np.count_nonzero(tied_for_best.sum(axis=1) > 1))
        remaining -= count

    observed = selection_scores(records)
    return {
        "replicates": SELECTION_RANK_BOOTSTRAP_REPLICATES,
        "candidate_order": CANDIDATE_IDS,
        "observed_scores": {name: {"numerator": value.numerator, "denominator": value.denominator,
                                    "value": float(value)} for name, value in observed},
        "rank_frequencies": {
            candidate: {str(rank + 1): int(rank_counts[candidate_i, rank]) / SELECTION_RANK_BOOTSTRAP_REPLICATES
                        for rank in range(12)}
            for candidate_i, candidate in enumerate(CANDIDATE_IDS)
        },
        "top_rank_frequency": {
            candidate: int(rank_counts[i, 0]) / SELECTION_RANK_BOOTSTRAP_REPLICATES
            for i, candidate in enumerate(CANDIDATE_IDS)
        },
        "top_score_tie_frequency": {
            candidate: int(top_tie_counts[i]) / SELECTION_RANK_BOOTSTRAP_REPLICATES
            for i, candidate in enumerate(CANDIDATE_IDS)
        },
        "replicate_frequency_with_any_top_tie": any_tie_replicates / SELECTION_RANK_BOOTSTRAP_REPLICATES,
        "tie_policy": "exact integer-scaled score ties; frozen candidate order determines rank order",
        "uncertainty_scope": "selection partition only; not combined into primary evaluation interval",
    }
