"""One Phase 1 job: (d, q). Pre-registered in PHASE1_PROTOCOL.md.

Samples labeled development shots, then records, per decoder, a bit-packed per-shot error
indicator (work/, git-ignored) and counts/timings (JSON). Decoders: the static PyMatching
grid {ON, OFF} x 9 q_dec (includes A_nominal = OFF at q_dec=0), V3.2 ldpc BP+OSD at the
true q (sizing input), and the five-factor static-prior grid on the first n_ff shots;
V3 NumPy timing at d=5 on the first 2,000 shots. Raw detector arrays are not saved.
Usage: phase1_job.py <d> <q> [--rehearse]
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1]))
from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m  # noqa: E402
from outputs.qshift_scalable_decoder_dev_v3.bposd import BPOSD  # noqa: E402
from outputs.qshift_scalable_decoder_dev_v3_2.ldpc_bposd import LdpcBPOSD  # noqa: E402

SHOTS = {5: 100_000, 7: 200_000}
FF_SHOTS = {5: 25_000, 7: 50_000}
V3_TIMING_SHOTS = 2_000
REHEARSAL_SHOTS = 2_000
Q_DEC = [round(0.0025 * k, 4) for k in range(9)]
FF_PRIORS = [round(0.00125 * k, 5) for k in range(1, 17)]


def run(d: int, q: float, rehearse: bool) -> dict:
    seeds = json.loads((ROOT / "PHASE1_SEEDS.json").read_text(encoding="utf-8"))
    key = f"phase1:d{d}:q{q:.2f}"
    seed = int((seeds["rehearsal_seeds"] if rehearse else seeds["seeds"])[key])
    tag = "rehearsal" if rehearse else "phase1"
    work = ROOT / "work" / tag
    res = ROOT / ("work" if rehearse else "results") / f"{tag}_json"
    work.mkdir(parents=True, exist_ok=True)
    res.mkdir(parents=True, exist_ok=True)
    stem = f"d{d}_q{q:.2f}"
    if (res / f"{stem}.json").exists():
        raise SystemExit(f"{stem} already recorded; refusing to rerun")
    n = REHEARSAL_SHOTS if rehearse else SHOTS[d]
    n_ff = min(n, REHEARSAL_SHOTS if rehearse else FF_SHOTS[d])
    spec = m.CodeSpec(distance=d)
    qubits = m.burst_qubits(spec, "scaled_v1")
    t = time.perf_counter()
    det, obs = m.build_candidate_circuit(spec, q, qubits).compile_detector_sampler(seed=seed).sample(
        shots=n, separate_observables=True)
    det = np.asarray(det, dtype=np.uint8)
    y = np.asarray(obs, dtype=np.uint8)[:, 0]
    sample_s = time.perf_counter() - t
    out = {"d": d, "q": q, "seed": seed, "shots": n, "rehearsal": rehearse, "sampling_seconds": sample_s,
           "matching": {}, "timing_ms_per_shot": {}}
    bits = {}
    # Static matching grid.
    t_all = 0.0
    for qd in Q_DEC:
        mt = m.build_matching(m.build_decomposed_dem(m.build_candidate_circuit(spec, qd, qubits)))
        for corr in (True, False):
            t = time.perf_counter()
            pred = np.asarray(mt.decode_batch(det, enable_correlations=corr)).reshape(-1).astype(np.uint8)
            t_all += time.perf_counter() - t
            err = pred != y
            name = f"match_{'on' if corr else 'off'}_{qd}"
            out["matching"][name] = int(err.sum())
            bits[name] = np.packbits(err)
    out["timing_ms_per_shot"]["matching_one_arm"] = 1000 * t_all / (len(Q_DEC) * 2 * n)
    # V3.2 at the true q (sizing input).
    dem_true = m.build_candidate_circuit(spec, q, qubits).detector_error_model(
        decompose_errors=False, approximate_disjoint_errors=True)
    v32 = LdpcBPOSD(dem_true)
    t = time.perf_counter()
    pred = v32.decode_batch(det)[:, 0]
    out["timing_ms_per_shot"]["V3_2"] = 1000 * (time.perf_counter() - t) / n
    err = pred != y
    out["V3_2_errors"] = int(err.sum())
    bits["V3_2"] = np.packbits(err)
    # Five-factor static-prior grid on the first n_ff shots.
    base = m.build_matching(m.build_decomposed_dem(m.build_base_circuit(spec)))
    ff = m.FiveFactorDecoder(base, m.extract_burst_events(spec, qubits), spec.detectors, correlations=False)
    t = time.perf_counter()
    preds = ff.decode_rows(det[:n_ff], {repr(pq): pq for pq in FF_PRIORS})
    out["timing_ms_per_shot"]["five_factor_grid16"] = 1000 * (time.perf_counter() - t) / n_ff
    out["five_factor_shots"] = n_ff
    out["five_factor"] = {repr(pq): int((preds[repr(pq)][:, 0] != y[:n_ff]).sum()) for pq in FF_PRIORS}
    # V3 NumPy timing (d=5 only).
    if d == 5:
        k = min(n, V3_TIMING_SHOTS)
        v3 = BPOSD(dem_true)
        t = time.perf_counter()
        p3 = v3.decode_batch(det[:k])[:, 0]
        out["timing_ms_per_shot"]["V3_numpy"] = 1000 * (time.perf_counter() - t) / k
        out["V3_numpy_errors_first_k"] = int((p3 != y[:k]).sum())
        out["V3_numpy_timing_shots"] = k
    np.savez_compressed(work / f"{stem}_errbits.npz", n=n, **bits)
    (res / f"{stem}.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
    return out


if __name__ == "__main__":
    d, q = int(sys.argv[1]), float(sys.argv[2])
    r = run(d, q, "--rehearse" in sys.argv[3:])
    print(json.dumps({k: r[k] for k in ("d", "q", "shots", "V3_2_errors", "timing_ms_per_shot")}), flush=True)
