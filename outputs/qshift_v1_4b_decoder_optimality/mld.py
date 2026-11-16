"""Exact logical-class inference on a Stim detector error model (DEM).

For a DEM whose mechanisms are independent Bernoulli faults i with probability
p_i, detector signature D_i and logical parity L_i, this computes exactly

    P(s, l) = sum_{e in {0,1}^N : sum_i e_i D_i = s, sum_i e_i L_i = l} prod_i p_i^e_i (1-p_i)^(1-e_i)

for each observed syndrome s and l in {0,1}, and decodes argmax_l P(s, l). That is
maximum a posteriori *logical-class* (maximum-likelihood) decoding for the DEM.

Method: variable elimination in detector order. Mechanisms are absorbed when their
lowest-index detector is reached; a detector is conditioned on its observed value
(and eliminated) once every mechanism touching it has been absorbed. The working
table is over the currently open detectors plus the logical bit, so cost is
O(N * 2^(w+1)) per shot for maximum open width w (w = 11 for the V1.1 d=3 DEM).
Tables are renormalized after each conditioning; the log normalizer is tracked.

What "exact" covers: exact for the DEM as given. Stim's DEM conversion with
approximate_disjoint_errors=True replaces each categorical PAULI_CHANNEL_2 by
independent mechanisms (an O(p^2) approximation of the circuit noise), so this is
not exact maximum-likelihood decoding of the circuit itself.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import stim


@dataclass(frozen=True)
class Mechanism:
    p: float
    detectors: tuple[int, ...]
    logical: int


def dem_mechanisms(dem: stim.DetectorErrorModel) -> list[Mechanism]:
    """Flatten a DEM into mechanisms; merge identical signatures exactly (XOR of independents)."""
    if dem.num_observables != 1:
        raise ValueError("expected exactly one logical observable")
    merged: dict[tuple[tuple[int, ...], int], float] = {}
    for inst in dem.flattened():
        if inst.type != "error":
            continue
        dets: set[int] = set()
        logical = 0
        for t in inst.targets_copy():
            if t.is_separator():
                continue  # decomposed DEMs only; components are XORed into one signature here
            if t.is_relative_detector_id():
                dets ^= {t.val}
            elif t.is_logical_observable_id():
                logical ^= 1
        key = (tuple(sorted(dets)), logical)
        p = float(inst.args_copy()[0])
        q = merged.get(key, 0.0)
        merged[key] = q * (1 - p) + p * (1 - q)
    return [Mechanism(p, d, l) for (d, l), p in merged.items() if p > 0]


class ExactLogicalDecoder:
    def __init__(self, dem: stim.DetectorErrorModel):
        self.num_detectors = dem.num_detectors
        mechs = dem_mechanisms(dem)
        if any(not m.detectors for m in mechs):
            # Detector-free mechanisms only flip the logical; fold them into a prior on L.
            pass
        self.logical_only = [m for m in mechs if not m.detectors]
        self.by_min: dict[int, list[Mechanism]] = {}
        for m in mechs:
            if m.detectors:
                self.by_min.setdefault(m.detectors[0], []).append(m)
        self.max_width = self._plan_width()

    def _plan_width(self) -> int:
        opened: set[int] = set()
        width = 0
        for t in range(self.num_detectors):
            for m in self.by_min.get(t, []):
                opened |= set(m.detectors)
            width = max(width, len(opened))
            opened.discard(t)
        return width

    def joint(self, syndromes: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Return (log_scale, table) with P(s, l) = exp(log_scale) * table[:, l]."""
        s = np.asarray(syndromes, dtype=np.uint8)
        if s.ndim != 2 or s.shape[1] != self.num_detectors:
            raise ValueError("syndromes must be [shots, num_detectors]")
        shots = len(s)
        # Bit 0 is the logical; bits 1.. are open detectors in `active` order.
        active: list[int] = []
        table = np.zeros((shots, 2))
        table[:, 0] = 1.0
        log_scale = np.zeros(shots)
        for m in self.logical_only:
            table = (1 - m.p) * table + m.p * table[:, [1, 0]]
        for t in range(self.num_detectors):
            for m in self.by_min.get(t, []):
                for d in m.detectors:
                    if d not in active:
                        active.append(d)
                        table = np.concatenate([table, np.zeros_like(table)], axis=1)
                # XOR-shift by the mechanism's bit mask == flipping those tensor axes.
                nbits = len(active) + 1
                view = table.reshape((shots,) + (2,) * nbits)
                bits = ([0] if m.logical else []) + [1 + active.index(d) for d in m.detectors]
                axes = tuple(nbits - b for b in bits)  # flat bit b <-> axis (nbits - b)
                table = ((1 - m.p) * view + m.p * np.flip(view, axis=axes)).reshape(shots, -1)
            if t in active:
                j = 1 + active.index(t)
                n = table.shape[1]
                view = table.reshape(shots, n >> (j + 1), 2, 1 << j)
                table = view[np.arange(shots), :, s[:, t], :].reshape(shots, n >> 1)
                active.remove(t)
            else:
                # Detector touched by no mechanism: P(s_t = 1) = 0.
                table = table * (s[:, t] == 0)[:, None]
            norm = table.sum(axis=1)
            safe = np.where(norm > 0, norm, 1.0)
            table = table / safe[:, None]
            log_scale += np.log(safe)
            log_scale[norm == 0] = -np.inf
        if active or table.shape[1] != 2:
            raise RuntimeError("elimination did not close every detector")
        return log_scale, table

    def decode(self, syndromes: np.ndarray, batch: int = 256) -> tuple[np.ndarray, np.ndarray]:
        """Return (prediction uint8 [shots,1], posterior P(l=1 | s) [shots])."""
        s = np.asarray(syndromes, dtype=np.uint8)
        preds, post = [], []
        for start in range(0, len(s), batch):
            _, table = self.joint(s[start:start + batch])
            p1 = table[:, 1] / table.sum(axis=1)
            preds.append((p1 > 0.5).astype(np.uint8))  # ties (p1 == 0.5) -> 0
            post.append(p1)
        return np.concatenate(preds).reshape(-1, 1), np.concatenate(post)
