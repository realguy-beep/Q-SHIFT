"""Step 0 job: re-decode one saved d=5 screen chunk with L2 at a static q_dec (STEP0_PROTOCOL.md).

Usage: step0_job.py <q_dec> <true_q> <chunk>
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
from outputs.qshift_scalable_decoder_dev_v3_2.ldpc_bposd import LdpcBPOSD  # noqa: E402

L2 = {"bp_method": "product_sum", "schedule": "serial", "max_iter": 50, "osd_method": "OSD_CS", "osd_order": 10}
QDEC = (0.0, 0.0025, 0.005, 0.01, 0.02)


def main() -> None:
    q_dec, q, chunk = float(sys.argv[1]), float(sys.argv[2]), int(sys.argv[3])
    if q_dec not in QDEC:
        raise SystemExit("q_dec not in the pre-registered grid")
    stem = f"d5_q{q:.2f}_c{chunk}"
    out_dir = ROOT / "results" / "step0_json"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{stem}_qdec{q_dec:.4f}.json"
    if out.exists():
        raise SystemExit(f"{out.name} exists; refusing to rerun")
    seeds = json.loads((ROOT / "SCREEN_SEEDS.json").read_text(encoding="utf-8"))["seeds"]
    meta = json.loads((ROOT / "results" / "screen_json" / f"{stem}.json").read_text(encoding="utf-8"))
    if meta["seed"] != seeds[f"screen:d5:q{q:.2f}:chunk{chunk}"] or meta["rehearsal"]:
        raise RuntimeError("seed mismatch")
    with np.load(ROOT / "work" / "screen" / f"{stem}_shots.npz") as z:
        n, nd = int(z["n"]), int(z["num_detectors"])
        det = np.unpackbits(z["detectors"], axis=1)[:, :nd]
        y = np.unpackbits(z["observables"])[:n]
    if n != meta["shots"]:
        raise RuntimeError("shot count mismatch")
    spec = m.CodeSpec(distance=5)
    circ = m.build_candidate_circuit(spec, q_dec, m.burst_qubits(spec, "scaled_v1"))
    dem = circ.detector_error_model(decompose_errors=False, approximate_disjoint_errors=True)
    dec = LdpcBPOSD(dem, L2)
    t = time.perf_counter()
    pred = dec.decode_batch(det)[:, 0]
    sec = time.perf_counter() - t
    err = np.asarray(pred, dtype=np.uint8) != y
    with np.load(ROOT / "work" / "screen" / f"{stem}_errbits.npz") as z:
        astar = np.unpackbits(z["Astar"])[:n].astype(bool)
        screen_l2 = np.unpackbits(z["L2"])[:n].astype(bool)
    np.savez_compressed(ROOT / "work" / "step0" / f"{stem}_qdec{q_dec:.4f}_errbits.npz", err=np.packbits(err))
    rec = {"q_dec": q_dec, "q": q, "chunk": chunk, "shots": n, "errors": int(err.sum()),
           "astar_errors": int(astar.sum()), "cand_only": int((err & ~astar).sum()),
           "astar_only": int((astar & ~err).sum()), "ms_per_shot": 1000 * sec / n,
           "matches_screen_L2": bool(np.array_equal(err, screen_l2)) if q_dec == q else None}
    out.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(rec), flush=True)


if __name__ == "__main__":
    (ROOT / "work" / "step0").mkdir(parents=True, exist_ok=True)
    main()
