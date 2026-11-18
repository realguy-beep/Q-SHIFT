"""Background-floor diagnostic on Stage S DEVELOPMENT arrays only (BACKGROUND_ERROR_ANALYSIS.md).

Reads `outputs/qshift_d5_lowp_regime_v1/work/dev/` (Stage S, 200k shots per (condition, q), seeds in
DEV_SEEDS.json). It never reads Stage E (`work/eval_v1`) and generates no new Stim samples.

For every shot the Stage-S-selected L2 decoder failed (and a fixed control sample of successes), it asks:
  1. Did BP converge (BP-only estimate satisfies the syndrome)?
  2. Cost (negative log-likelihood ratio, sum_j e_j * log((1-p_j)/p_j)) of L2's estimate, which lies in the
     WRONG logical class.
  3. Cost of the best estimate a constrained BP+OSD (logical row appended, target = observed label) finds in
     the CORRECT class. This is an upper bound on the correct-class minimum.
  If (3) < (2), a more likely correct-class error exists: the failure is SEARCH-LIMITED (certain).
  Otherwise the failure is MLE-CONSISTENT as far as this search can tell (conservative label).
  4. Whether decoder variants (higher OSD order, OSD_E, more BP iterations, min-sum) fix the shot.
Observable labels are used offline only, as a diagnostic; no deployable decoder sees them.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import scipy.sparse as sp
from ldpc import BpOsdDecoder

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
sys.path.insert(0, str(REPO))
from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m  # noqa: E402
from outputs.qshift_scalable_decoder_dev_v3.bposd import dem_to_matrix  # noqa: E402

DEV = REPO / "outputs/qshift_d5_lowp_regime_v1/work/dev"
CONDS = {"L10": 0.001, "L15": 0.0015}            # base p
SELECTED_PRIOR = {"L10": 0.001, "L15": 0.0025}   # Stage S DEV_SELECTION.json
QS = (0.0, 0.01, 0.02)
BASE = {"bp_method": "product_sum", "schedule": "serial", "max_iter": 50, "osd_method": "OSD_CS", "osd_order": 10}
VARIANTS = {
    "L2_baseline": BASE,
    "osd_cs_40": {**BASE, "osd_order": 40},
    "osd_e_8": {**BASE, "osd_method": "OSD_E", "osd_order": 8},
    "bp_iter_500": {**BASE, "max_iter": 500},
    "min_sum_0.9": {**BASE, "bp_method": "minimum_sum", "ms_scaling_factor": 0.9},
}
CONTROL_PER_FILE = 100
CONTROL_SEED = 20261118


def load(cond: str, qi: int):
    with np.load(DEV / f"{cond}_q{qi}_shots.npz") as z:
        det = np.unpackbits(z["detectors"], axis=1)[:, : int(z["num_detectors"])]
        y = z["observables"].astype(np.uint8)
    with np.load(DEV / f"{cond}_q{qi}_l2_{SELECTED_PRIOR[cond]:.4f}_errbits.npz") as z:
        err = np.unpackbits(z["err"])[: len(y)].astype(bool)
    return det, y, err


def build(cond: str, qi: int):
    s = m.CodeSpec(distance=5, gate_p=CONDS[cond], measurement_p=CONDS[cond])
    qubits = m.burst_qubits(s, "scaled_v1")
    dem = m.build_candidate_circuit(s, SELECTED_PRIOR[cond], qubits).detector_error_model(
        decompose_errors=False, approximate_disjoint_errors=True)
    return dem_to_matrix(dem, merge=True)


class Diag:
    def __init__(self, dm):
        self.dm = dm
        self.H = sp.csr_matrix(dm.H)
        self.L = np.asarray(dm.L, dtype=np.int64).reshape(-1)
        self.p = np.asarray(dm.p, dtype=float)
        self.w = np.log((1 - self.p) / self.p)
        self.dec = {k: BpOsdDecoder(self.H, error_channel=list(self.p), **cfg) for k, cfg in VARIANTS.items()}
        Ha = sp.vstack([self.H, sp.csr_matrix(self.L.reshape(1, -1))]).tocsr()
        self.constrained = BpOsdDecoder(Ha, error_channel=list(self.p), **{**BASE, "osd_order": 40})

    def syn(self, det):
        return (np.asarray(det, dtype=np.uint8) ^ self.dm.offset_detectors).astype(np.uint8)

    def obs(self, e):
        return int((int(e.astype(np.int64) @ self.L) % 2) ^ self.dm.offset_logical)

    def cost(self, e):
        return float(self.w[e.astype(bool)].sum())

    def shot(self, det, y):
        s = self.syn(det)
        out = {}
        for k, d in self.dec.items():
            e = np.asarray(d.decode(s), dtype=np.uint8)
            out[k] = {"correct": self.obs(e) == int(y), "cost": self.cost(e), "weight": int(e.sum())}
            if k == "L2_baseline":
                bp = np.asarray(d.bp_decoding, dtype=np.uint8)
                out[k]["bp_converged"] = bool(d.converge)
                out[k]["bp_satisfies_syndrome"] = bool(np.array_equal((self.H @ bp) % 2, s))
        target = np.concatenate([s, [np.uint8(int(y) ^ self.dm.offset_logical)]]).astype(np.uint8)
        ec = np.asarray(self.constrained.decode(target), dtype=np.uint8)
        ok = np.array_equal((self.H @ ec) % 2, s) and self.obs(ec) == int(y)
        out["correct_class"] = {"valid": bool(ok), "cost": self.cost(ec), "weight": int(ec.sum())}
        return out


def main() -> None:
    if "eval_v1" in str(DEV):
        raise SystemExit("refusing: Stage E path")
    rng = np.random.default_rng(CONTROL_SEED)
    rows, t0 = [], time.perf_counter()
    for cond in CONDS:
        for qi in range(3):
            det, y, err = load(cond, qi)
            dg = Diag(build(cond, qi))
            fail = np.flatnonzero(err)
            ok = np.flatnonzero(~err)
            ctrl = np.sort(rng.choice(ok, size=CONTROL_PER_FILE, replace=False))
            for kind, idx in (("failure", fail), ("control", ctrl)):
                for i in idx:
                    r = dg.shot(det[i], y[i])
                    r.update({"cond": cond, "q": QS[qi], "shot": int(i), "kind": kind})
                    rows.append(r)
            print(cond, qi, "failures", len(fail), f"{time.perf_counter() - t0:.0f}s", flush=True)
    fails = [r for r in rows if r["kind"] == "failure"]
    ctrls = [r for r in rows if r["kind"] == "control"]
    reproduced = sum(not r["L2_baseline"]["correct"] for r in fails)
    search_limited = [r for r in fails if r["correct_class"]["valid"]
                      and r["correct_class"]["cost"] < r["L2_baseline"]["cost"] - 1e-9]
    summary = {
        "schema": "qshift-adaptive-robust-floor-diagnostic-v1",
        "data": "Stage S development arrays only (qshift_d5_lowp_regime_v1/work/dev); Stage E not read",
        "selected_prior": SELECTED_PRIOR, "variants": VARIANTS,
        "failures": len(fails), "failures_reproduced_by_baseline": reproduced,
        "controls": len(ctrls),
        "bp_converged_on_failures": sum(r["L2_baseline"]["bp_converged"] for r in fails),
        "bp_converged_on_controls": sum(r["L2_baseline"]["bp_converged"] for r in ctrls),
        "correct_class_found": sum(r["correct_class"]["valid"] for r in fails),
        "search_limited_failures": len(search_limited),
        "mle_consistent_failures": len(fails) - len(search_limited),
        "variant_fixes_on_failures": {k: sum(r[k]["correct"] for r in fails) for k in VARIANTS},
        "variant_breaks_on_controls": {k: sum(not r[k]["correct"] for r in ctrls) for k in VARIANTS},
        "by_condition": {c: {"failures": sum(r["cond"] == c for r in fails),
                             "search_limited": sum(r["cond"] == c for r in search_limited)} for c in CONDS},
        "cost_gap_wrong_minus_correct": sorted(round(r["L2_baseline"]["cost"] - r["correct_class"]["cost"], 3)
                                               for r in fails if r["correct_class"]["valid"]),
        "seconds": round(time.perf_counter() - t0, 1),
    }
    out = ROOT / "results" / "floor_diagnostic"
    out.mkdir(parents=True, exist_ok=True)
    (out / "FLOOR_DIAG.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
    (out / "floor_rows.json").write_text(json.dumps(rows) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
