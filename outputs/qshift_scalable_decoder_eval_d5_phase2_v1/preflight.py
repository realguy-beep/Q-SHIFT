"""Project Phase 2 runtime from the real rehearsal (work/rehearsal) and Step 0 contention data. Writes PREFLIGHT.json."""
from __future__ import annotations

import glob
import json
from pathlib import Path

import contract as K

ROOT = Path(__file__).resolve().parent
CONTENTION = 30.3 / 20.65   # Step 0 L2 at 8 workers vs screen L2 at true q (PHASE2_D5_PRIOR.json / SCREEN_RESULTS.json)
WORKERS, OVERHEAD, FIXED_S = 8, 1.25, 600
BUDGET_S = 10_800           # 3 h hard wall-time budget for the single run (approved cap: 10 h)


def main() -> None:
    recs = [json.loads(Path(f).read_text(encoding="utf-8")) for f in sorted(glob.glob(str(ROOT / "work/rehearsal/roots/*.json")))]
    if len(recs) != 3:
        raise SystemExit("needs the 3-root real rehearsal")
    ms = sum(sum(r["ms_per_shot"].values()) for r in recs) / len(recs)   # all arms, per shot, rehearsal (3 workers)
    total = K.FROZEN.jobs * K.FROZEN.shots_per_root
    cpu_s = total * ms * CONTENTION / 1000
    wall_s = cpu_s / WORKERS * OVERHEAD + FIXED_S
    job_s = K.FROZEN.shots_per_root * ms * CONTENTION / 1000
    out = {"schema": "qshift-d5-phase2-preflight-v1", "rehearsal_ms_per_shot_all_arms": ms,
           "contention_factor": CONTENTION, "eval_shots": total, "projected_cpu_seconds": cpu_s,
           "projected_wall_seconds": wall_s, "projected_seconds_per_job": job_s, "workers": WORKERS,
           "wall_budget_seconds": BUDGET_S, "within_budget": wall_s <= BUDGET_S,
           "per_arm_ms_rehearsal": {a: sum(r["ms_per_shot"][a] for r in recs) / len(recs) for a in K.ARMS}}
    (ROOT / "PREFLIGHT.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
