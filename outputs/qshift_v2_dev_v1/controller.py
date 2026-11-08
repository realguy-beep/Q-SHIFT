"""Small causal controller components for Q-SHIFT v2 development pilots."""
from __future__ import annotations

from dataclasses import dataclass
from collections import deque
import math
from typing import Callable

import numpy as np


@dataclass
class EventTriggeredProfile:
    """Blockwise GLR on a categorical detector summary; updates future blocks only."""
    probabilities: np.ndarray
    category_probabilities: np.ndarray
    active_p: float
    window_blocks: int = 8
    min_dwell_blocks: int = 2
    delta_p: float = 0.001
    threshold: float = 8.0

    def __post_init__(self):
        self.probabilities = np.asarray(self.probabilities, dtype=float)
        self.category_probabilities = np.asarray(self.category_probabilities, dtype=float)
        if self.category_probabilities.shape != (len(self.probabilities), 6):
            raise ValueError("need six categorical probabilities per p grid point")
        if np.any(self.category_probabilities <= 0):
            raise ValueError("categorical likelihoods must be positive")
        self.log_probs = np.log(self.category_probabilities)
        self.history: deque[np.ndarray] = deque(maxlen=self.window_blocks)
        self.blocks = 0
        self.last_update = -10**9
        self.switches = 0
        self.alarms = 0

    def observe_completed_block(self, categories: np.ndarray, estimate_fn: Callable[[np.ndarray], float]):
        """Ingest only after the block was decoded/committed; return next-block p."""
        c = np.asarray(categories, dtype=int).reshape(-1)
        if c.size == 0 or np.any((c < 0) | (c > 5)):
            raise ValueError("categories must be nonempty integers from zero through five")
        counts = np.bincount(c, minlength=6).astype(float)
        self.history.append(counts)
        self.blocks += 1
        active = int(np.argmin(np.abs(self.probabilities - self.active_p)))
        other = np.arange(len(self.probabilities)) != active
        if len(self.history) < 2:
            return self.active_p
        total = np.sum(np.stack(self.history), axis=0)
        scores = self.log_probs @ total - float(self.log_probs[active] @ total)
        glr = float(np.max(scores[other]))
        if glr <= self.threshold or self.blocks - self.last_update < self.min_dwell_blocks:
            return self.active_p
        self.alarms += 1
        p_new = float(np.clip(estimate_fn(np.asarray(categories_for_window(self.history))),
                              self.probabilities[0], self.probabilities[-1]))
        self.last_update = self.blocks
        if abs(p_new - self.active_p) >= self.delta_p:
            self.active_p = p_new
            self.switches += 1
            self.history.clear()
        return self.active_p


def categories_for_window(history: deque[np.ndarray]) -> np.ndarray:
    """Reconstruct categorical counts for profile fitting (bounded by pilot window)."""
    chunks = []
    for category, count in enumerate(np.sum(np.stack(history), axis=0).astype(int)):
        chunks.append(np.full(count, category, dtype=np.uint8))
    return np.concatenate(chunks)


class TrailingWindow:
    def __init__(self, window: int):
        self.window = window
        self.data = deque(maxlen=window)

    def push(self, detectors: np.ndarray) -> None:
        for row in np.asarray(detectors):
            self.data.append(np.asarray(row, dtype=np.uint8).copy())

    def ready(self) -> bool:
        return len(self.data) == self.window

    def estimate(self, estimator) -> float:
        return estimator.estimate(np.stack(self.data))


def pair_category(detectors: np.ndarray, pairs: tuple[tuple[int, int], ...]) -> np.ndarray:
    d = np.asarray(detectors, dtype=np.uint8)
    if d.ndim != 2 or d.shape[1] != 40:
        raise ValueError("expected (shots,40) detector matrix")
    return np.stack([d[:, a] & d[:, b] for a, b in pairs], axis=1).sum(axis=1).astype(np.uint8)


def categorical_profile(batches: list[tuple[float, np.ndarray]], pairs: tuple[tuple[int, int], ...], grid: np.ndarray) -> np.ndarray:
    """Smoothed six-bin category model, interpolated and renormalized over p."""
    ps = sorted(set(float(p) for p, _ in batches))
    table = []
    for p in ps:
        vals = np.concatenate([pair_category(d, pairs) for q, d in batches if float(q) == p])
        table.append((np.bincount(vals, minlength=6) + 0.5) / (len(vals) + 3.0))
    out = np.column_stack([np.interp(grid, ps, np.asarray(table)[:, j]) for j in range(6)])
    out = np.maximum(out, 1e-9)
    return out / out.sum(axis=1, keepdims=True)
