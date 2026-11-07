"""Read-only reproduction of the earlier categorical toy package."""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import stim
import pymatching
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / "outputs" / "categorical_decoder_feasibility"
sys.path.insert(0, str(OLD))

from categorical_reference import decoder_risk, exact_posterior  # noqa: E402
from run_toy_comparisons import evaluate  # noqa: E402
from toy_circuits import one_qubit_model, two_qubit_model  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    manifest = json.loads((OLD / "MANIFEST.json").read_text(encoding="utf-8"))
    checked = {}
    for rel, record in manifest["local_files"].items():
        path = OLD / rel
        actual = sha256(path)
        if actual != record["sha256"]:
            raise RuntimeError(f"old package hash mismatch: {rel}")
        checked[f"categorical_decoder_feasibility/{rel}"] = actual
    for rel, record in manifest["read_only_source_references"].items():
        path = ROOT / rel
        actual = sha256(path)
        if actual != record["sha256"]:
            raise RuntimeError(f"source reference hash mismatch: {rel}")
        checked[rel] = actual

    stored = json.loads((OLD / "TOY_RESULTS.json").read_text(encoding="utf-8"))
    recomputed = {
        "one_qubit": evaluate("one_qubit", one_qubit_model()),
        "two_qubit": evaluate("two_qubit", two_qubit_model()),
    }
    expected = {
        "one_qubit": {"exact": 0.002646, "off": 0.002646, "on": 0.002646},
        "two_qubit": {"exact": 0.060000, "off": 0.112800, "on": 0.112800},
    }
    for name, result in recomputed.items():
        risks = result["logical_error_probability_under_exact_channel"]
        values = {"exact": risks["exact_categorical_MAP"],
                  "off": risks["pymatching_approx_dem_correlation_disabled"],
                  "on": risks["pymatching_approx_dem_correlation_enabled"]}
        for key, target in expected[name].items():
            if not math.isclose(values[key], target, rel_tol=0, abs_tol=1e-12):
                raise AssertionError((name, key, values[key], target))
        if name == "two_qubit":
            row = result["syndrome_decisions"][3]
            if (row["exact_MAP_decision"], row["PyMatching_uncorrelated_decision"],
                    row["PyMatching_correlated_decision"]) != (1, 0, 0):
                raise AssertionError("syndrome-11 decision convention/result changed")
        old_risk = stored[name]["result"]["logical_error_probability_under_exact_channel"]
        for key, value in values.items():
            old_key = {"exact": "exact_categorical_MAP", "off": "pymatching_approx_dem_correlation_disabled",
                       "on": "pymatching_approx_dem_correlation_enabled"}[key]
            if not math.isclose(value, old_risk[old_key], rel_tol=0, abs_tol=1e-12):
                raise AssertionError(f"reproduction vs saved artifact mismatch: {name}/{key}")

    out = {
        "status": "PASS",
        "preserved_manifest_hashes_verified": len(checked),
        "software": {"python": sys.version.split()[0], "stim": stim.__version__,
                     "pymatching": pymatching.__version__, "numpy": np.__version__},
        "stored_historical_results_read_only": True,
        "stochastic_phase2b_shots_generated": 0,
        "deterministic_forced_fault_configurations_recomputed": 320,
        "results": recomputed,
    }
    (Path(__file__).resolve().parent / "BASELINE_REPRODUCTION.json").write_text(
        json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": out["status"], "hashes": len(checked),
                      "software": out["software"],
                      "one_qubit_risks": expected["one_qubit"],
                      "two_qubit_risks": expected["two_qubit"],
                      "syndrome_11_decisions": [1, 0, 0]}, indent=2))


if __name__ == "__main__":
    main()
