"""BM0 screen job on one saved d57 screen chunk (SCREEN_PROTOCOL.md). Usage: screen_job.py <d> <q> <chunk>"""
from __future__ import annotations

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

SRC = REPO / "outputs" / "qshift_scalable_decoder_eval_d57_v1"


def main() -> None:
    d, q, c = int(sys.argv[1]), float(sys.argv[2]), int(sys.argv[3])
    stem = f"d{d}_q{q:.2f}_c{c}"
    out = ROOT / "results" / "screen_json" / f"{stem}.json"
    if out.exists():
        raise SystemExit(f"{stem} exists; refusing to rerun")
    out.parent.mkdir(parents=True, exist_ok=True)
    (ROOT / "work" / "screen_bm").mkdir(parents=True, exist_ok=True)
    seeds = json.loads((SRC / "SCREEN_SEEDS.json").read_text(encoding="utf-8"))["seeds"]
    meta = json.loads((SRC / "results" / "screen_json" / f"{stem}.json").read_text(encoding="utf-8"))
    if meta["seed"] != seeds[f"screen:d{d}:q{q:.2f}:chunk{c}"] or meta["rehearsal"]:
        raise RuntimeError("seed mismatch")
    with np.load(SRC / "work" / "screen" / f"{stem}_shots.npz") as z:
        n, nd = int(z["n"]), int(z["num_detectors"])
        x = np.unpackbits(z["detectors"], axis=1)[:, :nd]
        y = np.unpackbits(z["observables"])[:n]
    with np.load(SRC / "work" / "screen" / f"{stem}_errbits.npz") as z:
        ref = {a: np.unpackbits(z[a])[:n].astype(bool) for a in ("Astar", "L2")}
    if n != meta["shots"] or int(ref["Astar"].sum()) != meta["errors"]["Astar"]:
        raise RuntimeError("saved data mismatch")
    cfg, conv, qd = bm.VARIANTS["BM0"]
    spec = m.CodeSpec(distance=d)
    dec = bm.BeliefMatching(m.build_decomposed_dem(m.build_candidate_circuit(spec, qd, m.burst_qubits(spec, "scaled_v1"))),
                            cfg, conv)
    t = time.perf_counter()
    err = dec.decode_batch(x) != y
    sec = time.perf_counter() - t
    np.savez_compressed(ROOT / "work" / "screen_bm" / f"{stem}_errbits.npz", BM0=np.packbits(err))
    rec = {"d": d, "q": q, "chunk": c, "seed": meta["seed"], "shots": n, "BM0_errors": int(err.sum()),
           "Astar_errors": int(ref["Astar"].sum()), "L2_errors": int(ref["L2"].sum()),
           "bm_only_vs_Astar": int((err & ~ref["Astar"]).sum()), "astar_only": int((ref["Astar"] & ~err).sum()),
           "bm_only_vs_L2": int((err & ~ref["L2"]).sum()), "l2_only": int((ref["L2"] & ~err).sum()),
           "ms_per_shot": 1000 * sec / n, "stats": dec.stats}
    out.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(rec), flush=True)


if __name__ == "__main__":
    main()
