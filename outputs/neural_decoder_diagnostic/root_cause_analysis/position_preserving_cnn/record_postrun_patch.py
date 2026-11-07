"""Record the post-run CSV-only correction while retaining the frozen runner."""
import difflib
import hashlib
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    freeze = json.loads((OUT / "freeze.json").read_text(encoding="utf-8"))
    rel = "outputs/neural_decoder_diagnostic/root_cause_analysis/position_preserving_cnn/run_experiment.py"
    expected = freeze["source_sha256"][rel]
    frozen = OUT / "run_experiment_frozen.py"
    current = OUT / "run_experiment.py"
    if sha(frozen) != expected:
        raise RuntimeError("Frozen runner copy does not match the pre-sampling hash.")
    if sha(current) == expected:
        raise RuntimeError("No post-run source change detected; patch record is unnecessary.")
    old_text = frozen.read_text(encoding="utf-8").splitlines(keepends=True)
    new_text = current.read_text(encoding="utf-8").splitlines(keepends=True)
    diff = "".join(difflib.unified_diff(old_text, new_text,
        fromfile="run_experiment_frozen.py", tofile="run_experiment.py (report-only fix)"))
    (OUT / "REPORTING_ONLY_DIFF.txt").write_text(diff, encoding="utf-8")
    payload = {"status": "POST_RUN_REPORTING_ONLY_PATCH",
        "pre_sampling_runner_sha256": expected, "preserved_frozen_runner": "run_experiment_frozen.py",
        "preserved_frozen_runner_sha256": sha(frozen), "current_runner": "run_experiment.py",
        "current_runner_sha256": sha(current), "diff_sha256": sha(OUT / "REPORTING_ONLY_DIFF.txt"),
        "scope": "Adds the already-computed aggregate paired LER difference as an explicit row field so the final CSV writer can serialize it.",
        "sampling_or_model_logic_changed": False, "historical_run_outputs_modified": False,
        "created_unix_after_completed_run": time.time()}
    (OUT / "POSTRUN_REPORTING_PATCH.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("status", "pre_sampling_runner_sha256", "current_runner_sha256",
                                              "diff_sha256", "sampling_or_model_logic_changed")}, indent=2))


if __name__ == "__main__": main()
