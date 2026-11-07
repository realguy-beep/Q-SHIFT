"""Small, bounded utilities for diagnosing rare-positive neural decoder collapse."""
from __future__ import annotations

import math

import numpy as np


def debias_weighted_logits(logits, positive_weight: float):
    """Undo the ideal log-odds shift induced by positive-weighted BCE.

    If the model estimates the optimum of BCEWithLogitsLoss(pos_weight=w),
    its logit is logit(P(y=1|x)) + log(w). This correction is only a calibration
    identity under a correctly specified, well-optimized model; validation must
    still assess the resulting probabilities.
    """
    if not math.isfinite(float(positive_weight)) or float(positive_weight) <= 0:
        raise ValueError("positive_weight must be finite and positive")
    return np.asarray(logits) - math.log(float(positive_weight))


def group_label_bound(detectors, labels) -> dict:
    """Best accuracy attainable by a deterministic detector-only lookup rule."""
    d = np.asarray(detectors, dtype=np.uint8)
    y = np.asarray(labels, dtype=np.uint8).reshape(-1)
    if d.ndim != 2 or len(d) != len(y):
        raise ValueError("Expected aligned [shots, detectors] and [shots] arrays")
    if np.any(d > 1) or np.any(y > 1):
        raise ValueError("Features and labels must be binary")
    groups: dict[bytes, list[int]] = {}
    for row, label in zip(d, y):
        key = np.packbits(row, bitorder="little").tobytes()
        counts = groups.setdefault(key, [0, 0])
        counts[int(label)] += 1
    contradictory = [counts for counts in groups.values() if counts[0] and counts[1]]
    attainable = sum(max(counts) for counts in groups.values())
    return {"n": len(y), "unique_feature_vectors": len(groups),
            "repeated_feature_rows": len(y) - len(groups),
            "contradictory_feature_vectors": len(contradictory),
            "rows_in_contradictory_groups": int(sum(sum(v) for v in contradictory)),
            "best_deterministic_correct": int(attainable),
            "best_deterministic_accuracy": float(attainable / max(1, len(y)))}


def balanced_batch_indices(labels, batch_size: int, rng: np.random.Generator) -> np.ndarray:
    """Draw a deterministic, balanced binary minibatch with replacement."""
    y = np.asarray(labels, dtype=np.uint8).reshape(-1)
    if batch_size <= 0 or batch_size % 2:
        raise ValueError("batch_size must be a positive even integer")
    if np.any((y > 1)):
        raise ValueError("labels must be binary")
    negative = np.flatnonzero(y == 0)
    positive = np.flatnonzero(y == 1)
    if not len(negative) or not len(positive):
        raise ValueError("balanced batches require both classes")
    chosen = np.concatenate((rng.choice(negative, batch_size // 2, replace=True),
                             rng.choice(positive, batch_size // 2, replace=True)))
    rng.shuffle(chosen)
    return chosen


def confusion_counts(labels, predictions) -> dict:
    y = np.asarray(labels, dtype=np.uint8).reshape(-1)
    p = np.asarray(predictions, dtype=np.uint8).reshape(-1)
    if y.shape != p.shape or np.any(y > 1) or np.any(p > 1):
        raise ValueError("labels and predictions must be aligned binary arrays")
    return {"tn": int(np.count_nonzero((y == 0) & (p == 0))),
            "fp": int(np.count_nonzero((y == 0) & (p == 1))),
            "fn": int(np.count_nonzero((y == 1) & (p == 0))),
            "tp": int(np.count_nonzero((y == 1) & (p == 1)))}
