"""Belief-matching: BP on the hypergraph DEM, then PyMatching on a graph re-weighted by BP posteriors.

Built from ONE decomposed stim DEM (decompose_errors=True), so the hypergraph and the matching graph
are consistent by construction:
  * each error instruction i (probability p_i) is a BP column whose detector support is the XOR of its
    graphlike components, and whose logical bit is the XOR of theirs;
  * each distinct component (1 or 2 detectors) is a matching edge e;
  * edge probability from instruction probabilities r_i (prior or posterior) uses the exact
    independent-merge rule  p_e = (1 - prod_{i ∋ e} (1 - 2 r_i)) / 2,  the same rule PyMatching uses to
    merge parallel edges from a DEM, so with r = prior the graph equals PyMatching's own.
Instructions whose total detector support is empty are dropped from BP (undetectable); a component
with no detectors or more than two detectors is a build error.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pymatching
import scipy.sparse as sp
from ldpc import BpDecoder

CLIP = 1e-12
BP_DEFAULT = {"bp_method": "product_sum", "schedule": "serial", "max_iter": 50}


@dataclass
class BMGraph:
    H: sp.csc_matrix          # [detectors, instructions] hypergraph (BP)
    L: np.ndarray             # [instructions] uint8 logical bit of each instruction
    p: np.ndarray             # [instructions] prior probability
    M: sp.csr_matrix          # [instructions, edges] 1 if instruction contains edge
    He: sp.csc_matrix         # [detectors, edges] matching check matrix (1 or 2 ones per column)
    Le: sp.csc_matrix         # [1, edges] logical bit of each edge
    num_detectors: int


def build_graph(dem_decomposed) -> BMGraph:
    edge_index: dict[tuple[int, ...], int] = {}
    edge_obs: list[int] = []
    cols_h, rows_h, L, p, m_rows, m_cols = [], [], [], [], [], []
    for ins in dem_decomposed.flattened():
        if ins.type != "error":
            continue
        comps: list[list] = [[]]
        for t in ins.targets_copy():
            if t.is_separator():
                comps.append([])
            else:
                comps[-1].append(t)
        support: set[int] = set()
        obs, members = 0, []
        for c in comps:
            ds = tuple(sorted(t.val for t in c if t.is_relative_detector_id()))
            ob = sum(1 for t in c if t.is_logical_observable_id()) % 2
            if not 1 <= len(ds) <= 2:
                raise ValueError(f"non-graphlike component {ds} in {ins}")
            if ds not in edge_index:
                edge_index[ds] = len(edge_obs)
                edge_obs.append(ob)
            elif edge_obs[edge_index[ds]] != ob:
                raise ValueError(f"edge {ds} has conflicting logical bits")
            if edge_index[ds] in members:
                raise ValueError(f"component repeated within one instruction: {ins}")
            members.append(edge_index[ds])
            support ^= set(ds)
            obs ^= ob
        if not support:
            continue
        i = len(p)
        for dt in sorted(support):
            rows_h.append(dt)
            cols_h.append(i)
        L.append(obs)
        p.append(float(ins.args_copy()[0]))
        m_rows += [i] * len(members)
        m_cols += members
    n, ne, nd = len(p), len(edge_obs), dem_decomposed.num_detectors
    H = sp.csc_matrix((np.ones(len(rows_h), np.uint8), (rows_h, cols_h)), shape=(nd, n))
    M = sp.csr_matrix((np.ones(len(m_rows)), (m_rows, m_cols)), shape=(n, ne))
    er, ec = [], []
    for ds, e in edge_index.items():
        er += list(ds)
        ec += [e] * len(ds)
    He = sp.csc_matrix((np.ones(len(er), np.uint8), (er, ec)), shape=(nd, ne))
    Le = sp.csc_matrix(np.asarray(edge_obs, dtype=np.uint8).reshape(1, ne))
    return BMGraph(H, np.asarray(L, np.uint8), np.asarray(p), M, He, Le, nd)


def edge_probabilities(g: BMGraph, r: np.ndarray) -> np.ndarray:
    """Independent-merge rule; handles r > 1/2 (negative factors) exactly via sign parity."""
    f = 1.0 - 2.0 * np.clip(r, CLIP, 1 - CLIP)
    log_abs = g.M.T @ np.log(np.abs(f))
    neg = (g.M.T @ (f < 0).astype(np.float64)).round().astype(np.int64) % 2
    prod = np.exp(log_abs) * np.where(neg == 1, -1.0, 1.0)
    return np.clip((1.0 - prod) / 2.0, CLIP, 1 - CLIP)


def weights(pe: np.ndarray) -> np.ndarray:
    return np.log((1.0 - pe) / pe)


class BeliefMatching:
    def __init__(self, dem_decomposed, bp: dict | None = None, use_converged_bp: bool = False):
        self.g = build_graph(dem_decomposed)
        self.cfg = {**BP_DEFAULT, **(bp or {})}
        self.use_converged_bp = use_converged_bp
        self.bp = BpDecoder(self.g.H, error_channel=list(map(float, self.g.p)), **self.cfg) if self.cfg["max_iter"] > 0 else None
        self.prior_weights = weights(edge_probabilities(self.g, self.g.p))
        self.stats = {"shots": 0, "zero_syndrome": 0, "bp_converged": 0, "bp_shortcut_used": 0}

    def matching(self, w: np.ndarray) -> pymatching.Matching:
        return pymatching.Matching.from_check_matrix(self.g.He, weights=w, faults_matrix=self.g.Le,
                                                     use_virtual_boundary_node=True)

    def decode_one(self, s: np.ndarray) -> int:
        s = np.asarray(s, dtype=np.uint8)
        self.stats["shots"] += 1
        if not s.any():
            self.stats["zero_syndrome"] += 1
            return 0
        if self.bp is None:
            w = self.prior_weights
        else:
            e = self.bp.decode(s)
            if self.bp.converge:
                self.stats["bp_converged"] += 1
                if self.use_converged_bp:
                    self.stats["bp_shortcut_used"] += 1
                    return int(self.g.L @ np.asarray(e, dtype=np.int64) % 2)
            llr = np.asarray(self.bp.log_prob_ratios, dtype=np.float64)
            w = weights(edge_probabilities(self.g, 1.0 / (1.0 + np.exp(np.clip(llr, -700, 700)))))
        return int(np.asarray(self.matching(w).decode(s)).reshape(-1)[0])

    def decode_batch(self, det: np.ndarray) -> np.ndarray:
        return np.asarray([self.decode_one(row) for row in np.asarray(det, dtype=np.uint8)], dtype=np.uint8)


VARIANTS = {
    "BM0": ({"bp_method": "product_sum", "schedule": "parallel", "max_iter": 50}, False, 0.01),
    "BM1": ({"bp_method": "product_sum", "schedule": "serial", "max_iter": 50}, False, 0.01),
    "BM2": ({"bp_method": "product_sum", "schedule": "serial", "max_iter": 50}, True, 0.01),
    "BM3": ({"bp_method": "product_sum", "schedule": "serial", "max_iter": 50}, False, 0.0025),
}
