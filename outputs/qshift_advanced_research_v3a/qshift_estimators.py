"""Detector-only Q-SHIFT Candidate A and B population/template estimators.

This module consumes detector bits or a supplied 45-feature mean. It never
accepts an observable, logical label, true parameter, or scenario label.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Literal

import numpy as np

SCHEMA_VERSION = "qshift-template-bank-v1"
ESTIMATOR_VERSION = "qshift-joint-estimator-v1"
FAMILY = Literal["exact_categorical", "approximate_dem"]
FEATURE_PAIRS = ((8, 10), (16, 18), (24, 26), (32, 34), (36, 38))
DETECTOR_COUNT = 40
FEATURE_COUNT = 45
BURST_KNOTS = np.asarray([0.0, 0.005, 0.010, 0.015, 0.020], dtype=np.float64)
BURST_GRID = np.linspace(0.0, 0.020, 21)
MEASUREMENT_GRID = np.linspace(0.0, 0.010, 11)
FIT_BURST_GRID = np.linspace(0.0, 0.020, 201)
FIT_MEASUREMENT_GRID = np.linspace(0.0, 0.010, 101)
A_GRID = np.linspace(0.0, 0.020, 2001)
TIE_TOLERANCE = 0.0


class EstimatorInputError(ValueError):
    """Invalid detector history, feature mean, or template family."""


def detector_features(detectors: np.ndarray) -> np.ndarray:
    """Map an `(shots, 40)` binary detector array to `(shots, 45)` features."""
    d = np.asarray(detectors)
    if d.ndim != 2 or d.shape[1] != DETECTOR_COUNT:
        raise EstimatorInputError(f"detectors must have shape (shots,{DETECTOR_COUNT})")
    if d.shape[0] < 1:
        raise EstimatorInputError("detector history must contain at least one shot")
    if not np.issubdtype(d.dtype, np.number) and d.dtype != np.bool_:
        raise EstimatorInputError("detectors must be numeric binary values")
    if not np.isfinite(d).all() or not np.logical_or(d == 0, d == 1).all():
        raise EstimatorInputError("detectors must contain only finite 0/1 values")
    d = d.astype(np.uint8, copy=False)
    out = np.empty((d.shape[0], FEATURE_COUNT), dtype=np.uint8)
    out[:, :DETECTOR_COUNT] = d
    for k, (i, j) in enumerate(FEATURE_PAIRS):
        out[:, DETECTOR_COUNT + k] = d[:, i] & d[:, j]
    return out


def validate_feature_mean(mean: np.ndarray) -> np.ndarray:
    x = np.asarray(mean, dtype=np.float64)
    if x.shape != (FEATURE_COUNT,):
        raise EstimatorInputError(f"feature mean must have shape ({FEATURE_COUNT},)")
    if not np.isfinite(x).all() or np.any(x < 0.0) or np.any(x > 1.0):
        raise EstimatorInputError("feature mean entries must be finite probabilities in [0,1]")
    return x


def population_profile_scales(table: np.ndarray) -> np.ndarray:
    """Population limit of the existing pooled feature scale calculation."""
    a = np.asarray(table, dtype=np.float64)
    if a.shape != (len(BURST_GRID), len(MEASUREMENT_GRID), FEATURE_COUNT):
        raise EstimatorInputError("template table has an invalid shape for profile scales")
    p_idx = [0, 5, 10, 15, 20]
    m_idx = int(np.argmin(np.abs(MEASUREMENT_GRID - 0.003)))
    if not np.isclose(MEASUREMENT_GRID[m_idx], 0.003, atol=1e-12):
        raise EstimatorInputError("template grid must contain measurement probability .003")
    means = a[p_idx, m_idx, :]
    pooled_mean = means.mean(axis=0)
    within = np.mean(means * (1.0 - means), axis=0)
    between = np.mean((means - pooled_mean) ** 2, axis=0)
    return np.sqrt(np.maximum(within + between, 1e-6))


@dataclass(frozen=True)
class TemplateBank:
    """Versioned exact-categorical and approximate-DEM population templates."""
    burst_grid: np.ndarray
    measurement_grid: np.ndarray
    means: dict[str, np.ndarray]
    scales: dict[str, np.ndarray]
    provenance: dict
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise EstimatorInputError(f"unsupported template schema {self.schema_version!r}")
        if not np.array_equal(np.asarray(self.burst_grid), BURST_GRID):
            raise EstimatorInputError("burst grid differs from the published Phase 2C grid")
        if not np.array_equal(np.asarray(self.measurement_grid), MEASUREMENT_GRID):
            raise EstimatorInputError("measurement grid differs from the published Phase 2C grid")
        for family in ("exact_categorical", "approximate_dem"):
            if family not in self.means or family not in self.scales:
                raise EstimatorInputError(f"missing template family {family}")
            table = np.asarray(self.means[family], dtype=np.float64)
            scale = np.asarray(self.scales[family], dtype=np.float64)
            if table.shape != (21, 11, FEATURE_COUNT):
                raise EstimatorInputError(f"{family} means must have shape (21,11,45)")
            if not np.isfinite(table).all() or np.any(table < 0) or np.any(table > 1):
                raise EstimatorInputError(f"{family} means must be finite probabilities")
            if scale.shape != (FEATURE_COUNT,) or not np.isfinite(scale).all() or np.any(scale <= 0):
                raise EstimatorInputError(f"{family} scales must be positive 45-vectors")
            expected = population_profile_scales(table)
            if not np.allclose(scale, expected, atol=1e-14, rtol=1e-12):
                raise EstimatorInputError(f"{family} scales do not match the population profile rule")
        if self.provenance.get("gate_p") != 0.003:
            raise EstimatorInputError("template gate_p provenance must explicitly equal .003")

    @classmethod
    def from_tables(cls, exact: np.ndarray, dem: np.ndarray, provenance: dict) -> "TemplateBank":
        means = {"exact_categorical": np.asarray(exact, dtype=np.float64),
                 "approximate_dem": np.asarray(dem, dtype=np.float64)}
        scales = {name: population_profile_scales(table) for name, table in means.items()}
        return cls(BURST_GRID.copy(), MEASUREMENT_GRID.copy(), means, scales, dict(provenance))

    def to_dict(self) -> dict:
        return {"schema_version": self.schema_version,
                "feature_definition": {"detectors": DETECTOR_COUNT, "features": FEATURE_COUNT,
                    "pairs": [list(p) for p in FEATURE_PAIRS],
                    "order": "D0..D39 then pair conjunctions in listed order"},
                "burst_grid": self.burst_grid.tolist(),
                "measurement_grid": self.measurement_grid.tolist(),
                "means": {k: v.tolist() for k, v in self.means.items()},
                "scales": {k: v.tolist() for k, v in self.scales.items()},
                "provenance": self.provenance}

    def save(self, path: str | Path) -> str:
        target = Path(path)
        payload = json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload, encoding="utf-8")
        return hashlib.sha256(target.read_bytes()).hexdigest()

    @classmethod
    def load(cls, path: str | Path) -> "TemplateBank":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        feature_definition = raw.get("feature_definition", {})
        if (feature_definition.get("detectors") != DETECTOR_COUNT or
                feature_definition.get("features") != FEATURE_COUNT or
                feature_definition.get("pairs") != [list(p) for p in FEATURE_PAIRS] or
                feature_definition.get("order") != "D0..D39 then pair conjunctions in listed order"):
            raise EstimatorInputError("serialized pair-feature definition is not recognized")
        return cls(np.asarray(raw["burst_grid"], dtype=np.float64),
                   np.asarray(raw["measurement_grid"], dtype=np.float64),
                   {k: np.asarray(v, dtype=np.float64) for k, v in raw["means"].items()},
                   {k: np.asarray(v, dtype=np.float64) for k, v in raw["scales"].items()},
                   raw["provenance"], raw["schema_version"])

    def interpolated(self, family: FAMILY, burst: float, measurement: float) -> np.ndarray:
        _validate_family(family)
        pb = _validate_parameter(burst, "p_burst", 0.0, 0.020)
        pm = _validate_parameter(measurement, "p_measurement", 0.0, 0.010)
        return bilinear(self.means[family], pb, pm)


def _validate_family(family: str) -> None:
    if family not in ("exact_categorical", "approximate_dem"):
        raise EstimatorInputError("family must be exact_categorical or approximate_dem")


def _validate_parameter(value: float, name: str, lo: float, hi: float) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError) as exc:
        raise EstimatorInputError(f"{name} must be a finite number") from exc
    if not np.isfinite(x) or x < lo or x > hi:
        raise EstimatorInputError(f"{name} must be finite and in [{lo},{hi}]")
    return x


def bilinear(table: np.ndarray, burst: float, measurement: float) -> np.ndarray:
    pb = _validate_parameter(burst, "p_burst", 0.0, 0.020)
    pm = _validate_parameter(measurement, "p_measurement", 0.0, 0.010)
    i = min(max(int(np.searchsorted(BURST_GRID, pb, side="right") - 1), 0), 19)
    j = min(max(int(np.searchsorted(MEASUREMENT_GRID, pm, side="right") - 1), 0), 9)
    u = (pb - BURST_GRID[i]) / (BURST_GRID[i + 1] - BURST_GRID[i])
    v = (pm - MEASUREMENT_GRID[j]) / (MEASUREMENT_GRID[j + 1] - MEASUREMENT_GRID[j])
    a = np.asarray(table, dtype=np.float64)
    return ((1-u)*(1-v)*a[i,j] + u*(1-v)*a[i+1,j]
            + (1-u)*v*a[i,j+1] + u*v*a[i+1,j+1])


@dataclass(frozen=True)
class Estimate:
    estimator: str
    family: FAMILY
    p_burst: float
    p_measurement: float
    objective: float
    boundary_hit: bool
    history_length: int | None
    template_schema: str = SCHEMA_VERSION
    estimator_version: str = ESTIMATOR_VERSION

    def to_dict(self) -> dict:
        return {"estimator": self.estimator, "family": self.family,
                "p_burst": self.p_burst, "p_measurement": self.p_measurement,
                "objective": self.objective, "boundary_hit": self.boundary_hit,
                "history_length": self.history_length,
                "template_schema": self.template_schema,
                "estimator_version": self.estimator_version}


class CandidateA:
    """Source-faithful population-limit counterpart of DetectorProfileEstimator."""
    def __init__(self, bank: TemplateBank, family: FAMILY):
        _validate_family(family)
        self.bank, self.family = bank, family
        knots = [0, 5, 10, 15, 20]
        pm_idx = 3  # the published .001 grid contains p_m=.003
        self.templates = bank.means[family][knots, pm_idx, :]
        self.scales = bank.scales[family]
        # These values depend only on the immutable template bank. Cache them
        # once instead of rebuilding 45 interpolants for every history.
        self._scaled_surface = np.column_stack([
            np.interp(A_GRID, BURST_KNOTS, self.templates[:, k])
            for k in range(FEATURE_COUNT)
        ]) / self.scales[None, :]

    def estimate_mean(self, mean: np.ndarray, history_length: int | None = None) -> Estimate:
        target = validate_feature_mean(mean)
        residual = self._scaled_surface - target[None, :] / self.scales[None, :]
        scores = np.einsum('ij,ij->i', residual, residual) / FEATURE_COUNT
        idx = int(np.argmin(scores))  # ordered grid supplies lower-p tie break
        pb = float(A_GRID[idx])
        hit = bool(idx == 0 or idx == len(A_GRID)-1)
        return Estimate("candidate_a_population_limit", self.family, pb, 0.003,
                        float(scores[idx]), hit, history_length)

    def estimate(self, detectors: np.ndarray) -> Estimate:
        f = detector_features(detectors)
        return self.estimate_mean(f.mean(axis=0), history_length=f.shape[0])


class CandidateB:
    """Joint standardized 45-feature fit on the Phase 2C two-parameter grid."""
    def __init__(self, bank: TemplateBank, family: FAMILY,
                 tie_tolerance: float = TIE_TOLERANCE):
        _validate_family(family)
        if not np.isfinite(tie_tolerance) or tie_tolerance < 0:
            raise EstimatorInputError("tie_tolerance must be finite and nonnegative")
        self.bank, self.family = bank, family
        self.tie_tolerance = float(tie_tolerance)
        self.scales = bank.scales[family]
        self.surface = self._build_surface()
        self._scaled_surface = self.surface / self.scales[None, None, :]

    def _build_surface(self) -> np.ndarray:
        table = self.bank.means[self.family]
        bi = np.clip(np.searchsorted(BURST_GRID, FIT_BURST_GRID, side="right") - 1, 0, 19)
        mj = np.clip(np.searchsorted(MEASUREMENT_GRID, FIT_MEASUREMENT_GRID, side="right") - 1, 0, 9)
        bu = (FIT_BURST_GRID - BURST_GRID[bi]) / (BURST_GRID[bi + 1] - BURST_GRID[bi])
        mv = (FIT_MEASUREMENT_GRID - MEASUREMENT_GRID[mj]) / (MEASUREMENT_GRID[mj + 1] - MEASUREMENT_GRID[mj])
        b0, b1 = bi[:, None], (bi + 1)[:, None]
        m0, m1 = mj[None, :], (mj + 1)[None, :]
        u, v = bu[:, None, None], mv[None, :, None]
        a00, a10 = table[b0, m0], table[b1, m0]
        a01, a11 = table[b0, m1], table[b1, m1]
        return ((1-u)*(1-v)*a00 + u*(1-v)*a10
                + (1-u)*v*a01 + u*v*a11)

    def estimate_mean(self, mean: np.ndarray, history_length: int | None = None) -> Estimate:
        target = validate_feature_mean(mean)
        residual = self._scaled_surface - target[None, None, :] / self.scales[None, None, :]
        scores = np.einsum('ijk,ijk->ij', residual, residual) / FEATURE_COUNT
        best = float(scores.min())
        # Flatten order is p_burst outer, p_measurement inner. Include exact
        # floating-point score ties only; the first index is lexicographically lower.
        candidates = np.flatnonzero(scores.ravel() <= best + self.tie_tolerance)
        flat = int(candidates[0])
        i, j = np.unravel_index(flat, scores.shape)
        pb, pm = float(FIT_BURST_GRID[i]), float(FIT_MEASUREMENT_GRID[j])
        hit = bool(i == 0 or i == len(FIT_BURST_GRID)-1 or
                   j == 0 or j == len(FIT_MEASUREMENT_GRID)-1)
        return Estimate("candidate_b_joint_standardized", self.family, pb, pm,
                        float(scores[i,j]), hit, history_length)

    def estimate(self, detectors: np.ndarray) -> Estimate:
        f = detector_features(detectors)
        return self.estimate_mean(f.mean(axis=0), history_length=f.shape[0])
