"""Fresh episode-cluster precision check for the frozen histogram CUSUM."""
from __future__ import annotations

import hashlib
import json
import platform
import resource
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
from adaptive_histogram_cusum import sample_scores
from adaptive_histogram_cusum_calibrated import events

H = float(json.loads((HERE / "adaptive_histogram_cusum_calibrated_results.json").read_text())
          ["threshold_calibration"]["threshold"])
EXPECTED_H = 8.5945561755
PROFILE = "z_biased"
MEASUREMENT_P = 0.006
EPISODES = 5_000
DWELL = 1_000
SEED = 2026111901
BOOTSTRAPS = 20_000
BOOTSTRAP_SEED = 2026111902
BATCH = 100


def main() -> None:
    if abs(H - EXPECTED_H) > 1e-9:
        raise RuntimeError(f"frozen threshold changed: {H}")
    started = time.perf_counter()
    scores, sample_seconds = sample_scores(PROFILE, MEASUREMENT_P, EPISODES * DWELL, SEED)
    truth = False  # z_biased
    counts = np.empty(EPISODES, dtype=np.int16)
    for episode in range(EPISODES):
        stream = scores[episode * DWELL:(episode + 1) * DWELL]
        counts[episode] = sum(int(state != truth) for _, state in events(stream, H))

    monitored = EPISODES * (DWELL - 100)
    point_rate = float(counts.sum()) * 100_000 / monitored
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    boot_rates = np.empty(BOOTSTRAPS, dtype=np.float64)
    for start in range(0, BOOTSTRAPS, BATCH):
        size = min(BATCH, BOOTSTRAPS - start)
        indices = rng.integers(0, EPISODES, size=(size, EPISODES), endpoint=False)
        boot_rates[start:start + size] = counts[indices].sum(axis=1) * 100_000 / monitored
    ci = np.quantile(boot_rates, [0.025, 0.975], method="linear")
    passed = bool(ci[1] <= 25.0)
    script_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result = {
        "status": "completed_frozen_threshold_large_validation",
        "profile": PROFILE,
        "measurement_probability": MEASUREMENT_P,
        "threshold": H,
        "episodes": EPISODES,
        "shots_per_episode": DWELL,
        "monitored_shots": monitored,
        "seed": SEED,
        "false_switches": int(counts.sum()),
        "episodes_with_false_switch": int(np.count_nonzero(counts)),
        "point_rate_per_100k_monitored_shots": point_rate,
        "cluster_bootstrap": {
            "resampling_unit": "whole 1000-shot episode",
            "replicates": BOOTSTRAPS,
            "analysis_seed": BOOTSTRAP_SEED,
            "percentile_95_interval_per_100k": [float(ci[0]), float(ci[1])],
        },
        "predeclared_upper_limit_per_100k": 25.0,
        "upper_interval_clears_limit": passed,
        "unique_detector_score_samples": int(len(scores)),
        "unique_qshift_circuit_samples": 0,
        "sample_generation_seconds": sample_seconds,
        "elapsed_seconds": time.perf_counter() - started,
        "peak_rss_kib": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        "software_versions": {"python": platform.python_version(), "numpy": np.__version__},
        "script_sha256": script_hash,
        "scope": "single fresh development validation of a frozen detector-only threshold; no retuning, transition test, or logical utility test",
    }
    target = HERE / "adaptive_histogram_cusum_large_validation_results.json"
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in (
        "false_switches", "episodes_with_false_switch", "point_rate_per_100k_monitored_shots",
        "cluster_bootstrap", "upper_interval_clears_limit", "elapsed_seconds",
        "peak_rss_kib", "unique_detector_score_samples")}, indent=2))


if __name__ == "__main__":
    main()
