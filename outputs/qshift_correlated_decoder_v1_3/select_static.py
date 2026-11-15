"""Select the V1.3 baselines on the V1.2 evaluation arrays (sampler-free).

Selection set: V1.2 pilot_runs/attempt_001, 72 archives x 4,000 = 288,000 shots,
already-exposed development data, hash-verified against the V1.2 status journal
and checked unchanged before/after. Per-root q-hat comes from V1.2's detector-only
calibration record. Selects:
  * Astar     : best static PyMatching over {correlations ON, OFF} x q grid
  * AstarAlt  : best static PyMatching in the other mode
  * A2sw tau  : switch threshold for mode-switching adaptive matching
  * BoffStatic: static prior for the cost-consistent five-factor decoder
Criterion everywhere: minimum total errors (equal shots per condition, so equal-weight
mean LER); ties to the smaller q / tau, and ON before OFF.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from outputs.qshift_correlated_decoder_feasibility_v1_1.model import (  # noqa: E402
    build_base_circuit, build_candidate_circuit, build_decomposed_dem, build_matching, extract_burst_events)
from outputs.qshift_correlated_decoder_v1_3 import contract as K  # noqa: E402
from outputs.qshift_correlated_decoder_v1_3.common import atomic_json, load_json, sha256_file  # noqa: E402
from outputs.qshift_correlated_decoder_v1_3.multi_prior import ModeAwareFiveFactor  # noqa: E402

OUT_PATH = ROOT / "STATIC_SELECTION.json"
Q_GRID = [round(0.00125 * k, 5) for k in range(17)]
TAU_GRID = [0.0, 0.0005, 0.001, 0.002, 0.003, 0.004, 0.005, 0.0075, 0.01]
V12_ROOTS, V12_SHOTS = 24, 4000


def select_min(errors: dict, order_key=lambda k: k):
    return min(errors, key=lambda k: (errors[k], order_key(k)))


def load_v12(run_dir: Path):
    status = load_json(run_dir / "status.json")
    if status.get("state") != "completed":
        raise ValueError("V1.2 selection run is not completed")
    calls = {c["key"]: c for c in status["sampler_calls_started"] if c["phase"] == "evaluation"}
    qhat = load_json(run_dir / "calibration_diagnostics.json")["per_root_qhat"]
    data = {}
    for qi, q in enumerate(K.QS):
        for r in range(V12_ROOTS):
            call = calls[K.eval_key(q, r)]
            path = run_dir / call["archive"]
            if call["state"] != "committed" or sha256_file(path) != call["archive_sha256"]:
                raise ValueError(f"V1.2 archive identity mismatch: {path.name}")
            with np.load(path, allow_pickle=False) as z:
                x = np.asarray(z["detectors"], dtype=np.uint8)
                y = np.asarray(z["observables"], dtype=np.uint8)[:, 0]
                a2 = np.asarray(z["pred_A2"], dtype=np.uint8)[:, 0]
            if x.shape != (V12_SHOTS, 40):
                raise ValueError(f"V1.2 archive shape mismatch: {path.name}")
            data[(qi, r)] = (x, y, a2, float(qhat[K.root_id(qi, r)]), call["archive_sha256"])
    return data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v1-2-run", type=Path, required=True, help="V1.2 pilot_runs/attempt_001 (read-only)")
    args = parser.parse_args()
    run_dir = args.v1_2_run.resolve()
    if OUT_PATH.exists():
        raise FileExistsError("STATIC_SELECTION.json exists; selection runs once and is never overwritten")
    before = {p.relative_to(run_dir).as_posix(): sha256_file(p) for p in sorted(run_dir.rglob("*")) if p.is_file()}
    data = load_v12(run_dir)
    started = time.perf_counter()

    # Static matching over mode x q.
    matchings = {q: build_matching(build_decomposed_dem(build_candidate_circuit(q))) for q in Q_GRID}
    static = {(mode, q): [0, 0, 0] for mode in (True, False) for q in Q_GRID}
    for (qi, _), (x, y, _, _, _) in data.items():
        for q in Q_GRID:
            for mode in (True, False):
                p = np.asarray(matchings[q].decode_batch(x, enable_correlations=mode)).reshape(-1)
                static[(mode, q)][qi] += int(np.count_nonzero(p != y))
    totals = {k: sum(v) for k, v in static.items()}
    astar = select_min(totals, lambda k: (k[1], not k[0]))
    alt = select_min({k: v for k, v in totals.items() if k[0] != astar[0]}, lambda k: k[1])

    # Mode-switching adaptive matching threshold.
    base = build_matching(build_decomposed_dem(build_base_circuit()))
    a2_check = 0
    sw = {tau: [0, 0, 0] for tau in TAU_GRID}
    for (qi, _), (x, y, a2_saved, qh, _) in data.items():
        on = np.asarray(build_matching(build_decomposed_dem(build_candidate_circuit(qh))).decode_batch(
            x, enable_correlations=True)).reshape(-1)
        a2_check += int(np.count_nonzero(on != a2_saved))
        off = np.asarray(base.decode_batch(x, enable_correlations=False)).reshape(-1)
        for tau in TAU_GRID:
            pred = off if qh < tau else on
            sw[tau][qi] += int(np.count_nonzero(pred != y))
    if a2_check:
        raise RuntimeError("recomputed ON-at-q-hat predictions differ from saved V1.2 A2 predictions")
    tau = select_min({t: sum(v) for t, v in sw.items()})

    # Cost-consistent five-factor static prior.
    five = ModeAwareFiveFactor(base, extract_burst_events(), correlations=False)
    priors = {repr(q): q for q in Q_GRID}
    boff = {q: [0, 0, 0] for q in Q_GRID}
    for (qi, _), (x, y, _, _, _) in data.items():
        d = five.decode_rows(x, priors)
        for q in Q_GRID:
            boff[q][qi] += int(np.count_nonzero(d[repr(q)][:, 0] != y))
    boff_q = select_min({q: sum(v) for q, v in boff.items()})
    seconds = time.perf_counter() - started

    after = {p.relative_to(run_dir).as_posix(): sha256_file(p) for p in sorted(run_dir.rglob("*")) if p.is_file()}
    if before != after:
        raise RuntimeError("V1.2 selection run changed during selection")
    record = {
        "schema": "qshift-correlated-decoder-v1.3-selection-v1",
        "selection_set": {"source": "V1.2 pilot_runs/attempt_001 (read-only; already-exposed development data)",
                          "shots": len(data) * V12_SHOTS, "file_count": len(before),
                          "files_unchanged_before_after": True,
                          "archives": {f"eval_q{qi}_r{r:02d}.npz": v[4] for (qi, r), v in sorted(data.items())},
                          "per_root_qhat_source": "V1.2 calibration_diagnostics.json (detector-only)",
                          "recomputed_on_at_qhat_matches_saved_A2": True},
        "criterion": "minimum equal-weight mean LER over q in {0,0.01,0.02}; ties to smaller q/tau, ON before OFF",
        "q_grid": Q_GRID, "tau_grid": TAU_GRID,
        "static_matching": [{"correlations": m, "q": q, "errors_by_condition": static[(m, q)], "total": totals[(m, q)]}
                            for m in (True, False) for q in Q_GRID],
        "a2sw": [{"tau": t, "errors_by_condition": sw[t], "total": sum(sw[t])} for t in TAU_GRID],
        "boff_static": [{"q": q, "errors_by_condition": boff[q], "total": sum(boff[q])} for q in Q_GRID],
        "selected": {K.SEL_ASTAR: {"correlations": astar[0], "q": astar[1]},
                     K.SEL_ASTAR_ALT: {"correlations": alt[0], "q": alt[1]},
                     K.SEL_TAU: tau, K.SEL_BOFFSTATIC_Q: boff_q},
        "decode_seconds": seconds, "sampler_calls": 0, "v1_3_evaluation_data_accessed": False,
    }
    atomic_json(OUT_PATH, record)
    print({"selected": record["selected"], "seconds": round(seconds, 1),
           "Astar_total": totals[astar], "AstarAlt_total": totals[alt], "A2sw_total": sum(sw[tau]),
           "BoffStatic_total": sum(boff[boff_q])})


if __name__ == "__main__":
    main()
