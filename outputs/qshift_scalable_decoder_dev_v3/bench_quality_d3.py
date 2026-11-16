"""Pre-registered V3 d=3 quality benchmark (PROTOCOL.md). No sampling.

Decodes the first 1,000 rows of each of the 72 already-exposed V1.5 evaluation archives
with V3 BP+OSD (variants 'min' and 'lc') at each root's frozen V1.5 q-hat, and stores
per-root errors alongside the saved V1.5 Astar / BoffStatic / Bexact predictions.
Archive hashes are checked against V1.5's committed status record first.
Usage: bench_quality_d3.py <V1.5 package dir> <qi:root,...|all>   -> work/d3/root_*.npz
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1]))
from outputs.qshift_correlated_decoder_feasibility_v1_1.model import build_base_circuit, build_candidate_circuit  # noqa: E402
from outputs.qshift_scalable_decoder_dev_v3.bposd import BPOSD  # noqa: E402

ROWS = 1000
SAVED_ARMS = ("Astar", "BoffStatic", "Bexact")


def main() -> None:
    pkg, which = Path(sys.argv[1]).resolve(), sys.argv[2]
    records = pkg / "results_v1" / "run_records"
    status = json.loads((records / "status.json").read_text(encoding="utf-8"))
    qhat = json.loads((records / "models_frozen.json").read_text(encoding="utf-8"))["root_qhat"]
    calls = {c["archive"]: c for c in status["sampler_calls_started"] if c["phase"] == "evaluation"}
    roots = ([(qi, r) for qi in range(3) for r in range(24)] if which == "all"
             else [tuple(int(v) for v in item.split(":")) for item in which.split(",")])
    out_dir = ROOT / "work" / "d3"
    out_dir.mkdir(parents=True, exist_ok=True)
    for qi, r in roots:
        target = out_dir / f"root_q{qi}_r{r:02d}.npz"
        if target.exists():
            continue
        rel = f"evaluation/eval_q{qi}_r{r:02d}.npz"
        path = pkg / "pilot_runs" / "attempt_001" / rel
        if hashlib.sha256(path.read_bytes()).hexdigest() != calls[rel]["archive_sha256"]:
            raise RuntimeError(f"archive hash mismatch: {rel}")
        with np.load(path, allow_pickle=False) as z:
            x = np.asarray(z["detectors"][:ROWS], dtype=np.uint8)
            y = np.asarray(z["observables"][:ROWS, 0], dtype=np.uint8)
            saved = {a: np.asarray(z[f"pred_{a}"][:ROWS, 0], dtype=np.uint8) for a in SAVED_ARMS}
        q = float(qhat[f"q{qi}_r{r:02d}"])
        circuit = build_base_circuit() if q <= 0 else build_candidate_circuit(q)
        dec = BPOSD(circuit.detector_error_model(decompose_errors=False, approximate_disjoint_errors=True))
        out = {}
        timing = {}
        for variant in ("min", "lc"):
            t = time.perf_counter()
            res = [dec.decode_one(row, variant) for row in x]
            timing[variant] = (time.perf_counter() - t) / len(x)
            out[variant] = np.asarray([o["prediction"] for o in res], dtype=np.uint8)
            if variant == "min":
                used_osd = int(sum(o["used_osd"] for o in res))
                bp_converged = int(sum(o["converged"] for o in res))
        np.savez_compressed(target, y=y, V3_min=out["min"], V3_lc=out["lc"],
                            **{a: saved[a] for a in SAVED_ARMS}, qhat=q,
                            sec_min=timing["min"], sec_lc=timing["lc"], used_osd=used_osd, bp_converged=bp_converged)
        print(f"q{qi} r{r:02d} done min={1000 * timing['min']:.1f}ms lc={1000 * timing['lc']:.1f}ms osd={used_osd}", flush=True)


if __name__ == "__main__":
    main()
