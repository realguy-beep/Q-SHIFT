"""Decode an already-exposed evaluation set with the V1.4B reference/candidate decoders.

Reads saved detector/observable arrays (read-only; hash-checked against the run's
status journal); no sampling. Per root writes work/<set>/root_q{qi}_r{rr}.npz with:
  R_true  exact DEM logical-class decoder at the true q (privileged reference)
  R_zero  exact decoder on the burst-free DEM (q=0), a burst-blind reference
  Bmld    exact decoder at the per-root detector-only q-hat (candidate B)
  Asoft   mask marginalization over Boff's cost-consistent options at q-hat (candidate A)
  boff_mask_count  number of bursts in Boff's chosen (min-cost) mask at q-hat
plus posteriors P(l=1|s). Usage: screen_decode.py <set_name> <run_dir> <qi:root,...|all>
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1]))
from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m  # noqa: E402
from outputs.qshift_v1_4b_decoder_optimality.mld import ExactLogicalDecoder  # noqa: E402

QS = (0.0, 0.01, 0.02)
SPEC = m.CodeSpec()
QUBITS = m.burst_qubits(SPEC, "scaled_v1")
EVENTS = m.extract_burst_events(SPEC, QUBITS)


def exact_decoder(q: float) -> ExactLogicalDecoder:
    circuit = m.build_candidate_circuit(SPEC, q, QUBITS)
    return ExactLogicalDecoder(circuit.detector_error_model(decompose_errors=False, approximate_disjoint_errors=True))


def soft_and_mask(five: m.FiveFactorDecoder, x: np.ndarray, q: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Candidate A (log-sum-exp per logical class) and Boff's chosen-mask burst count."""
    pred = np.zeros(len(x), dtype=np.uint8)
    post = np.zeros(len(x))
    count = np.zeros(len(x), dtype=np.uint8)
    if q == 0.0:
        z = np.asarray(five.matching.decode_batch(x, enable_correlations=False)).reshape(-1)
        return z.astype(np.uint8), z.astype(float), count
    lam = math.log((1 - q) / q)
    for i, row in enumerate(x):
        opts = five.options(row)
        scores = np.asarray([-(c + k * lam) for k, _, c, _ in opts])
        preds = np.asarray([p for _, _, _, p in opts])
        best = min(opts, key=lambda o: (o[2] + o[0] * lam, o[0], o[1]))
        count[i] = best[0]
        s0 = np.logaddexp.reduce(scores[preds == 0]) if (preds == 0).any() else -np.inf
        s1 = np.logaddexp.reduce(scores[preds == 1]) if (preds == 1).any() else -np.inf
        post[i] = 1.0 / (1.0 + math.exp(min(700.0, s0 - s1)))
        pred[i] = 1 if s1 > s0 else 0
    return pred, post, count


def main() -> None:
    set_name, run_dir, which = sys.argv[1], Path(sys.argv[2]).resolve(), sys.argv[3]
    status = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
    calls = {c["archive"]: c for c in status["sampler_calls_started"] if c["phase"] == "evaluation"}
    qhat = json.loads((run_dir / "calibration_diagnostics.json").read_text(encoding="utf-8"))["per_root_qhat"]
    roots = ([(qi, r) for qi in range(3) for r in range(24)] if which == "all"
             else [tuple(int(v) for v in item.split(":")) for item in which.split(",")])
    out_dir = ROOT / "work" / set_name
    out_dir.mkdir(parents=True, exist_ok=True)
    base = m.build_matching(m.build_decomposed_dem(m.build_base_circuit(SPEC)))
    five = m.FiveFactorDecoder(base, EVENTS, SPEC.detectors, correlations=False)
    r_zero_dec = exact_decoder(0.0)
    true_decs = {qi: exact_decoder(q) for qi, q in enumerate(QS)}
    for qi, r in roots:
        target = out_dir / f"root_q{qi}_r{r:02d}.npz"
        if target.exists():
            continue
        archive = f"evaluation/eval_q{qi}_r{r:02d}.npz"
        path = run_dir / archive
        if hashlib.sha256(path.read_bytes()).hexdigest() != calls[archive]["archive_sha256"]:
            raise RuntimeError(f"archive hash mismatch: {archive}")
        with np.load(path, allow_pickle=False) as z:
            saved = {k: np.asarray(z[k]) for k in z.files}
        x = saved["detectors"]
        qh = float(qhat[f"q{qi}_r{r:02d}"])
        t0 = time.perf_counter()
        r_true, p_true = true_decs[qi].decode(x)
        r_zero, p_zero = r_zero_dec.decode(x)
        b_mld, p_bmld = (r_zero, p_zero) if qh == 0.0 else exact_decoder(qh).decode(x)
        t1 = time.perf_counter()
        a_soft, p_asoft, mask_count = soft_and_mask(five, x, qh)
        t2 = time.perf_counter()
        if "pred_Boff" not in saved:
            # S2 (V1.2 arrays) predates the cost-consistent arms: recompute them exactly as
            # V1.3 defines them (residual correlations OFF; per-root q-hat; static q=0.01125).
            recomputed = five.decode_rows(x, {"Boff": qh, "BoffStatic": 0.01125})
            saved["pred_Boff"], saved["pred_BoffStatic"] = recomputed["Boff"], recomputed["BoffStatic"]
        np.savez_compressed(target, y=saved["observables"][:, 0],
                            **{k: v[:, 0] for k, v in saved.items() if k.startswith("pred_")},
                            R_true=r_true[:, 0], R_zero=r_zero[:, 0], Bmld=b_mld[:, 0], Asoft=a_soft,
                            post_R_true=p_true, post_R_zero=p_zero, post_Bmld=p_bmld, post_Asoft=p_asoft,
                            boff_mask_count=mask_count, qhat=qh,
                            seconds_exact_three=t1 - t0, seconds_asoft=t2 - t1)
        print(f"{set_name} q{qi} r{r:02d} done exact3={t1 - t0:.1f}s asoft={t2 - t1:.1f}s", flush=True)


if __name__ == "__main__":
    main()
