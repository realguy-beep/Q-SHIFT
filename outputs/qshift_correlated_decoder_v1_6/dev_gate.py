"""V1.6 development gate (pre-registered in PREREGISTRATION_DEV.md). No sampling.

Reads already-exposed V1.2/V1.3/V1.5 calibration archives (detector-only) and the
first 500 labeled shots of V1.2/V1.3 nonzero-q evaluation archives (read-only).
Writes DEV_GATE.json once. Usage: dev_gate.py <worktrees_parent_dir>
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

OUT = ROOT / "DEV_GATE.json"
QS = (0.0, 0.01, 0.02)
STUDIES = {"V1.2": "qshift-correlated-decoder-v1_2/outputs/qshift_correlated_decoder_v1_2",
           "V1.3": "qshift-correlated-decoder-v1_3/outputs/qshift_correlated_decoder_v1_3",
           "V1.5": "qshift-correlated-decoder-v1_5/outputs/qshift_correlated_decoder_v1_5"}
LABEL_STUDIES = ("V1.2", "V1.3")
LABEL_SHOTS = 500
THRESHOLD = float(chi2.ppf(1 - 0.01 / 15, df=1))
KNOWN = (8, 12, 15)


def main() -> None:
    parent = Path(sys.argv[1]).resolve()
    if OUT.exists():
        raise SystemExit("DEV_GATE.json exists; the gate runs once")
    classes = L.signature_classes()
    true_idx = next(i for i, c in enumerate(classes) if KNOWN in c.supports_flip0)
    learner = L.ParityLearner(classes, L.base_dem(), THRESHOLD)
    started = time.perf_counter()
    batches, pooled = [], {}
    for study, rel in STUDIES.items():
        run = parent / rel / "pilot_runs" / "attempt_001"
        rows = []
        for qi, q in enumerate(QS):
            for r in range(24):
                with np.load(run / "calibration" / f"cal_q{qi}_r{r:02d}.npz", allow_pickle=False) as z:
                    if z.files != ["detectors"]:
                        raise RuntimeError("calibration archive is not detector-only")
                    x = np.asarray(z["detectors"], dtype=np.uint8)
                rows.append(x)
                out = learner.select(x)
                batches.append({"study": study, "q": q, "root": r, "class_index": out["class_index"],
                                "q_hat": out["q_hat"], "delta": out["delta"],
                                "correct": (out["class_index"] == true_idx) if q > 0 else (out["class_index"] is None)})
        p = learner.select(np.vstack(rows))
        pooled[study] = {"class_index": p["class_index"], "correct_class": p["class_index"] == true_idx,
                         "q_hat": p["q_hat"], "delta": p["delta"]}
    stage1_seconds = time.perf_counter() - started

    flips = []
    by_key = {(b["study"], b["q"], b["root"]): b for b in batches}
    for study in LABEL_STUDIES:
        run = parent / STUDIES[study] / "pilot_runs" / "attempt_001"
        for qi, q in enumerate(QS[1:], start=1):
            for r in range(24):
                b = by_key[(study, q, r)]
                if b["class_index"] != true_idx:
                    continue
                with np.load(run / "evaluation" / f"eval_q{qi}_r{r:02d}.npz", allow_pickle=False) as z:
                    x = np.asarray(z["detectors"][:LABEL_SHOTS], dtype=np.uint8)
                    y = np.asarray(z["observables"][:LABEL_SHOTS, 0])
                f = L.learn_flip(L.SPEC, classes[true_idx], b["q_hat"], x, y)
                flips.append({"study": study, "q": q, "root": r, "flip": f["flip"],
                              "llr_1_minus_0": f["log_likelihood_ratio_1_minus_0"], "correct": f["flip"] == 0})
    seconds = time.perf_counter() - started

    nonzero = [b for b in batches if b["q"] > 0]
    zero = [b for b in batches if b["q"] == 0]
    g1 = sum(b["correct"] for b in nonzero) / len(nonzero)
    g2 = sum(b["correct"] for b in zero) / len(zero)
    g3 = sum(f["correct"] for f in flips) / len(flips) if flips else 0.0
    qhat = {str(q): {"mean": float(np.mean([b["q_hat"] for b in batches if b["q"] == q])),
                     "mae": float(np.mean([abs(b["q_hat"] - q) for b in batches if b["q"] == q]))} for q in QS}
    result = {
        "schema": "qshift-v1.6-dev-gate-v1", "threshold_delta": THRESHOLD, "true_class_index": true_idx,
        "G1_nonzero_class_accuracy": g1, "G2_q0_none_rate": g2, "G3_flip_accuracy": g3,
        "G1_pass": g1 >= 0.95, "G2_pass": g2 >= 0.90, "G3_pass": g3 >= 0.95,
        "gate": "PASS" if (g1 >= 0.95 and g2 >= 0.90 and g3 >= 0.95) else "FAIL",
        "flip_roots_evaluated": len(flips), "q_hat_by_q": qhat, "pooled_learner": pooled,
        "min_weight_heuristic_flip_for_true_class": classes[true_idx].min_weight_flip(),
        "batches": batches, "flips": flips, "stage1_seconds": stage1_seconds, "total_seconds": seconds,
        "label": "DEVELOPMENT ONLY on already-exposed data; known burst only; hidden burst not used",
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: result[k] for k in ("gate", "G1_nonzero_class_accuracy", "G2_q0_none_rate",
                                             "G3_flip_accuracy", "flip_roots_evaluated", "q_hat_by_q",
                                             "pooled_learner", "threshold_delta", "total_seconds")}, indent=1))


if __name__ == "__main__":
    main()
