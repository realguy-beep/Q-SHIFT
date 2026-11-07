"""Detector-grid encoders and a compact CNN/regression noise estimator."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np
import torch
from torch import nn

from outputs.stage4_noise_adaptive_feasibility_v1.prototype import (
    BURST_DETECTOR_PAIRS, DETECTOR_COUNT, detector_features,
)

GRID_SHAPE = (6, 4, 4)  # time, y, x, derived from the frozen Stim detector coordinates
MAX_BURST_PROBABILITY = 0.02


def detector_coordinate_map(coordinates: Mapping[int, Sequence[float]]) -> dict[int, tuple[int, int, int]]:
    """Convert Stim [x,y,t] coordinates to integer (t,y,x) tensor indices."""
    if set(map(int, coordinates)) != set(range(DETECTOR_COUNT)):
        raise ValueError("coordinate map must contain detector ids 0..39 exactly")
    result: dict[int, tuple[int, int, int]] = {}
    occupied = set()
    for detector_id, coord in coordinates.items():
        if len(coord) < 3:
            raise ValueError(f"detector {detector_id} has fewer than 3 coordinates")
        x, y, t = (float(coord[0]), float(coord[1]), float(coord[2]))
        ti, yi, xi = int(round(t)), int(round(y / 2)), int(round(x / 2))
        if abs(t - ti) > 1e-8 or abs(y / 2 - yi) > 1e-8 or abs(x / 2 - xi) > 1e-8:
            raise ValueError(f"unexpected non-grid Stim detector coordinate {detector_id}: {coord}")
        if not (0 <= ti < GRID_SHAPE[0] and 0 <= yi < GRID_SHAPE[1] and 0 <= xi < GRID_SHAPE[2]):
            raise ValueError(f"detector coordinate outside expected grid: {detector_id}: {coord}")
        point = (ti, yi, xi)
        if point in occupied:
            raise ValueError(f"multiple detectors share grid point {point}")
        occupied.add(point)
        result[int(detector_id)] = point
    if len(occupied) != DETECTOR_COUNT:
        raise ValueError("detector mapping is not bijective")
    return result


def batch_feature_vector(detectors: np.ndarray) -> np.ndarray:
    """Stage 4B's 45 detector-only empirical marginal/cofire rates."""
    d = np.asarray(detectors)
    if d.ndim != 2 or d.shape[1] != DETECTOR_COUNT or d.shape[0] < 2:
        raise ValueError(f"expected at least 2 detector rows with width {DETECTOR_COUNT}")
    if not np.isin(d, (0, 1)).all():
        raise ValueError("detectors must be binary")
    return detector_features(d.astype(np.uint8, copy=False)).mean(axis=0, dtype=np.float64)


def encode_calibration_batch(detectors: np.ndarray,
                             coordinate_map: Mapping[int, tuple[int, int, int]]) -> np.ndarray:
    """Make (3,6,4,4) input: detector rates, pair cofires, occupancy mask.

    Each joint feature from the Stage 4B burst-pair list is stored at both
    endpoint voxels. The endpoint locations are explicit and match Stim's
    detector-coordinate map; the occupancy channel disambiguates absent cells.
    """
    d = np.asarray(detectors)
    if d.ndim != 2 or d.shape[1] != DETECTOR_COUNT or d.shape[0] < 2:
        raise ValueError("invalid detector batch for CNN encoding")
    if not np.isin(d, (0, 1)).all():
        raise ValueError("detectors must be binary")
    x = np.zeros((3, *GRID_SHAPE), dtype=np.float32)
    for detector_id, point in coordinate_map.items():
        x[0, point[0], point[1], point[2]] = float(d[:, detector_id].mean())
        x[2, point[0], point[1], point[2]] = 1.0
    for a, b in BURST_DETECTOR_PAIRS:
        cofire = float(np.logical_and(d[:, a], d[:, b]).mean())
        for detector_id in (a, b):
            point = coordinate_map[detector_id]
            x[1, point[0], point[1], point[2]] = cofire
    return x


