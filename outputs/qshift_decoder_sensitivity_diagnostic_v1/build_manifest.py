"""Build the explicit, non-self-referential diagnostic hash inventory."""
from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path

import numpy
import pymatching
import stim

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
SOURCE_PATHS = (
    "outputs/phase3a_correlated_noise_preflight/simulator.py",
    "outputs/qshift_performance_sprint_v1/config.json",
    "outputs/qshift_performance_sprint_v1/EXPERIMENT_PROTOCOL.md",
    "outputs/qshift_performance_sprint_v1/estimator.py",
    "outputs/qshift_performance_sprint_v1/run_pilot.py",
)
ARTIFACT_PATHS = (
    ".gitignore",
    "diagnostic.py",
    "build_manifest.py",
    "tests/test_diagnostic.py",
    "feature_pair_map.json",
    "diagnostic_results_v1_4.json",
    "DIAGNOSTIC_RESULTS.md",
    "FEATURE_SEPARATION.md",
    "DECODER_DECISION_SENSITIVITY.md",
    "NEXT_METHOD_RECOMMENDATION.md",
)


def sha256(path: Path) -> str:
    # All manifested files are UTF-8 text. Normalize only CRLF to the Git LF
    # representation so the inventory is stable across core.autocrlf settings.
    data = path.read_bytes().replace(b"\r\n", b"\n")
    if b"\r" in data:
        raise ValueError(f"unexpected lone carriage return in {path}")
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    results = json.loads((ROOT / "diagnostic_results_v1_4.json").read_text(encoding="utf-8"))
    manifest = {
        "schema": "qshift-decoder-sensitivity-evidence-manifest-v1",
        "analysis_source_commit": "3a3f1dd2a14769dea645045c2be4acc8c1ecf739",
        "text_hash_canonicalization": "SHA256 of UTF-8 bytes after CRLF-to-LF normalization; no other transformations",
        "source_inputs": [
            {"path": p, "sha256": sha256(REPO / p)} for p in SOURCE_PATHS
        ],
        "diagnostic_artifacts": [
            {"path": f"outputs/qshift_decoder_sensitivity_diagnostic_v1/{p}",
             "sha256": sha256(ROOT / p)} for p in ARTIFACT_PATHS
        ],
        "environment": {
            "python": platform.python_version(), "numpy": numpy.__version__,
            "stim": stim.__version__, "pymatching": pymatching.__version__,
        },
        "saved_array_identity": results["training_and_calibration_detector_array_hashes"],
        "evaluation_detector_row_hashes": {
            p: result["detector_rows_sha256"]
            for p, result in results["decoder_sensitivity"]["detector_only_prediction_disagreement"].items()
        },
        "input_identity_policy": {
            "training_and_calibration": "canonical array hashes; source archives are not copied",
            "evaluation": "hashes cover only concatenated detector-row bytes per condition; observable members and whole archives were not read for hashing",
            "absolute_sample_path_published": False,
            "seed_values_published": False,
        },
        "scope": {
            "stim_sampler_calls": 0, "new_samples": 0,
            "evaluation_observable_members_loaded": False,
            "logical_error_metrics_computed": False,
        },
        "manifest_self_hash": "excluded",
    }
    path = ROOT / "SOURCE_AND_DATA_MANIFEST.json"
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"wrote {path.name}")


if __name__ == "__main__":
    main()
