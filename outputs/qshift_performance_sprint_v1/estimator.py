"""Small detector-only ridge estimator for the development pilot."""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class RidgeProfile:
    mean: np.ndarray
    scale: np.ndarray
    coef: np.ndarray
    intercept: float
    alpha: float
    clip_min: float
    clip_max: float

    @classmethod
    def fit(cls, detectors: np.ndarray, probability_targets: np.ndarray,
            *, alpha: float = 10.0, clip: tuple[float, float] = (0.0, 0.016)) -> "RidgeProfile":
        x = np.asarray(detectors, dtype=np.float64)
        y = np.asarray(probability_targets, dtype=np.float64).reshape(-1)
        if x.ndim != 2 or x.shape[1] != 40 or len(x) != len(y) or len(x) == 0:
            raise ValueError("training data must be nonempty [shots,40] with one p target per row")
        if not np.isfinite(x).all() or np.any((x != 0) & (x != 1)):
            raise ValueError("training detector features must be finite binary values")
        if not np.isfinite(y).all() or np.any((y < clip[0]) | (y > clip[1])):
            raise ValueError("training p targets are outside the frozen range")
        if not np.isfinite(alpha) or alpha <= 0:
            raise ValueError("alpha must be positive and finite")
        mean = x.mean(axis=0)
        scale = x.std(axis=0)
        scale[scale < 1e-12] = 1.0
        z = (x - mean) / scale
        y_mean = float(y.mean())
        gram = z.T @ z + float(alpha) * np.eye(z.shape[1])
        coef = np.linalg.solve(gram, z.T @ (y - y_mean))
        return cls(mean, scale, coef, y_mean, float(alpha), float(clip[0]), float(clip[1]))

    def predict(self, detectors: np.ndarray) -> np.ndarray:
        x = np.asarray(detectors, dtype=np.float64)
        if x.ndim != 2 or x.shape[1] != len(self.mean) or len(x) == 0:
            raise ValueError("prediction data must be nonempty [shots,40]")
        if not np.isfinite(x).all() or np.any((x != 0) & (x != 1)):
            raise ValueError("prediction features must be finite binary values")
        values = self.intercept + ((x - self.mean) / self.scale) @ self.coef
        return np.clip(values, self.clip_min, self.clip_max)

    def predict_mean(self, detectors: np.ndarray) -> float:
        return float(np.mean(self.predict(detectors)))

    def to_dict(self) -> dict:
        return {
            "mean": self.mean.tolist(), "scale": self.scale.tolist(),
            "coef": self.coef.tolist(), "intercept": self.intercept,
            "alpha": self.alpha, "clip_min": self.clip_min, "clip_max": self.clip_max,
            "feature_count": 40, "input": "detector bits only",
        }

    @classmethod
    def from_dict(cls, value: dict) -> "RidgeProfile":
        if value.get("feature_count") != 40 or value.get("input") != "detector bits only":
            raise ValueError("estimator identity mismatch")
        return cls(*(np.asarray(value[k], dtype=np.float64) for k in ("mean", "scale", "coef")),
                   float(value["intercept"]), float(value["alpha"]),
                   float(value["clip_min"]), float(value["clip_max"]))