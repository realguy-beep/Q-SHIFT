"""Recompute illustrative log(ARL)/KL scales from the 101-point nuisance grid."""
from __future__ import annotations

import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARL_TARGETS = (100, 1_000, 10_000)


def main() -> None:
    dense = json.loads((HERE / "BURST_STEP_DENSE_NUISANCE_AUDIT.json").read_text(encoding="utf-8"))
    rows = []
    for row in dense["rows"]:
        d = row["minimum_KL_new_given_old_nats_per_shot"]
        rows.append({
            "model": row["model"], "old_burst_p": row["old_burst_p"],
            "new_burst_p": row["new_burst_p"],
            "dense_grid_min_D_nats_per_shot": d,
            "old_measurement_p": row["old_measurement_p_at_minimum_grid"],
            "new_measurement_p": row["new_measurement_p_at_minimum_grid"],
            "grid_spacing": row["grid_spacing"],
            "illustrative_log_ARL_over_D_scales_shots": {
                str(gamma): math.log(gamma) / d for gamma in ARL_TARGETS
            },
        })
    result = {
        "classification": "ASYMPTOTIC_KL_SCALE_USING_DENSE_FINITE_NUISANCE_GRID_NOT_ROBUST_CONTINUOUS_BOUND",
        "method": "Apply log(gamma)/D(P1||P0) to each dense-grid minimum from the 101x101 independent old/new measurement-p grid.",
        "illustrative_arl_targets_shots": list(ARL_TARGETS),
        "rows": rows,
        "limits": [
            "The 101-point grid is not continuous optimization; no continuous-nuisance lower bound is established.",
            "The formula is a first-order asymptotic scale under known IID simple hypotheses, not finite-history delay or CUSUM operating characteristics.",
            "Only the ten burst-pair detectors are used; no logical outcomes, alarm thresholds or detector histories are evaluated."
        ],
        "sampling_calls": 0,
        "decoder_calls": 0,
    }
    (HERE / "QCD_DENSE_NUISANCE_SCALE_AUDIT.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"rows": rows}, indent=2))


if __name__ == "__main__":
    main()
