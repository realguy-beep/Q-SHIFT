"""V3.2 pre-registered gates K2 (d=3 quality) and K3 (feasibility). No sampling.

K2: first 1,000 rows of each of the 72 hash-checked V1.5 evaluation archives, DEM at each
root's frozen q-hat; compared with saved V1.5 Astar/BoffStatic/Bexact and stored V3
predictions; same statistics and criteria as V3 (root-paired bootstrap, 20,000, seed 20261116).
K3: the same 200 deterministic syndromes per distance as V3; single-shot decode times;
tracemalloc peak plus process RSS (ldpc allocates in C++). Writes V3_2_GATES.json once.
Usage: bench_v3_2.py <V1.5 package dir>
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
import tracemalloc
from pathlib import Path

import numpy as np
import psutil

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1]))
from outputs.qshift_correlated_decoder_feasibility_v1_1.model import build_base_circuit, build_candidate_circuit  # noqa: E402
from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m  # noqa: E402
from outputs.qshift_scalable_decoder_dev_v3.bench_feasibility import syndromes  # noqa: E402
from outputs.qshift_scalable_decoder_dev_v3.bposd import BPOSD  # noqa: E402
from outputs.qshift_scalable_decoder_dev_v3_2.ldpc_bposd import LdpcBPOSD  # noqa: E402

OUT = ROOT / "V3_2_GATES.json"
V3_WORK = ROOT.parent / "qshift_scalable_decoder_dev_v3" / "work" / "d3"
ROWS, N, BOOT, SEED = 1000, 24, 20000, 20261116


def k2(v15: Path) -> dict:
    records = v15 / "results_v1" / "run_records"
    status = json.loads((records / "status.json").read_text(encoding="utf-8"))
    qhat = json.loads((records / "models_frozen.json").read_text(encoding="utf-8"))["root_qhat"]
    calls = {c["archive"]: c for c in status["sampler_calls_started"] if c["phase"] == "evaluation"}
    arms = ("Astar", "BoffStatic", "Bexact", "V3_min", "V3_2")
    err, agree_v3, agree_ex, secs = {}, [], [], []
    for qi in range(3):
        for r in range(N):
            rel = f"evaluation/eval_q{qi}_r{r:02d}.npz"
            path = v15 / "pilot_runs" / "attempt_001" / rel
            if hashlib.sha256(path.read_bytes()).hexdigest() != calls[rel]["archive_sha256"]:
                raise RuntimeError(f"archive hash mismatch: {rel}")
            with np.load(path, allow_pickle=False) as z:
                x = np.asarray(z["detectors"][:ROWS], dtype=np.uint8)
                y = np.asarray(z["observables"][:ROWS, 0], dtype=np.uint8)
                saved = {a: np.asarray(z[f"pred_{a}"][:ROWS, 0]) for a in ("Astar", "BoffStatic", "Bexact")}
            with np.load(V3_WORK / f"root_q{qi}_r{r:02d}.npz") as z:
                saved["V3_min"] = z["V3_min"]
            q = float(qhat[f"q{qi}_r{r:02d}"])
            circuit = build_base_circuit() if q <= 0 else build_candidate_circuit(q)
            dec = LdpcBPOSD(circuit.detector_error_model(decompose_errors=False, approximate_disjoint_errors=True))
            t = time.perf_counter()
            saved["V3_2"] = dec.decode_batch(x)[:, 0]
            secs.append((time.perf_counter() - t) / len(x))
            for a in arms:
                err[(a, qi, r)] = saved[a] != y
            agree_v3.append(saved["V3_2"] == saved["V3_min"])
            agree_ex.append(saved["V3_2"] == saved["Bexact"])
    rate = {k: float(v.mean()) for k, v in err.items()}
    totals = {a: [int(sum(err[(a, qi, r)].sum() for r in range(N))) for qi in range(3)] for a in arms}
    per_q = ROWS * N
    nz = {a: float(np.mean([totals[a][1] / per_q, totals[a][2] / per_q])) for a in arms}
    q0 = {a: totals[a][0] / per_q for a in arms}
    rng = np.random.default_rng(SEED)
    idx = {qi: rng.integers(0, N, size=(BOOT, N)) for qi in range(3)}

    def paired(x, b):
        d = {qi: np.asarray([rate[(x, qi, r)] - rate[(b, qi, r)] for r in range(N)]) for qi in range(3)}
        boot = np.mean([d[qi][idx[qi]].mean(axis=1) for qi in (1, 2)], axis=0)
        return {"nonzero_estimate": float(np.mean([d[1].mean(), d[2].mean()])),
                "nonzero_95ci": np.quantile(boot, [0.025, 0.975]).tolist(), "q0_estimate": float(d[0].mean())}

    contrasts = {f"V3_2_minus_{b}": paired("V3_2", b) for b in ("Astar", "BoffStatic", "Bexact", "V3_min")}
    gap = (nz["Astar"] - nz["V3_2"]) / (nz["Astar"] - nz["Bexact"])
    beats = contrasts["V3_2_minus_Astar"]["nonzero_95ci"][1] < 0
    q0_ok = (q0["V3_2"] - q0["Astar"]) <= 0.0005
    return {"rows": per_q * 3, "errors_q0_q001_q002": totals, "nonzero_ler": nz, "q0_ler": q0, "contrasts": contrasts,
            "gap_recovery": gap, "agreement_with_V3_min": float(np.mean(np.concatenate(agree_v3))),
            "agreement_with_Bexact": float(np.mean(np.concatenate(agree_ex))),
            "mean_ms_per_shot_real_d3": 1000 * float(np.mean(secs)),
            "pass": beats and gap >= 0.50 and q0_ok, "beats_Astar_ci": beats, "q0_not_worse": q0_ok}


def k3() -> tuple[list, bool]:
    out = []
    proc = psutil.Process()
    for d in (3, 5, 7):
        spec = m.CodeSpec(distance=d)
        qubits = m.burst_qubits(spec, "scaled_v1")
        dem = m.build_candidate_circuit(spec, 0.01, qubits).detector_error_model(
            decompose_errors=False, approximate_disjoint_errors=True)
        x = syndromes(BPOSD(dem), m.extract_burst_events(spec, qubits))
        rss0 = proc.memory_info().rss
        tracemalloc.start()
        t = time.perf_counter()
        dec = LdpcBPOSD(dem)
        build = time.perf_counter() - t
        per, preds = [], []
        for row in x:
            t = time.perf_counter()
            preds.append(dec.decode_one(row))
            per.append(time.perf_counter() - t)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        rss = proc.memory_info().rss
        ref = [BPOSD(dem).decode_one(row)["prediction"] for row in x[:50]]
        per = np.asarray(per)
        out.append({"distance": d, "construction_seconds": build, "median_ms_per_shot": 1000 * float(np.median(per)),
                    "p95_ms_per_shot": 1000 * float(np.quantile(per, 0.95)), "max_ms_per_shot": 1000 * float(per.max()),
                    "peak_traced_memory_mib": peak / 2**20, "rss_mib_after": rss / 2**20,
                    "rss_growth_mib": (rss - rss0) / 2**20, "osd_order_used": dec.osd_order_used,
                    "agreement_with_V3_first50": float(np.mean(np.asarray(preds[:50]) == np.asarray(ref)))})
        print(out[-1], flush=True)
    d7 = next(r for r in out if r["distance"] == 7)
    ok = d7["median_ms_per_shot"] <= 50 and max(r["peak_traced_memory_mib"] for r in out) <= 1024 \
        and max(r["rss_mib_after"] for r in out) <= 1024
    return out, ok


def main() -> None:
    if OUT.exists():
        raise SystemExit("V3_2_GATES.json exists; runs once")
    feas, k3_pass = k3()
    quality = k2(Path(sys.argv[1]).resolve())
    print(json.dumps({k: quality[k] for k in ("errors_q0_q001_q002", "nonzero_ler", "gap_recovery", "agreement_with_V3_min",
                                              "agreement_with_Bexact", "mean_ms_per_shot_real_d3", "pass")}, indent=1))
    for k, v in quality["contrasts"].items():
        print(k, "%+.5f" % v["nonzero_estimate"], [round(c, 5) for c in v["nonzero_95ci"]], "q0 %+.5f" % v["q0_estimate"])
    decision = "GO" if (quality["pass"] and k3_pass) else ("REVISE" if quality["pass"] else "STOP")
    OUT.write_text(json.dumps({"schema": "qshift-scalable-v3-2-gates-v1", "K1": "tests/test_ldpc_bposd.py (2/2 pass)",
                               "K2_quality_d3": quality, "K3_feasibility": feas, "K3_pass": k3_pass, "decision": decision,
                               "label": "DEVELOPMENT ONLY: d=3 quality on already-exposed V1.5 arrays; feasibility on deterministic syndromes"},
                              indent=2) + "\n", encoding="utf-8", newline="\n")
    print("K3 pass", k3_pass, "DECISION", decision)


if __name__ == "__main__":
    main()
