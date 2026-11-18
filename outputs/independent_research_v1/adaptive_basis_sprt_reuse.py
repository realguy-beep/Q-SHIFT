"""Replays saved SPRT and logical streams under longer profile-stable dwell horizons."""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from adaptive_basis_sprt import PROFILES, sample_scores
from adaptive_basis_sprt_end_to_end import classifier_choices, logical_failures

HERE = Path(__file__).resolve().parent
WINDOWS = 2_500
BLOCK = 100
HORIZONS = (1, 10, 100)
BOOTSTRAPS = 5_000
BOOT_SEED = 2026115791


def main() -> None:
    started = time.perf_counter()
    frozen = json.loads((HERE / "adaptive_basis_sprt_results.json").read_text())
    rep = json.loads((HERE / "adaptive_basis_sprt_replication_results.json").read_text())
    end = json.loads((HERE / "adaptive_basis_sprt_end_to_end_results.json").read_text())
    calibration, logical = {}, {}
    calibration_reproduction = []
    logical_reproduction = []

    for row in rep["sample_rows"]:
        scores, _, _ = sample_scores(row["profile"], WINDOWS * 500, row["seed"])
        calibration[row["profile"]] = classifier_choices(scores, row["profile"])
        calibration_reproduction.append({"profile": row["profile"], "seed": row["seed"], "samples_reused": WINDOWS * 500})

    seed_map = {(row["profile"], row["basis"]): row["seed"] for row in end["logical_samples"]}
    logical_meta = {}
    for profile in PROFILES:
        for basis in ("x", "z"):
            fail_blocks, meta, _ = logical_failures(profile, basis, WINDOWS * BLOCK, seed_map[profile, basis])
            logical[profile, basis] = fail_blocks
            logical_meta[f"{profile}_{basis}"] = {"seed": seed_map[profile, basis], "samples_reused": WINDOWS * BLOCK, "failures": int(fail_blocks.sum())}

    names = ["sprt"] + [f"lda_{n}" for n in (25, 100, 500)] + [f"gaussian_llr_{n}" for n in (25, 100, 500)] + ["static_x", "static_z", "oracle"]
    rng = np.random.default_rng(BOOT_SEED)
    summaries = []
    total_blocks_per_profile = WINDOWS
    for horizon in HORIZONS:
        group_n = total_blocks_per_profile // horizon
        if total_blocks_per_profile % horizon:
            raise RuntimeError("horizon must divide the saved window count")
        starts = np.arange(group_n) * horizon
        policy_failures = {}
        calibration_costs = {}
        calibration_group_costs = {}
        selection_errors = {}
        for name in names:
            policy_failures[name] = {}
            calibration_costs[name] = 0
            calibration_group_costs[name] = {}
            selection_errors[name] = {}
            for profile in PROFILES:
                if name == "static_x":
                    decisions = np.ones(group_n, dtype=bool)
                elif name == "static_z":
                    decisions = np.zeros(group_n, dtype=bool)
                elif name == "oracle":
                    decisions = np.full(group_n, profile == "x_biased", dtype=bool)
                else:
                    choices, consumed = calibration[profile]
                    decisions = choices[name][starts]
                    if name == "sprt":
                        calibration_costs[name] += int(consumed[starts].sum())
                    else:
                        budget = int(name.rsplit("_", 1)[1])
                        calibration_costs[name] += budget * group_n
                        calibration_group_costs[name][profile] = np.full(group_n, budget, dtype=np.int64)
                if name == "sprt":
                    calibration_group_costs[name][profile] = consumed[starts].astype(np.int64)
                if name in ("static_x", "static_z", "oracle"):
                    calibration_group_costs[name][profile] = np.zeros(group_n, dtype=np.int64)
                selection_errors[name][profile] = int(np.count_nonzero(decisions != (profile == "x_biased")))
                xf = logical[profile, "x"].reshape(group_n, horizon)
                zf = logical[profile, "z"].reshape(group_n, horizon)
                policy_failures[name][profile] = np.where(decisions[:, None], xf, zf).sum(axis=1).astype(np.int64)

        # Grouping the fixed saved windows changes calibration cadence, not the
        # number of logical attempts represented by those windows.
        attempts = len(PROFILES) * WINDOWS * BLOCK
        static_z_ler = sum(policy_failures["static_z"][p].sum() for p in PROFILES) / attempts
        for name in names:
            total_fail = int(sum(policy_failures[name][p].sum() for p in PROFILES))
            total_cal = calibration_costs[name]
            boot_fail = np.zeros(BOOTSTRAPS, dtype=np.int64)
            boot_static = np.zeros(BOOTSTRAPS, dtype=np.int64)
            boot_cal = np.zeros(BOOTSTRAPS, dtype=np.int64)
            for profile in PROFILES:
                a = policy_failures[name][profile]
                b = policy_failures["static_z"][profile]
                index = rng.integers(0, group_n, size=(BOOTSTRAPS, group_n))
                boot_fail += a[index].sum(axis=1)
                boot_static += b[index].sum(axis=1)
                boot_cal += calibration_group_costs[name][profile][index].sum(axis=1)
            delta = (boot_fail - boot_static) / attempts
            yield_delta = (attempts - boot_fail) / (attempts + boot_cal) - (attempts - boot_static) / attempts
            summaries.append(
                {
                    "logical_attempts_per_profile": WINDOWS * horizon * BLOCK,
                    "reuse_horizon_blocks": horizon,
                    "dwell_logical_attempts": horizon * BLOCK,
                    "policy": name,
                    "logical_failures": total_fail,
                    "ler": total_fail / attempts,
                    "calibration_shots": total_cal,
                    "correct_outputs_per_logical_plus_calibration_circuit_shot": (attempts - total_fail) / (attempts + total_cal),
                    "paired_group_bootstrap_ler_delta_vs_static_z_95_ci": [float(np.quantile(delta, 0.025)), float(np.quantile(delta, 0.975))],
                    "paired_group_bootstrap_throughput_delta_vs_static_z_95_ci": [float(np.quantile(yield_delta, 0.025)), float(np.quantile(yield_delta, 0.975))],
                    "profile_failures": {p: int(policy_failures[name][p].sum()) for p in PROFILES},
                    "profile_selection_errors": selection_errors[name],
                }
            )

    output = {
        "status": "sprt_stable_profile_reuse_replay",
        "horizons_blocks_of_100_attempts": list(HORIZONS),
        "profile_reuse_assumption": "profile remains stable for the full dwell; no change-point observations",
        "calibration_streams_reused": calibration_reproduction,
        "logical_streams_reused": logical_meta,
        "summary": summaries,
        "bootstrap_replicates": BOOTSTRAPS,
        "bootstrap_seed": BOOT_SEED,
        "elapsed_seconds": time.perf_counter() - started,
        "new_stochastic_samples": 0,
        "scope": "deterministic reuse-horizon reanalysis; not temporal robustness or hardware validation",
    }
    target = HERE / "adaptive_basis_sprt_reuse_results.json"
    target.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"status": output["status"], "rows": len(summaries), "output": str(target)}, indent=2))


if __name__ == "__main__":
    main()
