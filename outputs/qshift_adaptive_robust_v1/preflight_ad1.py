"""AD1 preflight: project the run's wall time from the rehearsal (work/ad1/rehearsal) -> AD1_PREFLIGHT.json.

Rehearsal episodes decode REHEARSAL_EVAL_PER_BLOCK shots per block; the full run decodes EVAL_PER_BLOCK. The
projection scales each episode's measured L2 decode time per shot (from per-block timing is not recorded, so the
fixed part is estimated from a zero-decode baseline: total = fixed + per_shot * shots).
"""
from __future__ import annotations

import json
from pathlib import Path

import ad1
import ad1_config as C

ROOT = Path(__file__).resolve().parent
CONTENTION = 1.25
L2_SECONDS_PER_SHOT = 0.0185 * 1.6        # measured single-process 18.5 ms/shot, x1.6 for 8-way contention (RE1)


def main():
    recs = [json.loads(p.read_text(encoding="utf-8")) for p in (ad1.WORK / "rehearsal" / "records").glob("*.json")]
    worst = max(r["seconds"] for r in recs)
    reh_shots = C.REHEARSAL_EVAL_PER_BLOCK * len(C.SCORED) * len(C.L2_ARMS)
    full_shots = C.EVAL_PER_BLOCK * len(C.SCORED) * len(C.L2_ARMS)
    per_episode = worst + (full_shots - reh_shots) * L2_SECONDS_PER_SHOT
    n_ep = len(C.SCHEDULES) * C.EPISODES
    waves = -(-n_ep // 8)
    est = waves * per_episode
    out = {"rehearsal_worst_episode_s": worst, "l2_seconds_per_shot_assumed": L2_SECONDS_PER_SHOT,
           "projected_episode_s": round(per_episode), "episodes": n_ep, "workers": 8, "waves": waves,
           "projected_s": round(est), "projected_s_with_contention": round(est * CONTENTION), "budget_s": C.BUDGET_S,
           "within_budget": est * CONTENTION <= C.BUDGET_S, "job_timeout_s": C.JOB_TIMEOUT_S,
           "within_job_timeout": per_episode * CONTENTION <= C.JOB_TIMEOUT_S,
           "fallback": f"{C.EPISODES_FALLBACK} episodes per schedule" if est * CONTENTION > C.BUDGET_S else "not applied"}
    (ROOT / "AD1_PREFLIGHT.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8",
                                             newline="\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
