"""Apply the SCREEN_PROTOCOL.md rule. Writes SCREEN_RESULTS.json once."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "SCREEN_RESULTS.json"
CHUNKS, QS = {7: 6, 5: 2}, (0.0, 0.01, 0.02)
KEYS = ("BM0_errors", "Astar_errors", "L2_errors", "bm_only_vs_Astar", "astar_only", "bm_only_vs_L2", "l2_only")


def main() -> None:
    if OUT.exists():
        raise SystemExit("SCREEN_RESULTS.json exists")
    res = {}
    for d, nc in CHUNKS.items():
        by_q = {str(q): {k: 0 for k in KEYS} for q in QS}
        ms, conv = [], 0
        for q in QS:
            for c in range(nc):
                r = json.loads((ROOT / "results" / "screen_json" / f"d{d}_q{q:.2f}_c{c}.json").read_text(encoding="utf-8"))
                with np.load(ROOT / "work" / "screen_bm" / f"d{d}_q{q:.2f}_c{c}_errbits.npz") as z:
                    if int(np.unpackbits(z["BM0"])[: r["shots"]].sum()) != r["BM0_errors"]:
                        raise RuntimeError("error-bit mismatch")
                for k in KEYS:
                    by_q[str(q)][k] += r[k]
                ms.append(r["ms_per_shot"])
                conv += r["stats"]["bp_converged"]
        nz = {k: by_q["0.01"][k] + by_q["0.02"][k] for k in KEYS}
        res[str(d)] = {"by_q": by_q, "nonzero": nz, "mean_ms_per_shot": float(np.mean(ms)), "bp_converged": conv}
    r7, r5 = res["7"], res["5"]
    beats7 = r7["nonzero"]["BM0_errors"] < r7["nonzero"]["Astar_errors"]
    q0_ok = r7["by_q"]["0.0"]["BM0_errors"] <= 1.10 * r7["by_q"]["0.0"]["Astar_errors"]
    d5_ok = r5["nonzero"]["BM0_errors"] < r5["nonzero"]["Astar_errors"]
    outcome = "ADVANCE" if beats7 and q0_ok and d5_ok else ("REVISE" if beats7 else "STOP")
    out = {"schema": "qshift-bm-screen-results-v1", "per_distance": res, "d7_beats_Astar": beats7,
           "d7_q0_within_1_10": q0_ok, "d5_beats_Astar": d5_ok, "outcome": outcome,
           "label": "DEVELOPMENT ONLY: saved d57 screen arrays (re-used); small d=7 counts; not evidence"}
    OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("OUTCOME", outcome)
    for d in ("7", "5"):
        print(d, {q: {k: res[d]["by_q"][q][k] for k in KEYS[:3]} for q in res[d]["by_q"]}, "nz", res[d]["nonzero"],
              round(res[d]["mean_ms_per_shot"], 1), "ms")


if __name__ == "__main__":
    main()
