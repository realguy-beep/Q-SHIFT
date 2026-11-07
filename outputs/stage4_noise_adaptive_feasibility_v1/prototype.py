"""Detector-only burst-probability profiles and valid PyMatching reconstruction.

The estimator consumes calibration detector matrices only. Observable labels,
event flags, and the generating burst probability are not arguments to estimate().
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np

from outputs.phase3a_correlated_noise_preflight.simulator import (
    DEFAULT_BURST_PAIR,
    build_matching,
    build_spatial_burst_circuit,
)

DETECTOR_COUNT = 40
OBSERVABLE_COUNT = 1
BURST_DETECTOR_PAIRS = ((8, 10), (16, 18), (24, 26), (32, 34), (36, 38))
GRID_STEP = 0.00001


def detector_features(detectors: np.ndarray) -> np.ndarray:
    """Return per-shot 45 detector-only binary features.

    The first 40 features are detector bits. The final five indicate joint
    firing of the detector pairs whose graphlike DEM records are added by the
    selected burst mechanism. No observable or simulator event flags are used.
    """
    d = np.asarray(detectors)
    if d.ndim != 2 or d.shape[1] != DETECTOR_COUNT:
        raise ValueError(f"expected detectors shaped (shots,{DETECTOR_COUNT}), got {d.shape}")
    if not np.isin(d, (0, 1)).all():
        raise ValueError("detector matrix must be binary")
    d = d.astype(np.uint8, copy=False)
    pair_features = np.stack([d[:, a] & d[:, b] for a, b in BURST_DETECTOR_PAIRS], axis=1)
    return np.concatenate([d, pair_features], axis=1).astype(np.uint8, copy=False)


@dataclass(frozen=True)
class DetectorProfileEstimator:
    """One-dimensional profile estimator fitted from labeled simulator settings.

    The labels are the known probabilities used to create the *development*
    template batches. At inference, estimate() accepts detector bits only.
    Template feature means are linearly interpolated between probability knots.
    """
    probabilities: np.ndarray
    means: np.ndarray
    scales: np.ndarray
    grid_step: float = GRID_STEP

    @classmethod
    def fit(cls, batches: Sequence[tuple[float, np.ndarray]]) -> "DetectorProfileEstimator":
        if len(batches) < 2:
            raise ValueError("at least two probability profiles are required")
        grouped: dict[float, list[np.ndarray]] = {}
        all_features = []
        for p, detectors in batches:
            if not 0 <= float(p) <= 1:
                raise ValueError("profile probability must be in [0,1]")
            f = detector_features(detectors).astype(np.float64)
            if f.shape[0] < 2:
                raise ValueError("each profile batch needs at least two shots")
            grouped.setdefault(float(p), []).append(f)
            all_features.append(f)
        ps = np.asarray(sorted(grouped), dtype=np.float64)
        if ps.size < 2 or np.any(np.diff(ps) <= 0):
            raise ValueError("profile probabilities must contain at least two unique values")
        profile_means = []
        for p in ps:
            profile_means.append(np.concatenate(grouped[float(p)], axis=0).mean(axis=0))
        pooled = np.concatenate(all_features, axis=0)
        scales = np.sqrt(np.maximum(pooled.var(axis=0), 1e-6))
        return cls(ps, np.asarray(profile_means), scales)

    def estimate(self, calibration_detectors: np.ndarray) -> float:
        f = detector_features(calibration_detectors).astype(np.float64)
        if f.shape[0] < 2:
            raise ValueError("calibration batch needs at least two shots")
        observed = f.mean(axis=0)
        lo, hi = float(self.probabilities[0]), float(self.probabilities[-1])
        count = int(round((hi - lo) / self.grid_step)) + 1
        grid = np.linspace(lo, hi, max(2, count), dtype=np.float64)
        expected = np.column_stack([
            np.interp(grid, self.probabilities, self.means[:, j])
            for j in range(self.means.shape[1])
        ])
        scores = np.mean(((expected - observed[None, :]) / self.scales[None, :]) ** 2, axis=1)
        return float(grid[int(np.argmin(scores))])

    def bootstrap_interval(self, calibration_detectors: np.ndarray, *, rng: np.random.Generator,
                           replicates: int = 500) -> tuple[float, float]:
        d = np.asarray(calibration_detectors)
        if d.ndim != 2 or d.shape[1] != DETECTOR_COUNT or d.shape[0] < 2:
            raise ValueError("invalid calibration detector array")
        if replicates < 20:
            raise ValueError("at least 20 bootstrap replicates are required")
        estimates = np.empty(replicates, dtype=np.float64)
        for i in range(replicates):
            idx = rng.integers(0, d.shape[0], size=d.shape[0])
            estimates[i] = self.estimate(d[idx])
        return float(np.quantile(estimates, 0.025)), float(np.quantile(estimates, 0.975))


def build_decoder(burst_probability: float):
    """Reconstruct circuit DEM and PyMatching at a valid burst probability."""
    p = float(burst_probability)
    if not 0 <= p <= 1:
        raise ValueError("burst_probability must be in [0,1]")
    circuit = build_spatial_burst_circuit(
        memory_basis="z", regime="balanced", distance=3, rounds=5,
        gate_p=0.003, measurement_p=0.003, bias_ratio=10.0,
        burst_probability=p, burst_pair=DEFAULT_BURST_PAIR,
    )
    dem, matcher = build_matching(circuit, enable_correlations=True)
    if (circuit.num_detectors, circuit.num_observables) != (DETECTOR_COUNT, OBSERVABLE_COUNT):
        raise RuntimeError("circuit detector/observable shape changed")
    if (dem.num_detectors, dem.num_observables) != (DETECTOR_COUNT, OBSERVABLE_COUNT):
        raise RuntimeError("DEM detector/observable shape changed")
    return circuit, dem, matcher


def decode_prediction(matcher, detectors: np.ndarray) -> np.ndarray:
    d = np.asarray(detectors, dtype=np.uint8)
    if d.ndim != 2 or d.shape[1] != DETECTOR_COUNT:
        raise ValueError("invalid detector shape")
    prediction = np.asarray(matcher.decode_batch(d), dtype=np.uint8).reshape(-1)
    if prediction.shape != (d.shape[0],) or not np.isin(prediction, (0, 1)).all():
        raise RuntimeError("PyMatching prediction shape/value validation failed")
    return prediction


def logical_error_mask(prediction: np.ndarray, observable: np.ndarray) -> np.ndarray:
    p = np.asarray(prediction, dtype=np.uint8).reshape(-1)
    o = np.asarray(observable, dtype=np.uint8).reshape(-1)
    if p.shape != o.shape or not np.isin(p, (0, 1)).all() or not np.isin(o, (0, 1)).all():
        raise ValueError("prediction and observable must be aligned binary vectors")
    return p ^ o

