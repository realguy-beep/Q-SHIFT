"""Independent post-run recount for V1.6b. Deliberately imports nothing from this package.

Re-derives each condition's arm error totals and the key contrasts' point estimates from
the saved evaluation .npz files with plain NumPy, compares them to analysis.json, and
exits non-zero on any mismatch. Usage: recount_from_scratch.py <run_dir>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

CONDITIONS = ["known", "hidden"]
ARMS = ["A_nominal", "Astar_oracle", "Astar_learned", "BoffStatic_oracle", "Bexact_oracle", "Blearn"]
KEY = [("Blearn", "Astar_oracle"), ("Blearn", "Astar_learned"), ("Blearn", "Bexact_oracle")]
ROOTS = 24


def main(argv: list[str] | None = None) -> int:
    run = Path((argv or sys.argv[1:])[0]).resolve()
    analysis = json.loads((run / "analysis.json").read_text(encoding="utf-8"))
    problems = []
    for cond in CONDITIONS:
        totals = {a: [0, 0, 0] for a in ARMS}
        rate = {}
        for qi in range(3):
            for r in range(ROOTS):
                with np.load(run / cond / "evaluation" / f"eval_q{qi}_r{r:02d}.npz", allow_pickle=False) as z:
                    y = z["observables"][:, 0]
                    for a in ARMS:
                        e = int(np.count_nonzero(z[f"pred_{a}"][:, 0] != y))
                        totals[a][qi] += e
                        rate[(a, qi, r)] = e / len(y)
        for a in ARMS:
            if analysis["conditions"][cond]["arm_errors_q0_q001_q002"][a] != totals[a]:
                problems.append(f"{cond} {a}: {totals[a]} vs {analysis['conditions'][cond]['arm_errors_q0_q001_q002'][a]}")
            print(cond, a, totals[a])
        for x, b in KEY:
            mine = float(np.mean([np.mean([rate[(x, qi, r)] - rate[(b, qi, r)] for r in range(ROOTS)]) for qi in (1, 2)]))
            theirs = analysis["conditions"][cond]["contrasts"][f"{x}_minus_{b}"]["nonzero_estimate"]
            if abs(mine - theirs) > 1e-12:
                problems.append(f"{cond} {x}-{b}: {mine} vs {theirs}")
            print(cond, f"{x}-{b} {mine:+.6f}")
    print("RECOUNT", "MISMATCH" if problems else "MATCHES analysis.json", *problems, sep="\n")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
