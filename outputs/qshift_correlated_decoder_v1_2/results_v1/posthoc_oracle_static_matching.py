"""POST-HOC, DESCRIPTIVE ONLY: hindsight-tuned static matching on the V1.2 evaluation data.

Not part of the frozen decision. Picks the static PyMatching q that minimizes
equal-weight LER *on the V1.2 evaluation shots themselves* (oracle, in-sample),
which can only strengthen the baseline, and compares B against it per root.
Touches no B/Bstatic/C parameter. Reads saved arrays only; no sampling.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

PKG = Path(__file__).resolve().parents[1]
REPO = PKG.parents[1]
sys.path.insert(0, str(REPO))
from outputs.qshift_correlated_decoder_feasibility_v1_1.model import (  # noqa: E402
    build_candidate_circuit, build_decomposed_dem, build_matching)

RUN = PKG / "pilot_runs/attempt_001/evaluation"
GRID = [round(0.00125 * k, 5) for k in range(17)]  # 0 .. 0.02 step 0.00125
N, SHOTS = 24, 4000

matchings = {q: build_matching(build_decomposed_dem(build_candidate_circuit(q))) for q in GRID}
err = {q: np.zeros((3, N)) for q in GRID}
b_err = np.zeros((3, N))
for qi in range(3):
    for r in range(N):
        with np.load(RUN / f"eval_q{qi}_r{r:02d}.npz") as z:
            x, y, b = z["detectors"], z["observables"][:, 0], z["pred_B"][:, 0]
        b_err[qi, r] = np.count_nonzero(b != y) / SHOTS
        for q in GRID:
            p = np.asarray(matchings[q].decode_batch(x, enable_correlations=True)).reshape(-1)
            err[q][qi, r] = np.count_nonzero(p != y) / SHOTS
mean_ler = {q: float(err[q].mean()) for q in GRID}
oracle = min(GRID, key=lambda q: (mean_ler[q], q))
diff = b_err - err[oracle]
rng = np.random.default_rng(20261115)
boot = np.mean([diff[qi][rng.integers(0, N, size=(20000, N))].mean(axis=1) for qi in (1, 2)], axis=0)
out = {
    "label": "POST-HOC DESCRIPTIVE; oracle static matching tuned in-sample on V1.2 evaluation data; not a frozen endpoint",
    "grid": GRID,
    "equal_weight_mean_ler_by_static_q": mean_ler,
    "oracle_static_q": oracle,
    "oracle_ler_by_condition": err[oracle].mean(axis=1).tolist(),
    "B_ler_by_condition": b_err.mean(axis=1).tolist(),
    "B_minus_oracle_nonzero_estimate": float(diff[1:].mean(axis=1).mean()),
    "B_minus_oracle_nonzero_95ci_root_bootstrap": np.quantile(boot, [0.025, 0.975]).tolist(),
    "B_minus_oracle_q0_estimate": float(diff[0].mean()),
    "bootstrap_seed_note": "fixed descriptive seed 20261115; not from the frozen inventory",
}
(Path(__file__).parent / "posthoc_oracle_static_matching.json").write_text(
    json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({k: out[k] for k in ("oracle_static_q", "oracle_ler_by_condition", "B_ler_by_condition",
                                       "B_minus_oracle_nonzero_estimate", "B_minus_oracle_nonzero_95ci_root_bootstrap",
                                       "B_minus_oracle_q0_estimate")}, indent=1))
