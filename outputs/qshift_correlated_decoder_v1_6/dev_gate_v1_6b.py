"""V1.6b device-level development gate (pre-registered in PREREGISTRATION_DEV_V1_6B.md).

No sampling. Reads already-exposed V1.2/V1.3/V1.5 evaluation archives (detectors and,
for the flip stage only, labels) and per-root calibration archives (descriptive q-hat).
Writes DEV_GATE_V1_6B.json once. Usage: dev_gate_v1_6b.py <worktrees_parent_dir>
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import chi2

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1]))
from outputs.qshift_correlated_decoder_v1_6 import learner as L  # noqa: E402

OUT = ROOT / "DEV_GATE_V1_6B.json"
QS = (0.0, 0.01, 0.02)
STUDIES = ("qshift-correlated-decoder-v1_2/outputs/qshift_correlated_decoder_v1_2",
           "qshift-correlated-decoder-v1_3/outputs/qshift_correlated_decoder_v1_3",
           "qshift-correlated-decoder-v1_5/outputs/qshift_correlated_decoder_v1_5")
THRESHOLD = float(chi2.ppf(1 - 0.01 / 15, df=1))
KNOWN = (8, 12, 15)
BLOCKS, BLOCK = 24, 4000          # per q: 24 x 4,000 = 96,000
LABEL_PER_Q = 500
CURVE_N = (1500, 3000, 6000, 12000, 24000)


def load_study(run: Path):
    det, lab = {}, {}
    for qi in range(3):
        xs, ys = [], []
        for r in range(24):
            with np.load(run / "evaluation" / f"eval_q{qi}_r{r:02d}.npz", allow_pickle=False) as z:
                xs.append(np.asarray(z["detectors"], dtype=np.uint8))
                ys.append(np.asarray(z["observables"][:, 0], dtype=np.uint8))
        det[qi], lab[qi] = np.vstack(xs), np.concatenate(ys)
    return det, lab


def main() -> None:
    parent = Path(sys.argv[1]).resolve()
    if OUT.exists():
        raise SystemExit("DEV_GATE_V1_6B.json exists; the gate runs once")
    classes = L.signature_classes()
    true_idx = next(i for i, c in enumerate(classes) if KNOWN in c.supports_flip0)
    learner = L.ParityLearner(classes, L.base_dem(), THRESHOLD)
    started = time.perf_counter()
    g1, g2, g3, curve, perroot = [], [], [], {n: [] for n in CURVE_N}, []
    for si, rel in enumerate(STUDIES):
        run = parent / rel / "pilot_runs" / "attempt_001"
        det, lab = load_study(run)
        perm = {qi: np.random.default_rng(20261116 + si * 10 + qi).permutation(len(det[qi])) for qi in range(3)}
        det = {qi: det[qi][perm[qi]] for qi in range(3)}
        lab = {qi: lab[qi][perm[qi]] for qi in range(3)}
        block = lambda arr, qi, k, n=BLOCK: arr[qi][k * BLOCK:k * BLOCK + n]  # noqa: E731
        for k in range(BLOCKS):
            x = np.vstack([block(det, qi, k) for qi in range(3)])
            out = learner.select(x)
            rec = {"study": si, "k": k, "class_index": out["class_index"], "q_hat": out["q_hat"],
                   "delta": out["delta"], "correct": out["class_index"] == true_idx}
            g1.append(rec)
            if rec["correct"]:
                j = (k + 12) % BLOCKS
                xl = np.vstack([block(det, qi, j, LABEL_PER_Q) for qi in range(3)])
                yl = np.concatenate([block(lab, qi, j, LABEL_PER_Q) for qi in range(3)])
                f = L.learn_flip(L.SPEC, classes[true_idx], out["q_hat"], xl, yl)
                g3.append({"study": si, "k": k, "flip": f["flip"], "correct": f["flip"] == 0,
                           "llr_1_minus_0": f["log_likelihood_ratio_1_minus_0"]})
        for k in range(8):
            out = learner.select(det[0][k * 12000:(k + 1) * 12000])
            g2.append({"study": si, "k": k, "class_index": out["class_index"], "delta": out["delta"],
                       "correct": out["class_index"] is None})
        for n in CURVE_N:
            per_q = n // 3
            for k in range(len(det[0]) // per_q):
                x = np.vstack([det[qi][k * per_q:(k + 1) * per_q] for qi in range(3)])
                curve[n].append(learner.select(x)["class_index"] == true_idx)
        for qi, q in enumerate(QS):
            for r in range(24):
                with np.load(run / "calibration" / f"cal_q{qi}_r{r:02d}.npz", allow_pickle=False) as z:
                    qh, _ = learner.fit_class(np.asarray(z["detectors"], dtype=np.uint8), true_idx)
                perroot.append({"study": si, "q": q, "q_hat": qh})
    seconds = time.perf_counter() - started
    a1 = sum(r["correct"] for r in g1) / len(g1)
    a2 = sum(r["correct"] for r in g2) / len(g2)
    a3 = sum(r["correct"] for r in g3) / len(g3) if g3 else 0.0
    result = {
        "schema": "qshift-v1.6b-dev-gate-v1", "threshold_delta": THRESHOLD, "true_class_index": true_idx,
        "G1p_device_class_accuracy": a1, "G1p_n": len(g1), "G1p_pass": a1 >= 0.95,
        "G2p_q0_none_rate": a2, "G2p_n": len(g2), "G2p_pass": a2 >= 0.90,
        "G3p_flip_accuracy": a3, "G3p_n": len(g3), "G3p_pass": a3 >= 0.95,
        "gate": "PASS" if (a1 >= 0.95 and a2 >= 0.90 and a3 >= 0.95) else "FAIL",
        "device_q_hat_mean": float(np.mean([r["q_hat"] for r in g1])),
        "learning_curve_class_accuracy": {str(n): {"accuracy": float(np.mean(v)), "subsamples": len(v)}
                                          for n, v in curve.items()},
        "per_root_q_hat_with_true_class": {str(q): {
            "mean": float(np.mean([r["q_hat"] for r in perroot if r["q"] == q])),
            "mae": float(np.mean([abs(r["q_hat"] - q) for r in perroot if r["q"] == q]))} for q in QS},
        "G1p": g1, "G2p": g2, "G3p": g3, "seconds": seconds,
        "label": "DEVELOPMENT ONLY on already-exposed data; known burst only; hidden burst sealed and unused",
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ("G1p", "G2p", "G3p")}, indent=1))


if __name__ == "__main__":
    main()
