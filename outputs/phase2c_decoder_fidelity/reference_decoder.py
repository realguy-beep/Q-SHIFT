"""Sample-trained approximation to P(logical observable | detectors).

This is deliberately not called an exact maximum-likelihood decoder. It learns
the conditional observable probability from independent Stim samples drawn from
the requested categorical Pauli circuit, then returns the MAP bit at threshold
0.5. The model sees detector bits only at inference time.
"""
from __future__ import annotations

import numpy as np
from sklearn.ensemble import RandomForestClassifier


class SampledPosteriorDecoder:
    def __init__(self, *, seed: int, n_estimators: int = 192,
                 min_samples_leaf: int = 2, max_features: str | float = "sqrt",
                 max_depth: int | None = None):
        self.seed = int(seed)
        self.config = {
            "n_estimators": int(n_estimators),
            "min_samples_leaf": int(min_samples_leaf),
            "max_features": max_features,
            "max_depth": max_depth,
            "class_weight": None,
            "threshold": 0.5,
        }
        self.model = RandomForestClassifier(
            n_estimators=self.config["n_estimators"],
            min_samples_leaf=self.config["min_samples_leaf"],
            max_features=self.config["max_features"],
            max_depth=self.config["max_depth"],
            class_weight=None,
            random_state=self.seed,
            n_jobs=-1,
        )
        self.fit_seconds: float | None = None

    def fit(self, detectors: np.ndarray, observables: np.ndarray) -> "SampledPosteriorDecoder":
        import time

        d = np.asarray(detectors, dtype=np.uint8)
        y = np.asarray(observables, dtype=np.uint8).reshape(-1)
        if d.ndim != 2 or len(d) != len(y) or not np.isin(d, (0, 1)).all() or not np.isin(y, (0, 1)).all():
            raise ValueError("fit expects aligned binary detector rows and observable labels")
        start = time.perf_counter()
        self.model.fit(d, y)
        self.fit_seconds = time.perf_counter() - start
        return self

    def predict_probability(self, detectors: np.ndarray) -> np.ndarray:
        d = np.asarray(detectors, dtype=np.uint8)
        if d.ndim != 2 or not np.isin(d, (0, 1)).all():
            raise ValueError("predict expects a 2D binary detector array")
        classes = list(self.model.classes_)
        if 1 not in classes:
            return np.zeros(len(d), dtype=np.float64)
        return self.model.predict_proba(d)[:, classes.index(1)]

    def predict(self, detectors: np.ndarray) -> np.ndarray:
        # Exact 0.5 ties resolve to logical correction 0.
        return (self.predict_probability(detectors) > 0.5).astype(np.uint8)

