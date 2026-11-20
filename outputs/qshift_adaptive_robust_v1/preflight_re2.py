"""RE2 preflight: project the run's wall time from the rehearsal (work/re2/rehearsal) -> RE2_PREFLIGHT.json.

Per root: fixed part = total seconds minus the measured evaluation decode seconds (sampling, E1T, learning,
decoder builds, S* selection). Per arm: decode seconds per shot from the rehearsal, floored at RE1's measured
29.5 ms per BP+OSD arm per shot (rehearsal batches are small and noisy). Projection: the slowest root, times
ceil(66 / 8) waves, times a 1.25 contention factor. Fallback (drop L2L_B2) if the budget or the job timeout would
be exceeded.
"""
from __future__ import annotations

import json
import math

import re2
import re2_config as C
import studykit as SK

CONTENTION = 1.25
RE1_L2_S_PER_SHOT = 0.0295
L2_ARMS = ("L2L_E", "L2s_true", "L2L_B2")


def project(recs, with_b2):
    per_root = {}
    for r in recs:
        dec_s = sum(sum(q["seconds"].values()) for q in r["per_q"].values())
        fixed = r["seconds"] - dec_s
        shots = sum(q["shots"] for q in r["per_q"].values())
        rate = {a: sum(q["seconds"][a] for q in r["per_q"].values()) / shots for a in r["arms"]}
        for a in L2_ARMS:
            if a in rate:
                rate[a] = max(rate[a], RE1_L2_S_PER_SHOT)
        arms = [a for a in r["arms"] if with_b2 or a != "L2L_B2"]
        per_root[r["cond"]] = fixed + sum(rate[a] for a in arms) * C.EVAL_SHOTS * len(C.QS)
    n_roots = sum(v[3] for v in C.CONDITIONS.values())
    waves = math.ceil(n_roots / 8)
    worst = max(per_root.values())
    return {"per_root_s": {k: round(v) for k, v in per_root.items()}, "worst_root_s": round(worst),
            "roots": n_roots, "waves": waves, "projected_s": round(worst * waves),
            "projected_s_with_contention": round(worst * waves * CONTENTION)}


def main():
    recs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((re2.WORK / "rehearsal" / "roots").glob("*.json"))]
    if len(recs) != len(C.CONDITIONS):
        raise SystemExit("rehearsal incomplete")
    full = project(recs, True)
    fits = full["projected_s_with_contention"] <= C.BUDGET_S and full["worst_root_s"] * CONTENTION <= C.JOB_TIMEOUT_S
    out = {"with_L2L_B2": full, "without_L2L_B2": project(recs, False), "budget_s": C.BUDGET_S,
           "job_timeout_s": C.JOB_TIMEOUT_S, "contention": CONTENTION, "l2_floor_s_per_shot": RE1_L2_S_PER_SHOT,
           "workers": 8, "fallback": C.FALLBACK, "fallback_applied": not fits}
    SK.write_once_json(C.ROOT / "RE2_PREFLIGHT.json", out)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
