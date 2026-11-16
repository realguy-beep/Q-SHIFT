"""Independent post-run recount for V1.5. Deliberately imports nothing from this package.

Re-derives every arm's error totals and the co-primary point estimates directly
from the saved evaluation .npz files with plain NumPy, then compares them to the
run's analysis.json. Read-only; exits non-zero on any mismatch.
Usage: python recount_from_scratch.py <run_dir>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ARMS = ["Astar", "A2sw", "Boff", "BoffStatic", "Bexact"]
QS = ["0.0", "0.01", "0.02"]
ROOTS = 24


def main(argv: list[str] | None = None) -> int:
    run = Path((argv or sys.argv[1:])[0]).resolve()
    totals = {a: [0, 0, 0] for a in ARMS}
    per_root = {}
    sizes = set()
    for qi in range(3):
        for r in range(ROOTS):
            with np.load(run / "evaluation" / f"eval_q{qi}_r{r:02d}.npz", allow_pickle=False) as z:
                y = z["observables"][:, 0]
                sizes.add(len(y))
                for a in ARMS:
                    e = int(np.count_nonzero(z[f"pred_{a}"][:, 0] != y))
                    totals[a][qi] += e
                    per_root[(a, qi, r)] = e / len(y)
    if len(sizes) != 1:
        raise SystemExit(f"archives have unequal shot counts: {sorted(sizes)}")
    print("shots per root", sizes.pop())

    def contrast(x, b):
        return float(np.mean([np.mean([per_root[(x, qi, r)] - per_root[(b, qi, r)] for r in range(ROOTS)])
                              for qi in (1, 2)]))

    analysis = json.loads((run / "analysis.json").read_text(encoding="utf-8"))
    problems = []
    for a in ARMS:
        recorded = [analysis["arm_errors_by_condition"][a][q] for q in QS]
        if recorded != totals[a]:
            problems.append(f"{a}: recount {totals[a]} vs analysis {recorded}")
    for x, b in (("Bexact", "BoffStatic"), ("Bexact", "Astar")):
        mine = contrast(x, b)
        theirs = analysis["co_primary"][f"{x}_minus_{b}"]["nonzero_equal_weight_estimate"]
        if abs(mine - theirs) > 1e-12:
            problems.append(f"{x}-{b}: recount {mine} vs analysis {theirs}")
        print(f"{x}-{b} nonzero point estimate {mine:+.6f}")
    for a in ARMS:
        print(a, totals[a])
    print("RECOUNT", "MISMATCH" if problems else "MATCHES analysis.json", *problems, sep="\n")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
