"""Belief-matching Phase A bench (DESIGN_PLAN_DRAFT.md). No new sampling.

1. d=3 quality: first 1,000 rows of each of the 72 already-exposed V1.5 evaluation archives (the same
   rows V3 used as development data; hashes checked against V1.5's status record), decoded by BM0-BM3
   with their static DEM; compared with the saved V1.5 Astar and exact (Bexact) predictions.
2. Cost: rehearsal-only shots (never evaluation or screen data): the d57 screen rehearsal chunk
   (1,000 d=7 shots, q=0.02) and the d=5 Phase 2 rehearsal archives (3 x 1,000 d=5 shots).
   Timing only; error counts on these rehearsal rows are reported but carry no decision role.
Usage: bench_phase_a.py <V1.5 package dir>   -> PHASE_A_BENCH.json (written once)
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REPO))
import bm  # noqa: E402
from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m  # noqa: E402

OUT = ROOT / "PHASE_A_BENCH.json"
ROWS = 1000


def dem(d: int, q: float):
    spec = m.CodeSpec(distance=d)
    return m.build_decomposed_dem(m.build_candidate_circuit(spec, q, m.burst_qubits(spec, "scaled_v1")))


def decoders(d: int) -> dict:
    return {name: bm.BeliefMatching(dem(d, q), cfg, conv) for name, (cfg, conv, q) in bm.VARIANTS.items()}


def quality_d3(pkg: Path) -> dict:
    status = json.loads((pkg / "results_v1" / "run_records" / "status.json").read_text(encoding="utf-8"))
    calls = {c["archive"]: c for c in status["sampler_calls_started"] if c["phase"] == "evaluation"}
    decs = decoders(3)
    tot = {a: [0, 0, 0] for a in ("Astar", "Bexact", *decs)}
    disc = {n: {"bm_only": 0, "exact_only": 0} for n in decs}
    for qi in range(3):
        for r in range(24):
            rel = f"evaluation/eval_q{qi}_r{r:02d}.npz"
            path = pkg / "pilot_runs" / "attempt_001" / rel
            if hashlib.sha256(path.read_bytes()).hexdigest() != calls[rel]["archive_sha256"]:
                raise RuntimeError(f"archive hash mismatch: {rel}")
            with np.load(path, allow_pickle=False) as z:
                x = np.asarray(z["detectors"][:ROWS], dtype=np.uint8)
                y = np.asarray(z["observables"][:ROWS, 0], dtype=np.uint8)
                saved = {a: np.asarray(z[f"pred_{a}"][:ROWS, 0], dtype=np.uint8) for a in ("Astar", "Bexact")}
            for a, pr in saved.items():
                tot[a][qi] += int((pr != y).sum())
            for n, dec in decs.items():
                err = dec.decode_batch(x) != y
                tot[n][qi] += int(err.sum())
                ex = saved["Bexact"] != y
                disc[n]["bm_only"] += int((err & ~ex).sum())
                disc[n]["exact_only"] += int((ex & ~err).sum())
    gap = {n: None for n in decs}
    a_nz, e_nz = sum(tot["Astar"][1:]), sum(tot["Bexact"][1:])
    for n in decs:
        b_nz = sum(tot[n][1:])
        gap[n] = (a_nz - b_nz) / (a_nz - e_nz) if a_nz != e_nz else None
    return {"rows_per_q": 24 * ROWS, "errors_q0_q001_q002": tot, "discordance_vs_exact_all_q": disc,
            "fraction_of_exact_gain_over_Astar_nonzero": gap,
            "note": "BM uses a static DEM (q_dec per variant); Astar/Bexact are the saved V1.5 predictions (Bexact at per-root q-hat)"}


def cost(path_label: list[tuple[str, int, Path, str]]) -> dict:
    out = {}
    for label, d, path, kind in path_label:
        with np.load(path) as z:
            if kind == "screen":
                n, nd = int(z["n"]), int(z["num_detectors"])
                x = np.unpackbits(z["detectors"], axis=1)[:, :nd]
                y = np.unpackbits(z["observables"])[:n]
            else:
                y = z["observables"]
                x = np.unpackbits(z["detectors"], axis=1)[:, : m.CodeSpec(distance=d).detectors]
        res = {}
        for n, dec in decoders(d).items():
            t = time.perf_counter()
            pred = dec.decode_batch(x)
            res[n] = {"ms_per_shot": 1000 * (time.perf_counter() - t) / len(x), "errors": int((pred != y).sum()),
                      "shots": len(x), **{k: v for k, v in dec.stats.items() if k != "shots"}}
        out[label] = res
    return out


def main() -> None:
    if OUT.exists():
        raise SystemExit("PHASE_A_BENCH.json exists; runs once")
    pkg = Path(sys.argv[1]).resolve()
    t0 = time.perf_counter()
    q3 = quality_d3(pkg)
    d57 = REPO / "outputs" / "qshift_scalable_decoder_eval_d57_v1" / "work" / "screen_rehearsal" / "d7_q0.02_c0_shots.npz"
    p2 = REPO / "outputs" / "qshift_scalable_decoder_eval_d5_phase2_v1" / "work" / "rehearsal" / "archives"
    c = cost([("d7_rehearsal_q0.02", 7, d57, "screen")] + [(f"d5_rehearsal_q{qi}", 5, p2 / f"q{qi}_r00.npz", "p2")
                                                          for qi in range(3)])
    out = {"schema": "qshift-bm-phase-a-bench-v1", "quality_d3": q3, "cost_rehearsal_rows": c,
           "gate_d7_ms_per_shot_max": 50.0,
           "gate_passes": all(v["ms_per_shot"] <= 50.0 for v in c["d7_rehearsal_q0.02"].values()),
           "wall_seconds": time.perf_counter() - t0,
           "label": "DEVELOPMENT ONLY: d=3 rows are already-exposed V1.5 data; cost rows are rehearsal shots"}
    OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
