"""Apply the STEP0_PROTOCOL.md selection rule. Writes PHASE2_D5_PRIOR.json once."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "PHASE2_D5_PRIOR.json"
QDEC = (0.0, 0.0025, 0.005, 0.01, 0.02)
QS = (0.0, 0.01, 0.02)


def main() -> None:
    if OUT.exists():
        raise SystemExit("PHASE2_D5_PRIOR.json exists; aggregation runs once")
    table, integrity, astar = {}, [], {str(q): 0 for q in QS}
    for qd in QDEC:
        row = {"errors_by_q": {str(q): 0 for q in QS}, "cand_only_nz": 0, "astar_only_nz": 0, "ms_per_shot": []}
        for q in QS:
            for c in (0, 1):
                r = json.loads((ROOT / "results" / "step0_json" / f"d5_q{q:.2f}_c{c}_qdec{qd:.4f}.json").read_text(encoding="utf-8"))
                row["errors_by_q"][str(q)] += r["errors"]
                row["ms_per_shot"].append(r["ms_per_shot"])
                if qd == QDEC[0]:
                    astar[str(q)] += r["astar_errors"]
                if q > 0:
                    row["cand_only_nz"] += r["cand_only"]
                    row["astar_only_nz"] += r["astar_only"]
                if r["matches_screen_L2"] is not None:
                    integrity.append({"stem": f"d5_q{q:.2f}_c{c}", "matches": r["matches_screen_L2"]})
        row["nonzero_errors"] = row["errors_by_q"]["0.01"] + row["errors_by_q"]["0.02"]
        row["ms_per_shot"] = sum(row["ms_per_shot"]) / len(row["ms_per_shot"])
        table[f"{qd:.4f}"] = row
    if len(integrity) != 6 or not all(i["matches"] for i in integrity):
        raise SystemExit(f"integrity check failed: {integrity}; no selection made")
    limit = 1.10 * astar["0.0"]
    eligible = [qd for qd in QDEC if table[f"{qd:.4f}"]["errors_by_q"]["0.0"] <= limit]
    if eligible:
        sel, guard_failed = min(eligible, key=lambda qd: (table[f"{qd:.4f}"]["nonzero_errors"], qd)), False
    else:
        sel, guard_failed = min(QDEC, key=lambda qd: (table[f"{qd:.4f}"]["errors_by_q"]["0.0"], qd)), True
    out = {"schema": "qshift-d5-phase2-prior-v1", "candidate": "L2", "selected_q_dec": sel,
           "guard_failed": guard_failed, "eligible": eligible, "q0_limit": limit,
           "astar_errors_by_q": astar, "astar_nonzero": astar["0.01"] + astar["0.02"], "grid": table,
           "integrity_true_q_reproduces_screen_L2": integrity,
           "label": "DEVELOPMENT ONLY: in-sample prior selection on saved screen arrays; not evidence"}
    OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("SELECTED q_dec", sel, "guard_failed", guard_failed, "| Astar", astar)
    for k, v in table.items():
        print(k, v["errors_by_q"], "nz", v["nonzero_errors"], "disc", v["cand_only_nz"], "/", v["astar_only_nz"],
              f"{v['ms_per_shot']:.1f} ms")


if __name__ == "__main__":
    main()
