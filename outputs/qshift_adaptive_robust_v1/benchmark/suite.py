"""Broad-noise benchmark DRAFT definition (BROAD_NOISE_BENCHMARK.md). Data structures only: no sampling.

This is a design draft. It becomes binding only when copied into a frozen protocol with hashes, a commit,
and an owner sampling authorization. Nothing here has been sampled.
"""
from __future__ import annotations

from dataclasses import dataclass

SPLITS = ("dev", "val", "eval", "ood")
SEED_NAMESPACES = {s: f"qshift-adaptive-robust-v1:{s}" for s in SPLITS}


@dataclass(frozen=True)
class Condition:
    cid: str
    split: str
    distance: int
    gate_p: float
    measurement_p: float
    regime: str            # model_v14 background regime: balanced | z_biased | measurement_heavy | data_heavy
    burst: str             # burst family or "none"
    q: float               # burst probability per shot
    assumed_scale: float = 1.0   # decoder/learner assumed p = true p / assumed_scale (mismatch axis)
    drift: str = "static"        # static | step | ramp
    weight: float = 1.0

    @property
    def burst_free(self) -> bool:
        return self.q == 0.0 or self.burst == "none"


def _grid(split: str, prefix: str, rows: list[tuple]) -> list[Condition]:
    return [Condition(f"{prefix}{i:02d}", split, *r) for i, r in enumerate(rows)]


# (distance, gate_p, meas_p, regime, burst, q, assumed_scale, drift)
DEV = _grid("dev", "D", [
    (5, 0.003, 0.003, "balanced", "scaled_v1", 0.0, 1.0, "static"),
    (5, 0.003, 0.003, "balanced", "scaled_v1", 0.02, 1.0, "static"),
    (5, 0.002, 0.002, "balanced", "scaled_v1", 0.01, 1.0, "static"),
    (5, 0.003, 0.003, "balanced", "scaled_v1", 0.02, 0.83, "static"),   # true p 17% below assumed
    (5, 0.003, 0.003, "balanced", "scaled_v1", 0.02, 1.17, "static"),   # true p 17% above assumed
    (3, 0.003, 0.003, "balanced", "scaled_v1", 0.02, 1.0, "static"),
])
VAL = _grid("val", "V", [
    (5, 0.0015, 0.0015, "balanced", "centre_row", 0.02, 1.0, "static"),
    (5, 0.003, 0.009, "measurement_heavy", "scaled_v1", 0.02, 1.0, "static"),
    (5, 0.003, 0.003, "z_biased", "scaled_v1", 0.02, 1.0, "static"),
    (5, 0.003, 0.003, "balanced", "scaled_v1", 0.02, 1.0, "step"),
    (5, 0.0025, 0.0025, "balanced", "none", 0.0, 1.0, "static"),
])
EVAL = _grid("eval", "E", [
    # burst-present conditions: enter the primary pooled endpoint if eligible
    (3, 0.003, 0.003, "balanced", "fresh_geometry_A", 0.02, 1.0, "static"),
    (5, 0.001, 0.001, "balanced", "fresh_geometry_A", 0.02, 1.0, "static"),
    (5, 0.002, 0.002, "balanced", "fresh_geometry_B", 0.01, 1.0, "static"),
    (5, 0.003, 0.003, "balanced", "fresh_geometry_B", 0.02, 1.0, "static"),
    (5, 0.003, 0.009, "measurement_heavy", "fresh_geometry_A", 0.02, 1.0, "static"),
    (5, 0.003, 0.001, "data_heavy", "fresh_geometry_B", 0.02, 1.0, "static"),
    (5, 0.003, 0.003, "z_biased", "fresh_geometry_A", 0.02, 1.0, "static"),
    (5, 0.003, 0.003, "balanced", "fresh_geometry_A", 0.02, 0.85, "static"),
    (5, 0.003, 0.003, "balanced", "fresh_geometry_B", 0.02, 1.20, "static"),
    (5, 0.002, 0.002, "balanced", "fresh_geometry_A", 0.02, 1.0, "step"),
    # burst-free safety conditions: background-only safety endpoint, not the reduction endpoint
    (5, 0.001, 0.001, "balanced", "none", 0.0, 1.0, "static"),
    (5, 0.003, 0.003, "balanced", "none", 0.0, 1.0, "static"),
    (5, 0.003, 0.003, "z_biased", "none", 0.0, 1.0, "static"),
])
OOD = _grid("ood", "O", [
    (5, 0.003, 0.003, "balanced", "weight4_fresh", 0.02, 1.0, "static"),
    (5, 0.002, 0.004, "z_biased", "two_family_mixture", 0.02, 1.1, "ramp"),
    (7, 0.002, 0.002, "balanced", "fresh_geometry_A", 0.02, 1.0, "static"),    # exploratory, cost-capped
])
ALL = DEV + VAL + EVAL + OOD


def by_split(split: str) -> list[Condition]:
    return [c for c in ALL if c.split == split]


def primary_conditions() -> list[Condition]:
    """Eval conditions entering the pooled reduction endpoint (eligibility still applies)."""
    return [c for c in by_split("eval") if not c.burst_free]


def safety_conditions() -> list[Condition]:
    return [c for c in by_split("eval") if c.burst_free]
