"""Project Phase C runtime from the real rehearsal (work/c_rehearsal). Writes C_PREFLIGHT.json.

Rehearsal timings were measured with 6 concurrent jobs, so no extra contention factor is applied.
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import c_contract as K  # noqa: E402

WORKERS, OVERHEAD, FIXED_S = 8, 1.25, 900   # fixed: calibration jobs (mixed-class flip stage ~90 s) + start-up
BUDGET_S = 18_000                            # 5 h hard wall budget


def main() -> None:
    recs = [json.loads(Path(f).read_text(encoding="utf-8")) for f in sorted(glob.glob(str(ROOT / "work/c_rehearsal/roots/*.json")))]
    if len(recs) != 6:
        raise SystemExit("needs the 6-root real rehearsal")
    per_cond = {c: sum(sum(r["ms_per_shot"].values()) for r in recs if r["cond"] == c) / 3 for c in K.CONDITIONS}
    shots_per_cond = K.FROZEN.roots_per_q * len(K.QS) * K.FROZEN.shots_per_root
    cpu_s = sum(shots_per_cond * ms / 1000 for ms in per_cond.values())
    wall_s = cpu_s / WORKERS * OVERHEAD + FIXED_S
    out = {"schema": "qshift-d5-learned-support-C-preflight-v1", "rehearsal_ms_per_shot_all_arms_by_condition": per_cond,
           "eval_shots": K.FROZEN.jobs * K.FROZEN.shots_per_root, "projected_cpu_seconds": cpu_s,
           "projected_wall_seconds": wall_s,
           "projected_max_seconds_per_job": max(per_cond.values()) * K.FROZEN.shots_per_root / 1000,
           "workers": WORKERS, "wall_budget_seconds": BUDGET_S, "within_budget": wall_s <= BUDGET_S,
           "note": "H rehearsal timings use SURROGATE_H (M0); the hidden support's cost may differ"}
    (ROOT / "C_PREFLIGHT.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
