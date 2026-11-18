"""Model-based replay of basis adaptation under alternating X/Z profiles."""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
END_TO_END = json.loads((HERE / "adaptive_basis_end_to_end_results.json").read_text())
COST = json.loads((HERE / "adaptive_basis_cost_frontier.json").read_text())
POLICY = {(r["ratio"], r["profile"]): r for r in END_TO_END["condition_rows"] if r["kind"] == "policy"}
CONFUSION = {(r["ratio"], r["profile"], r["calibration_shots"]): r for r in COST["per_profile"]}
PROFILES = ("x_biased", "z_biased")
BLOCK_SHOTS = 100
HORIZON_SHOTS = 10_000_000
N_BLOCKS = HORIZON_SHOTS // BLOCK_SHOTS


def stable_profile(block: int, dwell_blocks: int) -> str:
    return PROFILES[(block // dwell_blocks) % 2]


def run_replay(ratio: float, calibration_shots: int, update_blocks: int, dwell_blocks: int) -> dict:
    fail_rate = {}
    prob_x = {}
    for profile in PROFILES:
        row = POLICY[(ratio, profile)]
        fail_rate[(profile, "x")] = sum(row["fixed_x_failures_by_window"]) / 100_000
        fail_rate[(profile, "z")] = sum(row["fixed_z_failures_by_window"]) / 100_000
        c = CONFUSION[(ratio, profile, calibration_shots)]
        prob_x[profile] = c["x_selected"] / 1000

    fail_expected = 0.0
    updates = 0
    block = 0
    while block < N_BLOCKS:
        profile_at_calibration = stable_profile(block, dwell_blocks)
        choose_x = prob_x[profile_at_calibration]
        stop = min(N_BLOCKS, block + update_blocks)
        fail_expected += sum(
            (choose_x * fail_rate[(stable_profile(i, dwell_blocks), "x")]
             + (1 - choose_x) * fail_rate[(stable_profile(i, dwell_blocks), "z")])
            * BLOCK_SHOTS
            for i in range(block, stop)
        )
        updates += 1
        block = stop

    static_ler = min(
        sum((fail_rate[(p, basis)] * (dwell_blocks * BLOCK_SHOTS)) for p in PROFILES)
        / (2 * dwell_blocks * BLOCK_SHOTS)
        for basis in ("x", "z")
    )
    adaptive_ler = fail_expected / HORIZON_SHOTS
    calibration_total = updates * calibration_shots
    adaptive_yield = (HORIZON_SHOTS - fail_expected) / (HORIZON_SHOTS + calibration_total)
    static_yield = 1 - static_ler
    return {
        "ratio": ratio,
        "calibration_shots": calibration_shots,
        "update_interval_logical_shots": update_blocks * BLOCK_SHOTS,
        "profile_dwell_logical_shots": dwell_blocks * BLOCK_SHOTS,
        "logical_attempts": HORIZON_SHOTS,
        "calibration_updates": updates,
        "calibration_overhead_shots": calibration_total,
        "adaptive_ler_per_logical_attempt": adaptive_ler,
        "best_static_ler_per_logical_attempt": static_ler,
        "relative_ler_reduction_vs_static": 1 - adaptive_ler / static_ler,
        "adaptive_correct_outputs_per_total_circuit_shot": adaptive_yield,
        "best_static_correct_outputs_per_circuit_shot": static_yield,
        "adaptive_to_static_throughput_ratio": adaptive_yield / static_yield,
        "confusion_x_choice_probability_by_current_profile": prob_x,
    }


def main() -> None:
    if END_TO_END["stochastic_circuit_shots"] < 1 or len(POLICY) != 6:
        raise RuntimeError("expected saved independent end-to-end data for all six profile/ratio cells")
    for ratio in (2.0, 5.0, 10.0):
        for profile in PROFILES:
            row = POLICY[(ratio, profile)]
            if len(row["fixed_x_failures_by_window"]) != 1000 or len(row["fixed_z_failures_by_window"]) != 1000:
                raise RuntimeError("logical outcomes do not contain the declared 1,000 batches/basis")

    # Stable-profile 500-shot replay should agree with the saved selector LER
    # to within 0.0004; calibration and logical streams are independent.
    for ratio in (2.0, 5.0, 10.0):
        expected = 0.0
        observed = 0.0
        for profile in PROFILES:
            row = POLICY[(ratio, profile)]
            px = CONFUSION[(ratio, profile, 500)]["x_selected"] / 1000
            lx = sum(row["fixed_x_failures_by_window"]) / 100_000
            lz = sum(row["fixed_z_failures_by_window"]) / 100_000
            expected += (px * lx + (1 - px) * lz) / 2
            observed += row["policy_failures"] / 200_000
        if abs(expected - observed) > 0.0004:
            raise RuntimeError(f"stable-profile replay mismatch for ratio {ratio}: {expected} vs {observed}")

    rows = [
        run_replay(ratio, cal, interval, dwell)
        for ratio in (2.0, 5.0, 10.0)
        for cal in (25, 100, 500)
        for interval in (1, 10, 100, 1000)
        for dwell in (1, 10, 100, 1000)
    ]
    out = {
        "status": "exploratory_model_based_temporal_replay",
        "source_streams": "existing adaptive_basis_end_to_end_results.json and adaptive_basis_cost_frontier.json; no new stochastic circuit samples",
        "classifier": "frozen d3 binary LDA; observed confusion rates applied at each scheduled update",
        "profile_process": "deterministic equal-dwell alternation between X- and Z-biased profiles",
        "distance": 3,
        "rounds": 5,
        "gate_and_measurement_p": 0.003,
        "bias_ratios": [2, 5, 10],
        "logical_block_shots": BLOCK_SHOTS,
        "horizon_logical_shots": HORIZON_SHOTS,
        "update_intervals_logical_blocks": [1, 10, 100, 1000],
        "dwell_logical_blocks": [1, 10, 100, 1000],
        "calibration_shot_budgets": [25, 100, 500],
        "calibration_outputs_assumed_useful": False,
        "stable_profile_replay_checks": "all ratios within 0.0004 LER of saved 500-shot policy result",
        "results": rows,
        "scope": "plug-in scenario projection only; not a causal change-point or device-drift test; classifier/error-rate uncertainty and nonstationarity are not modeled",
    }
    path = HERE / "temporal_basis_replay_results.json"
    path.write_text(json.dumps(out, indent=2) + "\n")
    print(f"Wrote {path}; {len(rows)} schedules; no new circuit samples")


if __name__ == "__main__":
    main()
