"""Project Step E runtime from the real rehearsal (work/eval_rehearsal). Writes EVAL_PREFLIGHT.json."""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import eval_contract as K  # noqa: E402

CONTENTION = 30.3 / 20.65   # Step 0: L2 at 8 workers vs single-process (see d=5 Phase 2 preflight)
WORKERS, OVERHEAD, FIXED_S = 8, 1.25, 600
BUDGET_S = 18_000           # 5 h hard wall budget (approved cap 10 h)


def main() -> None:
    recs = [json.loads(Path(f).read_text(encoding="utf-8")) for f in sorted(glob.glob(str(ROOT / "work/eval_rehearsal/roots/*.json")))]
    if len(recs) != 9:
        raise SystemExit("needs the 9-root real rehearsal")
    per_cond = {c: sum(sum(r["ms_per_shot"].values()) for r in recs if r["cond"] == c) / 3 for c in K.CONDITIONS}
    per_root_shots = K.FROZEN.roots_per_q * len(K.QS) * K.FROZEN.shots_per_root
    cpu_s = sum(per_root_shots * ms * CONTENTION / 1000 for ms in per_cond.values())
    wall_s = cpu_s / WORKERS * OVERHEAD + FIXED_S
    out = {"schema": "qshift-d5-robustness-preflight-v1", "rehearsal_ms_per_shot_all_arms_by_condition": per_cond,
           "contention_factor": CONTENTION, "eval_shots": K.FROZEN.jobs * K.FROZEN.shots_per_root,
           "projected_cpu_seconds": cpu_s, "projected_wall_seconds": wall_s,
           "projected_max_seconds_per_job": max(per_cond.values()) * CONTENTION * K.FROZEN.shots_per_root / 1000,
           "workers": WORKERS, "wall_budget_seconds": BUDGET_S, "within_budget": wall_s <= BUDGET_S}
    (ROOT / "EVAL_PREFLIGHT.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
