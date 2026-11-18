"""Project Stage E runtime from the real rehearsal (work/eval_rehearsal). Writes EVAL_PREFLIGHT.json.

Rehearsal jobs run with up to 6 in parallel, so their ms/shot already include contention; a further
contention factor of 1.25 and 25% overhead are applied conservatively.
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import eval_contract as K  # noqa: E402

CONTENTION = 1.25
WORKERS, OVERHEAD, FIXED_S = 8, 1.25, 600
BUDGET_S = 18_000           # 5 h hard wall budget


def main() -> None:
    recs = [json.loads(Path(f).read_text(encoding="utf-8")) for f in sorted(glob.glob(str(ROOT / "work/eval_rehearsal/roots/*.json")))]
    if len(recs) != 6:
        raise SystemExit("needs the 6-root real rehearsal")
    per_cond = {c: sum(sum(r["ms_per_shot"].values()) for r in recs if r["cond"] == c) / 3 for c in K.CONDITIONS}
    shots = {c: K.FROZEN.roots_per_q * len(K.QS) * K.FROZEN.shots(c) for c in K.CONDITIONS}
    cpu_s = sum(shots[c] * per_cond[c] * CONTENTION / 1000 for c in K.CONDITIONS)
    wall_s = cpu_s / WORKERS * OVERHEAD + FIXED_S
    out = {"schema": "qshift-d5-lowp-regime-preflight-v1", "rehearsal_ms_per_shot_all_arms_by_condition": per_cond,
           "contention_factor": CONTENTION, "eval_shots": K.FROZEN.total_shots, "eval_jobs": K.FROZEN.jobs,
           "projected_cpu_seconds": cpu_s, "projected_wall_seconds": wall_s,
           "projected_max_seconds_per_job": max(per_cond[c] * CONTENTION * K.FROZEN.shots(c) / 1000 for c in K.CONDITIONS),
           "workers": WORKERS, "wall_budget_seconds": BUDGET_S, "within_budget": wall_s <= BUDGET_S}
    (ROOT / "EVAL_PREFLIGHT.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
