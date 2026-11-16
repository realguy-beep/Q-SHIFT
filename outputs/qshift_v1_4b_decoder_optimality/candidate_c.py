"""Candidate C: five-factor enumeration with correlated-consistent residual cost.

Specified in WORKLOG.md (item 9) before any C screen statistic. For each of the
2^rounds burst masks, the residual is decoded once with
Matching.decode(residual, return_weight=True, enable_correlations=True); that
correlation-reweighted solution weight is the background cost and its prediction
the background logical. Mask choice: min(cost + |mask| * log((1-q)/q)), ties by
fewer bursts then lower mask (as Boff). q=0 uses the same correlated decode.

Usage: candidate_c.py <set_name> <run_dir> <qi:root,...|all>  -> work/<set>_C/root_*.npz
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1]))
from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m  # noqa: E402

SPEC = m.CodeSpec()
EVENTS = m.extract_burst_events(SPEC, m.burst_qubits(SPEC, "scaled_v1"))


class CorrelatedConsistentFiveFactor:
    def __init__(self, matching, events):
        self.matching = matching
        self.events = events

    def decode_rows(self, x: np.ndarray, q: float) -> np.ndarray:
        out = np.empty(len(x), dtype=np.uint8)
        if q == 0.0:
            for i, row in enumerate(x):
                out[i] = int(np.asarray(self.matching.decode(row, enable_correlations=True)).reshape(-1)[0])
            return out
        lam = math.log((1 - q) / q)
        for i, row in enumerate(x):
            best = None
            for mask in range(1 << len(self.events)):
                residual = np.asarray(row, dtype=np.uint8).copy()
                logical = count = 0
                for j, event in enumerate(self.events):
                    if (mask >> j) & 1:
                        residual[list(event.detector_ids)] ^= 1
                        logical ^= event.observable_flip
                        count += 1
                pred, weight = self.matching.decode(residual, return_weight=True, enable_correlations=True)
                cand = (float(weight) + count * lam, count, mask, int(np.asarray(pred).reshape(-1)[0]) ^ logical)
                if best is None or cand < best:
                    best = cand
            out[i] = best[3]
        return out


def main() -> None:
    set_name, run_dir, which = sys.argv[1], Path(sys.argv[2]).resolve(), sys.argv[3]
    qhat = json.loads((run_dir / "calibration_diagnostics.json").read_text(encoding="utf-8"))["per_root_qhat"]
    roots = ([(qi, r) for qi in range(3) for r in range(24)] if which == "all"
             else [tuple(int(v) for v in item.split(":")) for item in which.split(",")])
    out_dir = ROOT / "work" / f"{set_name}_C"
    out_dir.mkdir(parents=True, exist_ok=True)
    dec = CorrelatedConsistentFiveFactor(m.build_matching(m.build_decomposed_dem(m.build_base_circuit(SPEC))), EVENTS)
    for qi, r in roots:
        target = out_dir / f"root_q{qi}_r{r:02d}.npz"
        if target.exists():
            continue
        with np.load(ROOT / "work" / set_name / f"root_q{qi}_r{r:02d}.npz") as z:
            y = z["y"]
        with np.load(run_dir / "evaluation" / f"eval_q{qi}_r{r:02d}.npz", allow_pickle=False) as z:
            x = np.asarray(z["detectors"])
            if not np.array_equal(z["observables"][:, 0], y):
                raise RuntimeError("label mismatch with screen file")
        t = time.perf_counter()
        pred = dec.decode_rows(x, float(qhat[f"q{qi}_r{r:02d}"]))
        np.savez_compressed(target, C=pred, seconds=time.perf_counter() - t)
        print(f"{set_name}_C q{qi} r{r:02d} done {time.perf_counter() - t:.1f}s", flush=True)


if __name__ == "__main__":
    main()
