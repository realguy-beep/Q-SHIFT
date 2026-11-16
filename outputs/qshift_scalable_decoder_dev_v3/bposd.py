"""V3: pure-NumPy BP+OSD on a full Stim detector error model (hypergraph-preserving).

DEM -> parity-check matrix H (detectors x mechanisms), logical vector L, priors p.
Every independent DEM mechanism is one column carrying its full detector signature and
logical bit, so hyperedges and correlated burst mechanisms are never split. Identical
(detectors, logical) mechanisms may be merged exactly (XOR of independent Bernoullis);
same-detector / different-logical columns are kept (degeneracy stays visible).

BP:  sum-product, LLR domain, synchronous flooding, damping on check->variable messages,
     early stop when the max message change < tolerance (settings match scalable V2).
OSD: columns ranked by BP posterior fault probability; GF(2) Gaussian elimination on
     bit-packed rows; OSD-0 plus OSD-CS (weight-1 flips over the first `w1` non-pivot
     columns, weight-2 flips within the first `order`). Candidate cost is the PRIOR
     weight sum_{e_j=1} log((1-p_j)/p_j) (joint most-probable-fault objective).
     Prediction = exact parity L.e of the chosen vector. Variant "lc" sums exp(-cost)
     over the candidate set per logical class (local degeneracy approximation).
See PROTOCOL.md.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


class ImpossibleSyndromeError(ValueError):
    pass


@dataclass
class DemMatrix:
    H: np.ndarray            # uint8 [num_detectors, n]
    L: np.ndarray            # uint8 [n]
    p: np.ndarray            # float64 [n], 0 < p < 1
    offset_detectors: np.ndarray  # uint8 [num_detectors], from p == 1 mechanisms
    offset_logical: int

    @property
    def num_detectors(self) -> int:
        return self.H.shape[0]


def dem_to_matrix(dem, merge: bool = True) -> DemMatrix:
    if dem.num_observables != 1:
        raise ValueError("exactly one logical observable required")
    nd = int(dem.num_detectors)
    cols: list[tuple[tuple[int, ...], int]] = []
    probs: list[float] = []
    index: dict[tuple[tuple[int, ...], int], int] = {}
    off_det = np.zeros(nd, dtype=np.uint8)
    off_log = 0
    for ins in dem.flattened():
        if ins.type != "error":
            if ins.type not in ("detector", "logical_observable"):
                raise ValueError(f"unsupported DEM instruction: {ins.type}")
            continue
        args = ins.args_copy()
        if len(args) != 1:
            raise ValueError("error instruction must have exactly one probability")
        prob = float(args[0])
        if not math.isfinite(prob) or not 0 <= prob <= 1:
            raise ValueError("mechanism probability must be in [0, 1]")
        dets: set[int] = set()
        logical = 0
        for t in ins.targets_copy():
            if t.is_separator():
                continue  # decomposition hint only: one mechanism
            if t.is_relative_detector_id():
                if not 0 <= t.val < nd:
                    raise ValueError("detector target outside DEM dimensions")
                dets ^= {int(t.val)}
            elif t.is_logical_observable_id():
                if t.val != 0:
                    raise ValueError("unsupported observable id")
                logical ^= 1
            else:
                raise ValueError("unsupported DEM target")
        if prob == 0:
            continue
        if prob == 1:
            for d in dets:
                off_det[d] ^= 1
            off_log ^= logical
            continue
        if not dets and not logical:
            continue
        key = (tuple(sorted(dets)), logical)
        if merge and key in index:
            j = index[key]
            q = probs[j]
            probs[j] = q * (1 - prob) + prob * (1 - q)
            continue
        index[key] = len(cols)
        cols.append(key)
        probs.append(prob)
    n = len(cols)
    H = np.zeros((nd, n), dtype=np.uint8)
    L = np.zeros(n, dtype=np.uint8)
    for j, (dets, logical) in enumerate(cols):
        H[list(dets), j] = 1
        L[j] = logical
    return DemMatrix(H, L, np.asarray(probs, dtype=np.float64), off_det, int(off_log))


class BeliefPropagation:
    """Vectorized sum-product BP over H (mirrors scalable V2's update rules)."""

    def __init__(self, dm: DemMatrix, iterations: int = 50, damping: float = 0.5,
                 tolerance: float = 1e-8, clip: float = 1e-12):
        self.dm = dm
        self.iterations, self.damping, self.tolerance, self.clip = iterations, damping, tolerance, clip
        checks, variables = np.nonzero(dm.H)
        order = np.lexsort((checks, variables))      # edges grouped by variable, then check
        self.ec = checks[order].astype(np.int64)     # edge -> check
        self.ev = variables[order].astype(np.int64)  # edge -> variable
        self.n = dm.H.shape[1]
        self.m = dm.H.shape[0]
        self.prior = np.log1p(-dm.p) - np.log(dm.p)

    def posterior_llr(self, syndrome: np.ndarray) -> tuple[np.ndarray, dict]:
        s = np.asarray(syndrome, dtype=np.uint8) ^ self.dm.offset_detectors
        sign_s = np.where(s[self.ec] == 1, -1.0, 1.0)
        v2c = self.prior[self.ev].copy()
        c2v = np.zeros_like(v2c)
        residual, converged, performed = math.inf, False, 0
        for it in range(1, self.iterations + 1):
            t = np.tanh(v2c / 2)
            mag = np.abs(t)
            zero = mag == 0
            logmag = np.log(np.where(zero, 1.0, mag))
            neg = (t < 0).astype(np.int64)
            tot_log = np.bincount(self.ec, weights=logmag, minlength=self.m)
            tot_neg = np.bincount(self.ec, weights=neg, minlength=self.m).astype(np.int64)
            tot_zero = np.bincount(self.ec, weights=zero.astype(np.int64), minlength=self.m).astype(np.int64)
            other_zero = tot_zero[self.ec] - zero
            prod_mag = np.where(other_zero > 0, 0.0, np.exp(tot_log[self.ec] - logmag))
            parity = (tot_neg[self.ec] - neg) % 2
            prod = sign_s * np.where(parity == 1, -1.0, 1.0) * prod_mag
            raw = 2 * np.arctanh(np.clip(prod, -1 + self.clip, 1 - self.clip))
            updated = self.damping * c2v + (1 - self.damping) * raw
            sums = np.bincount(self.ev, weights=updated, minlength=self.n)
            v2c = self.prior[self.ev] + sums[self.ev] - updated
            residual = float(np.max(np.abs(updated - c2v))) if len(updated) else 0.0
            c2v = updated
            performed = it
            if residual < self.tolerance:
                converged = True
                break
        llr = self.prior + np.bincount(self.ev, weights=c2v, minlength=self.n)
        return llr, {"converged": converged, "iterations": performed, "residual": residual}


def _pack(rows: np.ndarray) -> np.ndarray:
    """Pack a [m, n] uint8 bit matrix into [m, ceil(n/64)] uint64 words (little bit order)."""
    m, n = rows.shape
    pad = (-n) % 64
    packed = np.packbits(np.pad(rows, ((0, 0), (0, pad))), axis=1, bitorder="little")
    return np.ascontiguousarray(packed).view(np.uint64).copy()


def _bit(words: np.ndarray, col: int) -> np.ndarray:
    return ((words[:, col >> 6] >> np.uint64(col & 63)) & np.uint64(1)).astype(np.uint8)


class OrderedStatisticsDecoder:
    def __init__(self, dm: DemMatrix, order: int = 10, weight1_columns: int = 60, exhaustive: bool = False):
        self.dm = dm
        self.order, self.w1 = order, weight1_columns
        self.exhaustive = exhaustive  # tests only: enumerate every subset of non-pivot columns
        self.weight = np.log1p(-dm.p) - np.log(dm.p)

    def candidates(self, syndrome: np.ndarray, ranking: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return (fault vectors [k, n] uint8, costs [k], logical bits [k]) for OSD-0 and OSD-CS."""
        dm = self.dm
        s = np.asarray(syndrome, dtype=np.uint8) ^ dm.offset_detectors
        Hp = dm.H[:, ranking]
        aug = np.concatenate([Hp, s[:, None]], axis=1)
        words = _pack(aug)
        m, n = Hp.shape
        pivot_rows: list[int] = []
        pivot_cols: list[int] = []
        free_rows = np.ones(m, dtype=bool)
        for col in range(n):
            if len(pivot_cols) == m:
                break
            colbits = _bit(words, col).astype(bool)
            cand = np.nonzero(colbits & free_rows)[0]
            if len(cand) == 0:
                continue
            r = int(cand[0])
            others = np.nonzero(colbits)[0]
            others = others[others != r]
            if len(others):
                words[others] ^= words[r]
            free_rows[r] = False
            pivot_rows.append(r)
            pivot_cols.append(col)
        sbits = _bit(words, n)
        if sbits[free_rows].any():
            raise ImpossibleSyndromeError("syndrome is outside the column space of H")
        pr = np.asarray(pivot_rows, dtype=np.int64)
        pc = np.asarray(pivot_cols, dtype=np.int64)
        base = sbits[pr]                                     # pivot values for OSD-0
        pivot_set = np.zeros(n, dtype=bool)
        pivot_set[pc] = True
        nonpivot = np.nonzero(~pivot_set)[0]
        if self.exhaustive:
            if len(nonpivot) > 16:
                raise ValueError("exhaustive OSD is for small test models only")
            from itertools import combinations
            flips = [tuple(int(j) for j in c) for k in range(len(nonpivot) + 1) for c in combinations(nonpivot, k)]
            R = {int(j): _bit(words, int(j))[pr] for j in nonpivot}
        else:
            flips = [()]
            k1 = nonpivot[: self.w1]
            flips += [(int(j),) for j in k1]
            k2 = nonpivot[: self.order]
            flips += [(int(a), int(b)) for i, a in enumerate(k2) for b in k2[i + 1:]]
            R = {int(j): _bit(words, int(j))[pr] for j in set(int(x) for x in nonpivot[: max(self.w1, self.order)])}
        vecs = np.zeros((len(flips), n), dtype=np.uint8)
        for i, T in enumerate(flips):
            piv = base.copy()
            for j in T:
                piv ^= R[j]
                vecs[i, j] = 1
            vecs[i, pc] = piv
        # Map back from ranked order to original column order.
        out = np.zeros_like(vecs)
        out[:, ranking] = vecs
        costs = out.astype(np.float64) @ self.weight
        logical = ((out.astype(np.int64) @ dm.L.astype(np.int64)) % 2 ^ dm.offset_logical).astype(np.uint8)
        return out, costs, logical


class BPOSD:
    def __init__(self, dem, *, merge: bool = True, order: int = 10, weight1_columns: int = 60,
                 iterations: int = 50, damping: float = 0.5, tolerance: float = 1e-8):
        self.dm = dem_to_matrix(dem, merge=merge)
        self.bp = BeliefPropagation(self.dm, iterations, damping, tolerance)
        self.osd = OrderedStatisticsDecoder(self.dm, order, weight1_columns)

    def decode_one(self, syndrome: np.ndarray, variant: str = "min") -> dict:
        if variant not in ("min", "lc"):
            raise ValueError("variant must be 'min' or 'lc'")
        s = np.asarray(syndrome, dtype=np.uint8)
        llr, info = self.bp.posterior_llr(s)
        hard = (llr < 0).astype(np.uint8)
        eff = s ^ self.dm.offset_detectors
        bp_ok = bool(np.array_equal((self.dm.H.astype(np.int64) @ hard) % 2, eff))
        if variant == "min" and bp_ok:
            pred = int((int(hard.astype(np.int64) @ self.dm.L.astype(np.int64)) % 2) ^ self.dm.offset_logical)
            return {"prediction": pred, "used_osd": False, **info}
        ranking = np.argsort(llr, kind="stable")             # most likely faulty first
        vecs, costs, logical = self.osd.candidates(s, ranking)
        if variant == "min":
            pred = int(logical[int(np.argmin(costs))])
        else:
            if bp_ok:
                hc = float(hard.astype(np.float64) @ self.osd.weight)
                hl = int((int(hard.astype(np.int64) @ self.dm.L.astype(np.int64)) % 2) ^ self.dm.offset_logical)
                if not any(np.array_equal(v, hard) for v in vecs):
                    costs = np.append(costs, hc)
                    logical = np.append(logical, hl)
            best = costs.min()
            w = np.exp(-(costs - best))
            p1 = float(w[logical == 1].sum())
            p0 = float(w[logical == 0].sum())
            pred = int(p1 > p0)
        return {"prediction": pred, "used_osd": True, "candidates": int(len(costs)), **info}

    def decode_batch(self, x: np.ndarray, variant: str = "min") -> np.ndarray:
        return np.asarray([self.decode_one(row, variant)["prediction"] for row in np.asarray(x, dtype=np.uint8)],
                          dtype=np.uint8).reshape(-1, 1)
