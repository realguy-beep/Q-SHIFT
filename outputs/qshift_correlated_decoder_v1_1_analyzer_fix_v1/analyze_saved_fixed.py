"""Fixed copy of the frozen V1.1 saved-array analyzer; imports no runner code.

Derived from outputs/qshift_correlated_decoder_feasibility_v1_1/analyze_saved.py
(SHA-256 d6720b879cbef01f9c9a62ad103e930e5214129c615c4b0ade5e202320296239), which is
left unmodified. Changes, and nothing else:
  1. read the model-metadata key the frozen runner actually writes (A_global_qhat);
  2. validate model/calibration metadata before writing any output file;
  3. optional output_dir so analysis need not write into a preserved run directory.
Scoring, bootstrap, seeds and decision rules are unchanged from the frozen logic.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
# The frozen V1.1 package supplies the seed inventory; it is read, never written.
V1_1_PACKAGE = ROOT.parent / "qshift_correlated_decoder_feasibility_v1_1"
QS = (0.0, 0.01, 0.02)
ARMS = ("A", "A2", "B", "C")
N_ROOTS = 10
SHOTS_PER_ROOT = 2000
BOOTSTRAPS = 20000
# Must match the key run_eval.py writes into models_frozen.json. V1.1 attempt_001
# failed with KeyError because the frozen analyzer requested "global_A_qhat".
MODELS_GLOBAL_QHAT_KEY = "A_global_qhat"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def binary_matrix(a, name: str, expected_rows: int) -> np.ndarray:
    x = np.asarray(a)
    if x.shape != (expected_rows, 1) or not np.isin(x, [0, 1]).all():
        raise ValueError(f"{name} is not a binary [{expected_rows},1] matrix")
    return x.astype(np.uint8, copy=False)


def analyze(run_dir: Path, output_dir: Path | None = None) -> dict:
    output_dir = run_dir if output_dir is None else output_dir
    status = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
    identity = json.loads((run_dir / "execution_identity.json").read_text(encoding="utf-8"))
    inventory = json.loads((V1_1_PACKAGE / "seed_inventory.json").read_text(encoding="utf-8"))
    if status.get("state") != "evaluation_complete_pending_independent_analysis":
        raise ValueError("runner status is not analysis-ready")
    calls = status.get("sampler_calls_started", [])
    if len(calls) != 30 or any(call.get("state") != "committed" for call in calls):
        raise ValueError("expected exactly 30 committed evaluation calls")
    if status.get("shots_started") != 60000 or status.get("shots_committed") != 60000:
        raise ValueError("evaluation shot count is not exactly 60,000")
    if identity.get("evaluation_labels_exposed_to_decoders") is not False:
        raise ValueError("identity record does not certify the detector-only decoder boundary")
    # Validate metadata before writing anything, so an interface mismatch cannot leave
    # a partial paired_results.csv without analysis.json (the attempt_001 failure mode).
    models = json.loads((run_dir / "models_frozen.json").read_text(encoding="utf-8"))
    calibration = json.loads((run_dir / "calibration_diagnostics.json").read_text(encoding="utf-8"))
    if MODELS_GLOBAL_QHAT_KEY not in models:
        raise ValueError(f"models_frozen.json lacks required key {MODELS_GLOBAL_QHAT_KEY!r}")
    global_a_qhat = float(models[MODELS_GLOBAL_QHAT_KEY])
    if "estimation_summary" not in calibration:
        raise ValueError("calibration_diagnostics.json lacks estimation_summary")

    expected_call_keys = {
        f"evaluation:q{q:.2f}:root{root:02d}" for q in QS for root in range(N_ROOTS)
    }
    call_by_key = {call.get("key"): call for call in calls}
    if set(call_by_key) != expected_call_keys:
        raise ValueError("evaluation call/root inventory is incomplete or duplicated")
    sample_ids = [call.get("sample_id") for call in calls]
    if any(not isinstance(value, str) or len(value) != 64 for value in sample_ids) or len(set(sample_ids)) != 30:
        raise ValueError("evaluation sample IDs are missing or duplicated")
    used_seeds = [int(call["seed"]) for call in calls]
    expected_seeds = [int(inventory["seeds"][key]) for key in sorted(expected_call_keys)]
    if sorted(used_seeds) != sorted(expected_seeds) or len(set(used_seeds)) != 30:
        raise ValueError("evaluation seed-to-root mapping mismatch")

    per_condition = {}
    all_archive_hashes = {}
    totals = {arm: {"errors": 0, "shots": 0} for arm in ARMS}
    root_diffs = {q: [] for q in QS}
    csv_rows = []
    evaluation_dir = run_dir / "evaluation"
    for qi, q in enumerate(QS):
        condition_rows = []
        for ri in range(N_ROOTS):
            key = f"evaluation:q{q:.2f}:root{ri:02d}"
            call = call_by_key[key]
            path = evaluation_dir / f"eval_q{qi}_r{ri:02d}.npz"
            if not path.is_file():
                raise ValueError(f"missing paired root archive {path.name}")
            if call.get("archive") != f"evaluation/{path.name}" or call.get("shots") != SHOTS_PER_ROOT:
                raise ValueError(f"root archive allocation identity mismatch for {path.name}")
            file_hash = digest(path)
            if call.get("archive_sha256") != file_hash or call.get("archive_bytes") != path.stat().st_size:
                raise ValueError(f"archive identity mismatch for {path.name}")
            all_archive_hashes[path.name] = file_hash
            with np.load(path, allow_pickle=False) as archive:
                required = {"detectors", "observables", *(f"pred_{arm}" for arm in ARMS)}
                if set(archive.files) != required:
                    raise ValueError(f"unexpected arrays in {path.name}")
                detectors = np.asarray(archive["detectors"])
                labels = binary_matrix(archive["observables"], "observable labels", SHOTS_PER_ROOT)
                predictions = {arm: binary_matrix(archive[f"pred_{arm}"], f"prediction {arm}", SHOTS_PER_ROOT)
                               for arm in ARMS}
            if detectors.shape != (SHOTS_PER_ROOT, 40) or not np.isin(detectors, [0, 1]).all():
                raise ValueError(f"detector array shape or alphabet mismatch for {path.name}")
            if detectors.dtype != np.uint8:
                raise ValueError(f"detector dtype mismatch for {path.name}")
            y = labels[:, 0]
            row = {"q": q, "root": ri, "shots": SHOTS_PER_ROOT,
                   "detector_sha256": hashlib.sha256(detectors.tobytes()).hexdigest()}
            error_bits = {}
            for arm in ARMS:
                err = predictions[arm][:, 0] != y
                error_bits[arm] = err
                count = int(err.sum())
                totals[arm]["errors"] += count
                totals[arm]["shots"] += SHOTS_PER_ROOT
                row[f"{arm}_errors"] = count
                row[f"{arm}_ler"] = count / SHOTS_PER_ROOT
            row["B_minus_A"] = row["B_ler"] - row["A_ler"]
            row["B_minus_A2"] = row["B_ler"] - row["A2_ler"]
            row["A_B_prediction_disagreements"] = int(np.count_nonzero(predictions["A"] != predictions["B"]))
            row["A2_B_prediction_disagreements"] = int(np.count_nonzero(predictions["A2"] != predictions["B"]))
            row["B_only_errors_vs_A"] = int(np.count_nonzero(error_bits["B"] & ~error_bits["A"]))
            row["A_only_errors_vs_B"] = int(np.count_nonzero(error_bits["A"] & ~error_bits["B"]))
            condition_rows.append(row)
            csv_rows.append(row)
            root_diffs[q].append(row["B_minus_A"])
        per_condition[str(q)] = condition_rows
    if len(all_archive_hashes) != 30:
        raise ValueError("paired evaluation archive set is not exactly 30 roots")
    if any(path.suffix == ".npz" for path in evaluation_dir.iterdir() if path.name not in all_archive_hashes):
        raise ValueError("unexpected unregistered evaluation archive")

    # Resample paired root-level differences; each condition retains its own root stratum.
    root_diff_arrays = {q: np.asarray(values, dtype=np.float64) for q, values in root_diffs.items()}
    rng = np.random.default_rng(int(inventory["seeds"]["statistics:primary-bootstrap"]))
    primary_boot = np.empty(BOOTSTRAPS, dtype=np.float64)
    condition_boot = {q: np.empty(BOOTSTRAPS, dtype=np.float64) for q in QS}
    for b in range(BOOTSTRAPS):
        for q in QS:
            idx = rng.integers(0, N_ROOTS, size=N_ROOTS)
            condition_boot[q][b] = float(root_diff_arrays[q][idx].mean())
        primary_boot[b] = float(np.mean([condition_boot[0.01][b], condition_boot[0.02][b]]))
    primary_estimate = float(np.mean([root_diff_arrays[0.01].mean(), root_diff_arrays[0.02].mean()]))
    primary_ci = np.quantile(primary_boot, [0.025, 0.975], method="linear").tolist()
    per_condition_ci = {str(q): np.quantile(condition_boot[q], [0.025, 0.975], method="linear").tolist()
                        for q in QS}
    zero_rng = np.random.default_rng(int(inventory["seeds"]["statistics:zero-bootstrap"]))
    zero_boot = np.asarray([
        root_diff_arrays[0.0][zero_rng.integers(0, N_ROOTS, size=N_ROOTS)].mean()
        for _ in range(BOOTSTRAPS)
    ])
    zero_bounds = np.quantile(zero_boot, [0.05, 0.95], method="linear").tolist()

    rates = {arm: totals[arm]["errors"] / totals[arm]["shots"] for arm in ARMS}
    nonzero_ler = {arm: float(np.mean([
        sum(row[f"{arm}_errors"] for row in per_condition[str(q)]) /
        sum(row["shots"] for row in per_condition[str(q)]) for q in (0.01, 0.02)
    ])) for arm in ARMS}
    a_nonzero_errors = sum(row["A_errors"] for q in (0.01, 0.02) for row in per_condition[str(q)])
    b_point_better_both = all(
        sum(row["B_errors"] for row in per_condition[str(q)]) <
        sum(row["A_errors"] for row in per_condition[str(q)]) for q in (0.01, 0.02)
    )
    if a_nonzero_errors >= 100 and primary_ci[1] < 0 and b_point_better_both and zero_bounds[1] < 0.0005:
        decision = "GO_DEVELOPMENT_ONLY"
    elif primary_ci[0] >= 0 or zero_bounds[0] > 0.0005:
        decision = "NO_GO"
    else:
        decision = "INCONCLUSIVE"

    output_dir.mkdir(parents=True, exist_ok=True)
    row_csv = output_dir / "paired_results.csv"
    with row_csv.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(csv_rows[0]))
        writer.writeheader()
        writer.writerows(csv_rows)
    result = {
        "schema": "qshift-correlated-decoder-v1.1-independent-analysis-v1-fixed-key",
        "evaluation_roots": 30,
        "evaluation_shots": 60000,
        "bootstrap_replicates": BOOTSTRAPS,
        "bootstrap_quantile_method": "linear",
        "primary_estimand_B_minus_A_equal_weight_q0_01_q0_02": primary_estimate,
        "primary_two_sided_95_percentile_ci": primary_ci,
        "per_condition_B_minus_A_ci": per_condition_ci,
        "q0_B_minus_A_bootstrap_5th_95th_percentiles": zero_bounds,
        "q0_harm_tolerance": 0.0005,
        "arm_totals": {arm: {**totals[arm], "ler": rates[arm]} for arm in ARMS},
        "equal_weight_nonzero_condition_ler": nonzero_ler,
        "relative_reduction_B_vs_A_descriptive": None if nonzero_ler["A"] == 0 else (nonzero_ler["A"] - nonzero_ler["B"]) / nonzero_ler["A"],
        "A_nonzero_error_count": a_nonzero_errors,
        "B_point_ler_lower_than_A_at_both_nonzero_q": b_point_better_both,
        "calibration_estimation_diagnostics": calibration["estimation_summary"],
        "A_global_qhat": global_a_qhat,
        "root_results": per_condition,
        "paired_archive_sha256": all_archive_hashes,
        "paired_results_csv_sha256": digest(row_csv),
        "decision": decision,
        "interpretation": "exploratory development evidence only; ten roots per condition and one synthetic noise mechanism do not support independent confirmation",
    }
    (output_dir / "analysis.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return result


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--output-dir", type=Path, default=None,
                        help="write paired_results.csv/analysis.json here instead of run_dir")
    args = parser.parse_args()
    out = None if args.output_dir is None else args.output_dir.resolve()
    result = analyze(args.run_dir.resolve(), out)
    print(json.dumps({key: result[key] for key in (
        "primary_estimand_B_minus_A_equal_weight_q0_01_q0_02",
        "primary_two_sided_95_percentile_ci", "q0_B_minus_A_bootstrap_5th_95th_percentiles",
        "decision", "arm_totals")}, indent=2))


if __name__ == "__main__":
    main()
