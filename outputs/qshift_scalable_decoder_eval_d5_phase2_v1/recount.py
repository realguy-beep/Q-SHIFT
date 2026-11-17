"""Independent post-run recount: totals from archives (no analyzer code) and a re-decode check.

Usage: recount.py <mode> <run_dir> <analysis_json>
Re-decodes root 0 at every q from the saved detectors with every arm and requires bit-identical
predictions; recounts every arm's per-q totals and requires equality with ANALYSIS.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import contract as K  # noqa: E402
import eval_job  # noqa: E402


def main() -> None:
    mode, run_dir, analysis = sys.argv[1], Path(sys.argv[2]), json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
    alloc = K.MODES[mode]
    totals = {a: [0, 0, 0] for a in K.ARMS}
    for qi in range(len(K.QS)):
        for r in range(alloc.roots_per_q):
            with np.load(run_dir / "archives" / f"{K.stem(qi, r)}.npz") as z:
                y = z["observables"]
                for a in K.ARMS:
                    totals[a][qi] += int((np.unpackbits(z[f"pred_{a}"])[: len(y)] != y).sum())
    if totals != analysis["arm_errors_q0_q001_q002"]:
        raise SystemExit(f"recount mismatch: {totals} vs {analysis['arm_errors_q0_q001_q002']}")
    spec = eval_job.m.CodeSpec(distance=K.DISTANCE)
    qubits = eval_job.m.burst_qubits(spec, K.BURST_FAMILY)
    redecode = {}
    for qi in range(len(K.QS)):
        rec = json.loads((run_dir / "roots" / f"{K.stem(qi, 0)}.json").read_text(encoding="utf-8"))
        with np.load(run_dir / "archives" / f"{K.stem(qi, 0)}.npz") as z:
            det = np.unpackbits(z["detectors"], axis=1)[:, : rec["num_detectors"]]
            saved = {a: np.unpackbits(z[f"pred_{a}"])[: len(det)] for a in K.ARMS}
        res = eval_job.decode_all(spec, K.QS[qi], qubits, det)
        redecode[K.stem(qi, 0)] = {a: bool(np.array_equal(res[a][0], saved[a])) for a in K.ARMS}
    if not all(all(v.values()) for v in redecode.values()):
        raise SystemExit(f"re-decode mismatch: {redecode}")
    print(json.dumps({"recount_matches_analysis": True, "redecode_bit_identical": redecode}))


if __name__ == "__main__":
    main()
