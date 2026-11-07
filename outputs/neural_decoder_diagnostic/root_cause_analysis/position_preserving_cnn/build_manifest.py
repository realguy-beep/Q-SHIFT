"""Write and verify the evidence manifest for the positional-CNN pilot."""
import hashlib
import json
import platform
import sys
from pathlib import Path

import numpy as np
import pymatching
import stim
import torch

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    metadata = {"python": sys.version, "python_executable": sys.executable,
                "platform": platform.platform(), "numpy": np.__version__,
                "torch": torch.__version__, "torch_cuda_build": torch.version.cuda,
                "cuda_available_when_recorded": torch.cuda.is_available(),
                "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
                "stim": stim.__version__, "pymatching": pymatching.__version__,
                "metadata_recorded_after_run": True}
    (OUT / "RUN_METADATA.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    local = []
    for path in sorted(OUT.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.name == "MANIFEST.json":
            continue
        local.append({"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path), "bytes": path.stat().st_size})
    external = [
        "dashboard/structured_decoder.py", "dashboard/structured_training.py", "dashboard/models.py",
        "dashboard/simulator.py", "dashboard/tests/test_structured_training.py",
        "dashboard/tests/test_position_preserving_decoder.py",
        "outputs/phase2b_pauli_bias/noise_model.py", "outputs/phase2b_pauli_bias/decoder_bank.py",
        "outputs/phase2b_pauli_bias/PHASE2B_PROTOCOL.md", "outputs/phase2b_pauli_bias/CALIBRATION_SELECTION.json",
        "outputs/neural_decoder_diagnostic/root_cause_analysis/POSITIONAL_CNN_REPORT.md",
    ]
    inputs = [{"path": rel, "sha256": sha(ROOT / rel), "bytes": (ROOT / rel).stat().st_size} for rel in external]
    manifest = {"status": "verified", "scope": "position-preserving CNN development pilot; no independent test data",
                "pre_sampling_freeze_sha256": sha(OUT / "freeze.json"),
                "frozen_execution_runner_sha256": json.loads((OUT / "freeze.json").read_text(encoding="utf-8"))["source_sha256"][
                    "outputs/neural_decoder_diagnostic/root_cause_analysis/position_preserving_cnn/run_experiment.py"],
                "local_files": local, "external_source_inputs": inputs}
    path = OUT / "MANIFEST.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    failures = [item["path"] for item in local + inputs if sha(ROOT / item["path"]) != item["sha256"]]
    if failures:
        raise SystemExit(f"Manifest verification failed: {failures}")
    print(json.dumps({"status": "PASS", "local_files": len(local), "external_source_inputs": len(inputs)}, indent=2))


if __name__ == "__main__":
    main()
