"""AD3 preflight: project the run's wall time from the rehearsal (work/ad3/rehearsal) -> AD3_PREFLIGHT.json.

Per episode: non-decode seconds (sampling, estimation, decoder builds) + decode seconds x (1,000 / 200) evaluation
shots. Projection: the slowest episode x ceil(jobs / 8) waves x 1.25 contention. Fallback level 0 = 6 episodes per
schedule; 1 = 5 episodes. The lowest level that fits the budget and the job timeout is applied.
"""
from __future__ import annotations

import json
import math

import ad3
import ad3_config as C
import studykit as SK


def main():
    recs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((ad3.WORK / "rehearsal" / "records").glob("*.json"))]
    if len(recs) != len(C.REHEARSAL):
        raise SystemExit("rehearsal incomplete")
    scale = C.EVAL_PER_BLOCK / C.REHEARSAL_EVAL_PER_BLOCK
    per = {r["schedule"]: round((r["seconds"] - r["timing"]["decode_s"]) + r["timing"]["decode_s"] * scale)
           for r in recs}
    worst = max(per.values())
    levels = []
    for lvl, eps in ((0, C.EPISODES), (1, C.EPISODES_FALLBACK)):
        jobs = len(C.SCHEDULES) * eps
        waves = math.ceil(jobs / 8)
        proj = worst * waves * C.CONTENTION
        levels.append({"level": lvl, "episodes": eps, "jobs": jobs, "waves": waves, "worst_episode_s": worst,
                       "projected_s_with_contention": round(proj),
                       "fits": proj <= C.BUDGET_S and worst * C.CONTENTION <= C.JOB_TIMEOUT_S})
    fit = next((x["level"] for x in levels if x["fits"]), None)
    out = {"per_episode_s": per, "levels": levels, "budget_s": C.BUDGET_S, "job_timeout_s": C.JOB_TIMEOUT_S,
           "contention": C.CONTENTION, "workers": 8, "fallback": C.FALLBACK,
           "fallback_level": fit if fit is not None else 1, "fits_budget": fit is not None}
    SK.write_once_json(C.ROOT / "AD3_PREFLIGHT.json", out)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
