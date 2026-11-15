"""Independent aggregation of locally saved paired pilot arrays."""
from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path
import numpy as np

Q_ORDER = (0.0, 0.01, 0.02)
ARMS = ("A", "A2", "B", "C")
BOOTSTRAPS = 20_000


def _binary(a, name):
    x = np.asarray(a)
    if x.ndim != 2 or x.shape[1] != 1 or not np.isin(x, [0, 1]).all():
        raise ValueError(f"{name} must be a binary [shots,1] array")
    return x.astype(np.uint8, copy=False)


def load_root(path: Path):
    with np.load(path, allow_pickle=False) as z:
        needed = {"detectors", "observables", *(f"pred_{arm}" for arm in ARMS)}
        if not needed.issubset(z.files):
            raise ValueError(f"{path.name}: missing array fields")
        detectors = np.asarray(z["detectors"])
        labels = _binary(z["observables"], "observables")
        if detectors.ndim != 2 or detectors.shape != (len(labels), 40):
            raise ValueError(f"{path.name}: detector/label shape mismatch")
        if not np.isin(detectors, [0, 1]).all():
            raise ValueError(f"{path.name}: nonbinary detectors")
        preds = {arm: _binary(z[f"pred_{arm}"], f"pred_{arm}") for arm in ARMS}
        if any(len(x) != len(labels) for x in preds.values()):
            raise ValueError(f"{path.name}: prediction/label shape mismatch")
        return detectors.astype(np.uint8, copy=False), labels, preds


