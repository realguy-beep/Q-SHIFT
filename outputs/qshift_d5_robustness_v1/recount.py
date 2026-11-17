"""Independent post-run recount: totals from archives (no analyzer code) plus a bit-identical re-decode
of root 0 for every (condition, q) with every arm (parallel processes).

Usage: recount.py <mode> <run_dir> <analysis_json>
"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import eval_contract as K  # noqa: E402


def redecode(args):
    run_dir, c, qi = args
    import eval_job
    rec = json.loads((Path(run_dir) / "roots" / f"{K.stem(c, qi, 0)}.json").read_text(encoding="utf-8"))
    with np.load(Path(run_dir) / "archives" / f"{K.stem(c, qi, 0)}.npz") as z:
        det = np.unpackbits(z["detectors"], axis=1)[:, : rec["num_detectors"]]
        saved = {a: np.unpackbits(z[f"pred_{a}"])[: len(det)] for a in K.ARMS}
    res = eval_job.decode_all(c, K.QS[qi], det)
    return K.stem(c, qi, 0), {a: bool(np.array_equal(res[a][0], saved[a])) for a in K.ARMS}


def main() -> None:
    mode, run_dir = sys.argv[1], Path(sys.argv[2]).resolve()
    analysis = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
    alloc = K.MODES[mode]
    totals = {c: {a: [0, 0, 0] for a in K.ARMS} for c in K.CONDITIONS}
    for c, qi, r in K.jobs(alloc):
        with np.load(run_dir / "archives" / f"{K.stem(c, qi, r)}.npz") as z:
            y = z["observables"]
            for a in K.ARMS:
                totals[c][a][qi] += int((np.unpackbits(z[f"pred_{a}"])[: len(y)] != y).sum())
    for c in K.CONDITIONS:
        if totals[c] != analysis["conditions"][c]["arm_errors_q0_q001_q002"]:
            raise SystemExit(f"recount mismatch for {c}")
    with ProcessPoolExecutor(max_workers=8) as pool:
        red = dict(pool.map(redecode, [(str(run_dir), c, qi) for c in K.CONDITIONS for qi in range(len(K.QS))]))
    if not all(all(v.values()) for v in red.values()):
        raise SystemExit(f"re-decode mismatch: {red}")
    print(json.dumps({"recount_matches_analysis": True, "redecode_bit_identical": red}))


if __name__ == "__main__":
    main()
