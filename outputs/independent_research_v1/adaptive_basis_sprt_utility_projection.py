"""Bootstrap plug-in utility frontier for stable-profile calibration reuse."""
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
HORIZONS = (100, 1_000, 10_000, 100_000)
BOOTSTRAPS = 5_000
SEED = 2026115891
POLICIES = ["sprt"] + [f"lda_{n}" for n in (25, 100, 500)] + [f"gaussian_llr_{n}" for n in (25, 100, 500)] + ["static_x", "static_z", "oracle"]


def main() -> None:
    started = time.perf_counter()
    replication = json.loads((HERE / "adaptive_basis_sprt_replication_results.json").read_text())
    end = json.loads((HERE / "adaptive_basis_sprt_end_to_end_results.json").read_text())
    cal_choices, cal_cost = {}, {}
    logical_ler = {}
    for row in replication["sample_rows"]:
        score, _, _ = sample_scores(row["profile"], WINDOWS * 500, row["seed"])
        cal_choices[row["profile"]], cal_cost[row["profile"]] = classifier_choices(score, row["profile"])
    logical_seeds = {(row["profile"], row["basis"]): row["seed"] for row in end["logical_samples"]}
    logical_fail_windows = {}
    for profile in PROFILES:
        for basis in ("x", "z"):
            failures, _, _ = logical_failures(profile, basis, WINDOWS * BLOCK, logical_seeds[profile, basis])
            logical_fail_windows[profile, basis] = failures
            logical_ler[profile, basis] = float(failures.mean() / BLOCK)

    rng = np.random.default_rng(SEED)
    calibration_indices = {p: rng.integers(0, WINDOWS, size=(BOOTSTRAPS, WINDOWS)) for p in PROFILES}
    logical_indices = {(p, b): rng.integers(0, WINDOWS, size=(BOOTSTRAPS, WINDOWS)) for p in PROFILES for b in ("x", "z")}
    summaries = []
    for dwell in HORIZONS:
        point_yield, point_ler, point_cal = {}, {}, {}
        boot_yields = {name: np.zeros(BOOTSTRAPS) for name in POLICIES}
        boot_lers = {name: np.zeros(BOOTSTRAPS) for name in POLICIES}
        for name in POLICIES:
            profile_rates, profile_costs = {}, {}
            boot_profile_rates = {}
            boot_profile_costs = {}
            for profile in PROFILES:
                x_ler = logical_ler[profile, "x"]
                z_ler = logical_ler[profile, "z"]
                if name == "static_x":
                    p_choose_x = 1.0
                    shots = 0.0
                    boot_px = np.ones(BOOTSTRAPS)
                    boot_shots = np.zeros(BOOTSTRAPS)
                elif name == "static_z":
                    p_choose_x = 0.0
                    shots = 0.0
                    boot_px = np.zeros(BOOTSTRAPS)
                    boot_shots = np.zeros(BOOTSTRAPS)
                elif name == "oracle":
                    p_choose_x = float(profile == "x_biased")
                    shots = 0.0
                    boot_px = np.full(BOOTSTRAPS, p_choose_x)
                    boot_shots = np.zeros(BOOTSTRAPS)
                else:
                    choices = cal_choices[profile]
                    consumed = cal_cost[profile]
                    p_choose_x = float(choices[name].mean())
                    shots = float(consumed.mean()) if name == "sprt" else float(name.rsplit("_", 1)[1])
                    idx = calibration_indices[profile]
                    boot_px = choices[name][idx].mean(axis=1)
                    if name == "sprt":
                        boot_shots = consumed[idx].mean(axis=1)
                    else:
                        boot_shots = np.full(BOOTSTRAPS, shots)
                profile_rates[profile] = p_choose_x * x_ler + (1 - p_choose_x) * z_ler
                profile_costs[profile] = shots

                ix = logical_indices[profile, "x"]
                iz = logical_indices[profile, "z"]
                boot_x_ler = logical_fail_windows[profile, "x"][ix].mean(axis=1) / BLOCK
                boot_z_ler = logical_fail_windows[profile, "z"][iz].mean(axis=1) / BLOCK
                boot_profile_rates[profile] = boot_px * boot_x_ler + (1 - boot_px) * boot_z_ler
                boot_profile_costs[profile] = boot_shots

            point_ler[name] = float(np.mean(list(profile_rates.values())))
            point_cal[name] = float(sum(profile_costs.values()))
            correct = sum(dwell * (1 - profile_rates[p]) for p in PROFILES)
            point_yield[name] = correct / (2 * dwell + point_cal[name])
            failures = sum(dwell * boot_profile_rates[p] for p in PROFILES)
            costs = sum(boot_profile_costs[p] for p in PROFILES)
            boot_yields[name] = (2 * dwell - failures) / (2 * dwell + costs)
            boot_lers[name] = failures / (2 * dwell)

        for name in POLICIES:
            delta = boot_yields[name] - boot_yields["static_z"]
            ler_delta = boot_lers[name] - boot_lers["static_z"]
            summaries.append(
                {
                    "logical_attempts_per_profile_dwell": dwell,
                    "policy": name,
                    "expected_equal_profile_ler": point_ler[name],
                    "mean_calibration_shots_per_two_profile_cycle": point_cal[name],
                    "expected_correct_outputs_per_total_circuit_shot": point_yield[name],
                    "bootstrap_95_ci_throughput_delta_vs_static_z": [float(np.quantile(delta, 0.025)), float(np.quantile(delta, 0.975))],
                    "bootstrap_95_ci_ler_delta_vs_static_z": [float(np.quantile(ler_delta, 0.025)), float(np.quantile(ler_delta, 0.975))],
                }
            )
    output = {
        "status": "stable_profile_utility_plugin_projection",
        "calibration_and_logical_streams_reused": True,
        "horizons": list(HORIZONS),
        "policies": POLICIES,
        "summary": summaries,
        "bootstrap_replicates": BOOTSTRAPS,
        "bootstrap_seed": SEED,
        "elapsed_seconds": time.perf_counter() - started,
        "new_stochastic_samples": 0,
        "scope": "expected stable-profile utility projection; no profile drift or direct long-dwell experiment",
    }
    path = HERE / "adaptive_basis_sprt_utility_projection_results.json"
    path.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"status": output["status"], "sprt_rows": [r for r in summaries if r["policy"] == "sprt"], "output": str(path)}, indent=2))


if __name__ == "__main__":
    main()