def analyze_run(run_dir: Path, inventory: dict, *, bootstrap_replicates=BOOTSTRAPS):
    eval_dir = run_dir / "evaluation"
    roots = {q: [] for q in Q_ORDER}
    file_hashes = {}
    per_condition = {}
    root_diffs = {}
    totals = {arm: {"errors": 0, "shots": 0} for arm in ARMS}
    csv_rows = []
    for qi, q in enumerate(Q_ORDER):
        rows = []
        for root in range(10):
            path = eval_dir / f"eval_q{qi}_r{root:02d}.npz"
            if not path.is_file():
                raise ValueError(f"missing evaluation archive: {path.name}")
            raw = path.read_bytes()
            file_hashes[path.name] = hashlib.sha256(raw).hexdigest()
            detectors, labels, preds = load_root(path)
            if detectors.shape != (2000, 40) or labels.shape != (2000, 1):
                raise ValueError(f"{path.name}: wrong frozen evaluation allocation")
            item = {"root": root, "shots": len(labels), "labels": labels, "preds": preds,
                    "detector_sha256": hashlib.sha256(detectors.tobytes()).hexdigest()}
            roots[q].append(item)
            y = labels[:, 0]
            row = {"condition_q": q, "root": root, "shots": len(y),
                   "detector_sha256": item["detector_sha256"]}
            error_bits = {}
            for arm in ARMS:
                e = preds[arm][:, 0] != y
                error_bits[arm] = e
                n = int(e.sum())
                totals[arm]["errors"] += n
                totals[arm]["shots"] += len(y)
                row[f"{arm}_errors"] = n
                row[f"{arm}_ler"] = n / len(y)
            row["B_minus_A"] = row["B_ler"] - row["A_ler"]
            row["B_minus_A2"] = row["B_ler"] - row["A2_ler"]
            row["A_B_disagreements"] = int(np.count_nonzero(preds["A"] != preds["B"]))
            row["B_only_errors"] = int(np.count_nonzero(error_bits["B"] & ~error_bits["A"]))
            row["A_only_errors"] = int(np.count_nonzero(error_bits["A"] & ~error_bits["B"]))
            rows.append(row)
            csv_rows.append(row)
        per_condition[str(q)] = rows
        root_diffs[q] = np.asarray([row["B_minus_A"] for row in rows], dtype=np.float64)
    if len(file_hashes) != 30:
        raise ValueError("evaluation archive inventory is incomplete")

    rng = np.random.default_rng(inventory["seeds"]["statistics:primary-bootstrap"])
    boot_by_q = {q: np.empty(bootstrap_replicates, dtype=np.float64) for q in Q_ORDER}
    primary_boot = np.empty(bootstrap_replicates, dtype=np.float64)
    nonzero = (0.01, 0.02)
    for b in range(bootstrap_replicates):
        for q in Q_ORDER:
            indices = rng.integers(0, 10, size=10)
            boot_by_q[q][b] = float(root_diffs[q][indices].mean())
        primary_boot[b] = float(np.mean([boot_by_q[q][b] for q in nonzero]))
    primary = float(np.mean([root_diffs[q].mean() for q in nonzero]))
    primary_ci = np.quantile(primary_boot, [0.025, 0.975], method="linear").tolist()
    cond_ci = {str(q): np.quantile(boot_by_q[q], [0.025, 0.975], method="linear").tolist()
               for q in Q_ORDER}

    zrng = np.random.default_rng(inventory["seeds"]["statistics:zero-bootstrap"])
    q0_boot = np.asarray([root_diffs[0.0][zrng.integers(0, 10, size=10)].mean()
                          for _ in range(bootstrap_replicates)], dtype=np.float64)
    q0_bounds = np.quantile(q0_boot, [0.05, 0.95], method="linear").tolist()
    rates = {arm: totals[arm]["errors"] / totals[arm]["shots"] for arm in ARMS}
    equal_nonzero_ler = {arm: float(np.mean([
        sum(row[f"{arm}_errors"] for row in per_condition[str(q)]) /
        sum(row["shots"] for row in per_condition[str(q)]) for q in nonzero
    ])) for arm in ARMS}
    a_nonzero_errors = sum(sum(row["A_errors"] for row in per_condition[str(q)]) for q in nonzero)
    b_better_both = all(
        sum(row["B_errors"] for row in per_condition[str(q)]) <
        sum(row["A_errors"] for row in per_condition[str(q)]) for q in nonzero
    )
    calibration = json.loads((run_dir / "calibration" / "diagnostics.json").read_text(encoding="utf-8"))
    estimates = {}
    for qi, q in enumerate(Q_ORDER):
        values = np.asarray([calibration["per_root_qhat"][f"q{qi}_r{ri:02d}"] for ri in range(10)])
        estimates[str(q)] = {"mean_qhat": float(values.mean()), "bias": float(values.mean() - q),
                             "mae": float(np.abs(values - q).mean()), "root_qhat": values.tolist()}

    if a_nonzero_errors >= 100 and primary_ci[1] < 0 and b_better_both and q0_bounds[1] < 0.0005:
        decision = "GO_DEVELOPMENT_ONLY"
    elif primary_ci[0] >= 0 or q0_bounds[0] > 0.0005:
        decision = "NO_GO"
    else:
        decision = "INCONCLUSIVE"
    result = {
        "schema": "qshift-correlated-decoder-saved-array-analysis-v1",
        "bootstrap_replicates": bootstrap_replicates,
        "bootstrap_quantile_method": "linear",
        "primary_estimand_B_minus_A": primary,
        "primary_two_sided_95_percentile_ci": primary_ci,
        "condition_B_minus_A_two_sided_95_percentile_ci": cond_ci,
        "q0_B_minus_A_one_sided_95_percentile_bounds": {"lower_5th": q0_bounds[0], "upper_95th": q0_bounds[1]},
        "zero_burst_harm_tolerance": 0.0005,
        "arm_totals": {arm: {**totals[arm], "ler": rates[arm]} for arm in ARMS},
        "equal_weight_nonzero_condition_ler": equal_nonzero_ler,
        "A_nonzero_error_count": a_nonzero_errors,
        "B_point_ler_lower_than_A_in_each_nonzero_condition": b_better_both,
        "relative_reduction_B_vs_A": None if equal_nonzero_ler["A"] == 0 else (equal_nonzero_ler["A"] - equal_nonzero_ler["B"]) / equal_nonzero_ler["A"],
        "calibration_estimation_diagnostics": estimates,
        "global_A_q": json.loads((run_dir / "models_frozen.json").read_text(encoding="utf-8"))["global_A_q"],
        "per_condition_root_results": per_condition,
        "evaluation_archive_sha256": file_hashes,
        "decision": decision,
        "interpretation": "development feasibility only; ten roots/condition and a root percentile bootstrap are limited, not confirmatory inference",
    }
    csv_path = run_dir / "paired_results.csv"
    fields = list(csv_rows[0])
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(csv_rows)
    return result


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--inventory", type=Path, default=Path(__file__).with_name("seed_inventory.json"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    result = analyze_run(args.run_dir, inventory)
    target = args.output or (args.run_dir / "analysis.json")
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: result[k] for k in ("primary_estimand_B_minus_A", "primary_two_sided_95_percentile_ci", "q0_B_minus_A_one_sided_95_percentile_bounds", "decision")}, indent=2))


if __name__ == "__main__":
    main()
