"""Apply the pre-registered SCREEN_PROTOCOL.md selection rule. Writes SCREEN_RESULTS.json once."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "SCREEN_RESULTS.json"
QS = (0.0, 0.01, 0.02)
CHUNKS = {7: 6, 5: 2}
CANDS = ("L0", "L1", "L2", "L3")
ARMS = ("Astar", "A_nominal") + CANDS + ("N3",)


def main() -> None:
    if OUT.exists():
        raise SystemExit("SCREEN_RESULTS.json exists; aggregation runs once")
    seeds = json.loads((ROOT / "SCREEN_SEEDS.json").read_text(encoding="utf-8"))["seeds"]
    res = {}
    for d, nc in CHUNKS.items():
        tot = {a: {str(q): 0 for q in QS} for a in ARMS}
        shots = {str(q): 0 for q in QS}
        n3_rows = {str(q): 0 for q in QS}
        disc = {c: {"cand_only": 0, "astar_only": 0} for c in CANDS}
        n3_sub = {a: 0 for a in ("N3", "Astar") + CANDS}
        ms = {a: [] for a in ARMS}
        for q in QS:
            for c in range(nc):
                stem = f"d{d}_q{q:.2f}_c{c}"
                js = json.loads((ROOT / "results" / "screen_json" / f"{stem}.json").read_text(encoding="utf-8"))
                if js["seed"] != seeds[f"screen:d{d}:q{q:.2f}:chunk{c}"] or js["rehearsal"]:
                    raise RuntimeError(f"seed/rehearsal mismatch in {stem}")
                n = js["shots"]
                shots[str(q)] += n
                n3_rows[str(q)] += js["N3_rows"]
                with np.load(ROOT / "work" / "screen" / f"{stem}_errbits.npz") as z:
                    bits = {a: np.unpackbits(z[a])[: (js["N3_rows"] if a == "N3" else n)].astype(bool) for a in ARMS}
                for a in ARMS:
                    if int(bits[a].sum()) != js["errors"][a]:
                        raise RuntimeError(f"error-bit mismatch {stem} {a}")
                    tot[a][str(q)] += js["errors"][a]
                    ms[a].append(js["ms_per_shot"][a])
                if q > 0:
                    for cnd in CANDS:
                        disc[cnd]["cand_only"] += int((bits[cnd] & ~bits["Astar"]).sum())
                        disc[cnd]["astar_only"] += int((bits["Astar"] & ~bits[cnd]).sum())
                k = js["N3_rows"]
                for a in n3_sub:
                    n3_sub[a] += int(bits[a][:k].sum())
        nonzero = {a: tot[a]["0.01"] + tot[a]["0.02"] for a in ARMS if a != "N3"}
        res[d] = {"errors_by_q": tot, "shots_by_q": shots, "nonzero_errors": nonzero, "discordance_vs_Astar": disc,
                  "N3_subsample_errors_all_q": n3_sub, "N3_rows_by_q": n3_rows,
                  "mean_ms_per_shot": {a: float(np.mean(v)) for a, v in ms.items()}}
    r7, r5 = res[7], res[5]
    sel = min(CANDS, key=lambda c: (r7["nonzero_errors"][c], c))
    c1 = (r7["nonzero_errors"][sel] < r7["nonzero_errors"]["Astar"]
          and r7["errors_by_q"][sel]["0.0"] <= 1.10 * r7["errors_by_q"]["Astar"]["0.0"])
    c2 = r5["nonzero_errors"][sel] < r5["nonzero_errors"]["Astar"]
    any_beats_d7 = any(r7["nonzero_errors"][c] < r7["nonzero_errors"]["Astar"] for c in CANDS)
    outcome = "ADVANCE" if (c1 and c2) else ("REVISE" if any_beats_d7 else "STOP_d7")
    out = {"schema": "qshift-d57-screen-results-v1", "per_distance": {str(d): v for d, v in res.items()},
           "selected_candidate": sel, "criterion_1_d7": c1, "criterion_2_d5": c2,
           "any_candidate_beats_Astar_d7": any_beats_d7, "outcome": outcome,
           "label": "DEVELOPMENT ONLY: in-sample configuration screen; small d=7 counts; not evidence"}
    OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("OUTCOME", outcome, "selected", sel, "c1", c1, "c2", c2)
    for d in (7, 5):
        print(f"d={d} nonzero errors", res[d]["nonzero_errors"], "| q0", {a: res[d]["errors_by_q"][a]["0.0"] for a in ARMS if a != "N3"})
        print("   discordance", res[d]["discordance_vs_Astar"], "| N3 subsample", res[d]["N3_subsample_errors_all_q"])
        print("   ms/shot", {a: round(v, 2) for a, v in res[d]["mean_ms_per_shot"].items()})


if __name__ == "__main__":
    main()
