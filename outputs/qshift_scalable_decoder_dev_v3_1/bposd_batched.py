"""V3.1: batched BP for the V3 BP+OSD decoder (implementation-only revision).

Same algorithm and settings as V3 `BeliefPropagation`: sum-product in the LLR domain,
synchronous flooding, damping 0.5 on check->variable messages, clip 1e-12, at most 50
iterations, and per-shot early stopping when that shot's max message change < 1e-8 (a
converged shot's messages are frozen exactly as V3 freezes them by returning). Messages
for a batch are [batch, edges] arrays; check and variable sums use sparse incidence
products instead of per-shot bincount. OSD-CS, costs and variants are V3's, imported
unchanged. See PROTOCOL.md.
"""
from __future__ import annotations

import math
import time

import numpy as np
import scipy.sparse as sp

from outputs.qshift_scalable_decoder_dev_v3.bposd import (
    DemMatrix, ImpossibleSyndromeError, OrderedStatisticsDecoder, dem_to_matrix)

__all__ = ["BatchedBP", "BatchedBPOSD", "ImpossibleSyndromeError"]


class BatchedBP:
    def __init__(self, dm: DemMatrix, iterations: int = 50, damping: float = 0.5,
                 tolerance: float = 1e-8, clip: float = 1e-12):
        self.dm = dm
        self.iterations, self.damping, self.tolerance, self.clip = iterations, damping, tolerance, clip
        checks, variables = np.nonzero(dm.H)
        order = np.lexsort((checks, variables))      # identical edge ordering to V3
        self.ec = checks[order].astype(np.int64)
        self.ev = variables[order].astype(np.int64)
        self.m, self.n = dm.H.shape
        e = len(self.ec)
        ones = np.ones(e)
        self.to_check = sp.csr_matrix((ones, (np.arange(e), self.ec)), shape=(e, self.m))
        self.to_var = sp.csr_matrix((ones, (np.arange(e), self.ev)), shape=(e, self.n))
        self.prior = np.log1p(-dm.p) - np.log(dm.p)

    def _sum(self, values: np.ndarray, incidence) -> np.ndarray:
        """[B, E] -> [B, groups] sums over edges in each group."""
        return np.asarray(incidence.T @ values.T).T

    def posterior_llr(self, syndromes: np.ndarray) -> tuple[np.ndarray, dict]:
        s = np.asarray(syndromes, dtype=np.uint8) ^ self.dm.offset_detectors[None, :]
        batch = s.shape[0]
        sign_s = np.where(s[:, self.ec] == 1, -1.0, 1.0)
        v2c = np.tile(self.prior[self.ev], (batch, 1))
        c2v = np.zeros_like(v2c)
        active = np.ones(batch, dtype=bool)
        iterations = np.zeros(batch, dtype=np.int64)
        residual = np.full(batch, math.inf)
        for it in range(1, self.iterations + 1):
            idx = np.nonzero(active)[0]
            if len(idx) == 0:
                break
            v, c, sg = v2c[idx], c2v[idx], sign_s[idx]
            t = np.tanh(v / 2)
            mag = np.abs(t)
            zero = mag == 0
            logmag = np.log(np.where(zero, 1.0, mag))
            neg = (t < 0).astype(np.float64)
            tot_log = self._sum(logmag, self.to_check)[:, self.ec]
            tot_neg = np.rint(self._sum(neg, self.to_check)).astype(np.int64)[:, self.ec]
            tot_zero = np.rint(self._sum(zero.astype(np.float64), self.to_check)).astype(np.int64)[:, self.ec]
            other_zero = tot_zero - zero
            prod_mag = np.where(other_zero > 0, 0.0, np.exp(tot_log - logmag))
            parity = (tot_neg - neg.astype(np.int64)) % 2
            prod = sg * np.where(parity == 1, -1.0, 1.0) * prod_mag
            raw = 2 * np.arctanh(np.clip(prod, -1 + self.clip, 1 - self.clip))
            updated = self.damping * c + (1 - self.damping) * raw
            sums = self._sum(updated, self.to_var)[:, self.ev]
            res = np.max(np.abs(updated - c), axis=1) if updated.shape[1] else np.zeros(len(idx))
            c2v[idx] = updated
            v2c[idx] = self.prior[self.ev][None, :] + sums - updated
            residual[idx] = res
            iterations[idx] = it
            active[idx[res < self.tolerance]] = False
        llr = self.prior[None, :] + self._sum(c2v, self.to_var)
        return llr, {"converged": ~active, "iterations": iterations, "residual": residual}


class BatchedBPOSD:
    def __init__(self, dem, *, merge: bool = True, order: int = 10, weight1_columns: int = 60,
                 iterations: int = 50, damping: float = 0.5, tolerance: float = 1e-8):
        self.dm = dem_to_matrix(dem, merge=merge)
        self.bp = BatchedBP(self.dm, iterations, damping, tolerance)
        self.osd = OrderedStatisticsDecoder(self.dm, order, weight1_columns)
        self.L = self.dm.L.astype(np.int64)
        self.Ht = self.dm.H.T.astype(np.int64)

    def decode_batch(self, x: np.ndarray, variant: str = "min", timing: bool = False):
        if variant not in ("min", "lc"):
            raise ValueError("variant must be 'min' or 'lc'")
        x = np.asarray(x, dtype=np.uint8)
        t0 = time.perf_counter()
        llr, info = self.bp.posterior_llr(x)
        bp_seconds = time.perf_counter() - t0
        hard = (llr < 0).astype(np.int64)
        eff = x ^ self.dm.offset_detectors[None, :]
        bp_ok = np.all(((hard @ self.Ht) % 2) == eff, axis=1)
        hard_logical = ((hard @ self.L) % 2) ^ self.dm.offset_logical
        pred = np.empty(len(x), dtype=np.uint8)
        osd_seconds = np.zeros(len(x))
        used = np.zeros(len(x), dtype=bool)
        weight = self.osd.weight
        for i in range(len(x)):
            if variant == "min" and bp_ok[i]:
                pred[i] = hard_logical[i]
                continue
            t = time.perf_counter()
            vecs, costs, logical = self.osd.candidates(x[i], np.argsort(llr[i], kind="stable"))
            if variant == "min":
                pred[i] = logical[int(np.argmin(costs))]
            else:
                if bp_ok[i] and not any(np.array_equal(v, hard[i].astype(np.uint8)) for v in vecs):
                    costs = np.append(costs, float(hard[i].astype(np.float64) @ weight))
                    logical = np.append(logical, hard_logical[i])
                w = np.exp(-(costs - costs.min()))
                pred[i] = int(float(w[logical == 1].sum()) > float(w[logical == 0].sum()))
            osd_seconds[i] = time.perf_counter() - t
            used[i] = True
        out = pred.reshape(-1, 1)
        if not timing:
            return out
        per_shot = bp_seconds / len(x) + osd_seconds
        return out, {"llr": llr, "bp": info, "bp_seconds": bp_seconds, "per_shot_seconds": per_shot, "used_osd": used}
