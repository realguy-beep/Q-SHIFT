"""AD2 preflight: project the run's wall time from the rehearsal (work/ad2/rehearsal) -> AD2_PREFLIGHT.json.

Per episode: non-decode seconds (sampling, estimation, decoder builds) + decode seconds x (1,000 / 200) evaluation
shots. Without AD_W3: minus the rehearsal's AD_W3 seconds (unscaled, conservative). Projection: the slowest episode x
ceil(jobs / 8) waves x 1.25 contention. Fallback level 0 = as planned; 1 = drop AD_W3; 2 = also 5 episodes per
schedule. The lowest level that fits the budget and the job timeout is applied.
"""
from __future__ import annotations

import json
import math

import ad2
import ad2_config as C
import studykit as SK


def main():
    recs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((ad2.WORK / "rehearsal" / "records").glob("*.json"))]
    if len(recs) != len(C.REHEARSAL):
        raise SystemExit("rehearsal incomplete")
    scale = C.EVAL_PER_BLOCK / C.REHEARSAL_EVAL_PER_BLOCK
    per = {}
    for r in recs:
        tm = r["timing"]
        full = (r["seconds"] - tm["decode_s"]) + tm["decode_s"] * scale
        per[r["schedule"]] = {"with_w3": round(full), "without_w3": round(full - tm["w3_s"])}
    levels = []
    for lvl, key, eps in ((0, "with_w3", C.EPISODES), (1, "without_w3", C.EPISODES), (2, "without_w3", C.EPISODES_FALLBACK)):
        worst = max(v[key] for v in per.values())
        jobs = len(C.SCHEDULES) * eps
        waves = math.ceil(jobs / 8)
        proj = worst * waves * C.CONTENTION
        levels.append({"level": lvl, "worst_episode_s": worst, "jobs": jobs, "waves": waves,
                       "projected_s_with_contention": round(proj),
                       "fits": proj <= C.BUDGET_S and worst * C.CONTENTION <= C.JOB_TIMEOUT_S})
    fit = next((x["level"] for x in levels if x["fits"]), None)
    out = {"per_episode_s": per, "levels": levels, "budget_s": C.BUDGET_S, "job_timeout_s": C.JOB_TIMEOUT_S,
           "contention": C.CONTENTION, "workers": 8, "fallback": C.FALLBACK,
           "fallback_level": fit if fit is not None else 2, "fits_budget": fit is not None}
    SK.write_once_json(C.ROOT / "AD2_PREFLIGHT.json", out)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
