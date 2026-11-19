"""BRE preflight: project BRE-1 wall time from the rehearsal records (work/bre/rehearsal) -> BRE_PREFLIGHT.json."""
from __future__ import annotations

import json
import math
from pathlib import Path

import bre
import bre_config as C

ROOT = Path(__file__).resolve().parent
CONTENTION = 1.25


def main():
    recs = [json.loads(p.read_text(encoding="utf-8")) for p in (bre.WORK / "rehearsal" / "records").glob("*.json")]
    burst = max(r["seconds"] for r in recs if r["kind"] == "burst")
    q0 = max(r["seconds"] for r in recs if r["kind"] == "q0")
    b = bre.bursts()
    n_burst = len(C.CONDITIONS) * len(C.burst_ids(b)) * C.POOLS_PER_BURST
    n_q0 = len(C.CONDITIONS) * C.Q0_POOLS
    workers = 8
    est = (n_burst * burst + n_q0 * q0) / workers
    out = {"rehearsal_max_seconds": {"burst": burst, "q0": q0}, "jobs": {"burst": n_burst, "q0": n_q0},
           "workers": workers, "projected_s": round(est), "projected_s_with_contention": round(est * CONTENTION),
           "contention_factor": CONTENTION, "budget_s": C.BUDGET_S,
           "within_budget": est * CONTENTION <= C.BUDGET_S,
           "fallback": f"drop {C.PREFLIGHT_DROP}" if est * CONTENTION > C.BUDGET_S else "not applied",
           "max_job_s": math.ceil(max(burst, q0)), "job_timeout_s": C.JOB_TIMEOUT_S}
    (ROOT / "BRE_PREFLIGHT.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8",
                                             newline="\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
