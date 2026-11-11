"""Detector-only pooled-static calibration for prospective strong-baseline v2.

The profile-fitting function accepts only template batches tagged with their
known template probabilities. The pooled evaluation-calibration function
accepts arrays only; condition labels cannot be represented in its API.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np

from outputs.strong_fixed_baselines_v1.experiment_core import (
    detector_profile_estimator,
    validate_binary,
)


def fit_template_profiles(
    template_batches: Sequence[tuple[float, np.ndarray]],
    *,
    detector_count: int = 40,
) -> Any:
    """Fit detector-feature profiles from independently generated templates.

    These probabilities describe the fixed template-generation settings; they
    are not labels attached to final calibration samples.
    """
    if not template_batches:
        raise ValueError("independent template batches are required")
    normalized: list[tuple[float, np.ndarray]] = []
    seen: set[float] = set()
    for probability, detectors in template_batches:
        p = float(probability)
        if p in seen:
            raise ValueError(f"duplicate template probability: {p}")
        seen.add(p)
        d = validate_binary("template detectors", detectors)
        if d.ndim != 2 or d.shape[1] != detector_count or d.shape[0] == 0:
            raise ValueError("template detector shape is invalid")
        normalized.append((p, d))
    return detector_profile_estimator(normalized)


def estimate_pooled_probability(
    estimator: Any,
    calibration_detector_batches: Sequence[np.ndarray],
    *,
    detector_count: int = 40,
) -> tuple[float, np.ndarray]:
    """Estimate one p from concatenated detector rows, with no label channel.

    Each input must be a binary detector matrix. Tuples such as
    ``(generating_probability, detectors)`` are explicitly rejected.
    """
    if not calibration_detector_batches:
        raise ValueError("calibration detector batches are required")
    clean: list[np.ndarray] = []
    for batch in calibration_detector_batches:
        if isinstance(batch, tuple):
            raise TypeError("condition-tagged calibration input is forbidden")
        d = validate_binary("pooled calibration detectors", batch)
        if d.ndim != 2 or d.shape[1] != detector_count or d.shape[0] == 0:
            raise ValueError("calibration detector shape is invalid")
        clean.append(d)
    pooled = np.concatenate(clean, axis=0)
    p_hat = float(estimator.estimate(pooled))
    if not np.isfinite(p_hat) or not 0.0 <= p_hat <= 0.02:
        raise ValueError("estimated burst probability is outside the frozen profile range")
    return p_hat, pooled


def calibrate_pooled_static(
    template_batches: Sequence[tuple[float, np.ndarray]],
    calibration_detector_batches: Sequence[np.ndarray],
    *,
    detector_count: int = 40,
) -> tuple[Any, float, np.ndarray]:
    """Fit on templates, then estimate from pooled detector-only batches."""
    estimator = fit_template_profiles(template_batches, detector_count=detector_count)
    p_hat, pooled = estimate_pooled_probability(
        estimator, calibration_detector_batches, detector_count=detector_count
    )
    return estimator, p_hat, pooled