class BurstProbabilityCNN(nn.Module):
    """Small position- and time-preserving regression CNN for calibration batches."""

    def __init__(self, channels: int = 4, head_width: int = 16):
        super().__init__()
        if channels != 4 or head_width != 16:
            raise ValueError("Stage 4C frozen architecture uses channels=4 and head_width=16")
        self.features = nn.Sequential(
            nn.Conv3d(3, channels, kernel_size=3, padding=1),
            nn.GELU(),
            nn.Conv3d(channels, channels, kernel_size=3, padding=1),
            nn.GELU(),
            nn.Flatten(start_dim=1),
        )
        self.head = nn.Sequential(
            nn.Linear(channels * GRID_SHAPE[0] * GRID_SHAPE[1] * GRID_SHAPE[2], head_width),
            nn.GELU(),
            nn.Linear(head_width, 1),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.ndim != 5 or tuple(x.shape[1:]) != (3, *GRID_SHAPE):
            raise ValueError(f"expected (batch,3,{GRID_SHAPE}), got {tuple(x.shape)}")
        return self.head(self.features(x)).squeeze(-1)


def parameter_count(model: nn.Module) -> int:
    return sum(parameter.numel() for parameter in model.parameters())


@dataclass
class RidgeBurstRegressor:
    mean: np.ndarray
    scale: np.ndarray
    coef: np.ndarray
    alpha: float

    @classmethod
    def fit(cls, x: np.ndarray, y: np.ndarray, alpha: float) -> "RidgeBurstRegressor":
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64).reshape(-1)
        if x.ndim != 2 or x.shape[0] != y.size or x.shape[0] < 2:
            raise ValueError("invalid Ridge training arrays")
        mean = x.mean(axis=0)
        scale = np.where(x.std(axis=0) > 1e-9, x.std(axis=0), 1.0)
        z = (x - mean) / scale
        design = np.column_stack([np.ones(z.shape[0]), z])
        penalty = np.eye(design.shape[1], dtype=np.float64) * float(alpha)
        penalty[0, 0] = 0.0
        coef = np.linalg.solve(design.T @ design + penalty, design.T @ y)
        return cls(mean, scale, coef, float(alpha))

    def predict(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=np.float64)
        z = (x - self.mean) / self.scale
        design = np.column_stack([np.ones(z.shape[0]), z])
        return np.clip(design @ self.coef, 0.0, MAX_BURST_PROBABILITY)


def ridge_predictions_for_calibration(model: RidgeBurstRegressor, detectors: np.ndarray,
                                      chunk_shots: int = 250) -> tuple[float, float]:
    """Estimate p by averaging predictions on disjoint fixed-size detector chunks."""
    d = np.asarray(detectors)
    if d.ndim != 2 or d.shape[0] % chunk_shots:
        raise ValueError("calibration rows must be divisible into frozen chunk size")
    features = np.stack([batch_feature_vector(c) for c in d.reshape(-1, chunk_shots, DETECTOR_COUNT)])
    estimates = model.predict(features)
    return float(estimates.mean()), float(np.mean(np.abs(estimates - estimates.mean())))


def encode_training_batches(detector_batches: np.ndarray,
                            coordinate_map: Mapping[int, tuple[int, int, int]]) -> np.ndarray:
    batches = np.asarray(detector_batches)
    if batches.ndim != 3 or batches.shape[2] != DETECTOR_COUNT:
        raise ValueError("expected (batches,shots,40) detector batches")
    return np.stack([encode_calibration_batch(b, coordinate_map) for b in batches])


def ridge_features_for_batches(detector_batches: np.ndarray) -> np.ndarray:
    batches = np.asarray(detector_batches)
    if batches.ndim != 3 or batches.shape[2] != DETECTOR_COUNT:
        raise ValueError("expected (batches,shots,40) detector batches")
    return np.stack([batch_feature_vector(b) for b in batches])
