"""Sampler-free end-to-end rehearsal of the V1.2 runner -> analyzer -> manifest path.

Drives the exact `run_eval.run_pipeline` code with a deterministic fake sampler
(numpy RNG; no Stim sampler) at a reduced allocation. It exists to catch
interface defects like the V1.1 finalization KeyError before any real sampling.
Fake data carry no scientific meaning.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from outputs.qshift_correlated_decoder_feasibility_v1_1.model import extract_burst_events  # noqa: E402
from outputs.qshift_correlated_decoder_v1_2 import contract as K  # noqa: E402
from outputs.qshift_correlated_decoder_v1_2.common import load_json  # noqa: E402
from outputs.qshift_correlated_decoder_v1_2.run_eval import (  # noqa: E402
    INVENTORY_PATH,
    SELECTION_PATH,
    ResourceGuard,
    run_pipeline,
)

REHEARSAL_ALLOCATION = K.Allocation(roots_per_q=K.FROZEN_ALLOCATION.roots_per_q,
                                    eval_shots_per_root=40, calibration_shots_per_root=200)
LENIENT_LIMITS = {"wall_seconds": 3600, "sampled_peak_rss_bytes": 8 * 2**30,
                  "minimum_free_disk_bytes": 0, "maximum_run_artifact_bytes": 2**30}


def fake_sampler(burst_scale: float = 0.88, background_p: float = 0.01):
    """Background bit flips plus the five triple signatures at a rate rising with q."""
    events = extract_burst_events()

    def sample(qi: int, shots: int, seed: int):
        q = K.QS[qi]
        rng = np.random.default_rng(seed)
        det = (rng.random((shots, K.DETECTORS)) < background_p).astype(np.uint8)
        for event in events:
            hit = rng.random(shots) < min(1.0, burst_scale * q)
            det[np.ix_(hit, list(event.detector_ids))] ^= 1
        obs = (rng.random((shots, 1)) < 0.05).astype(np.uint8)
        return det, obs
    return sample


def rehearse(work_dir: Path, estimator, *, sampler=None, allocation: K.Allocation = REHEARSAL_ALLOCATION) -> dict:
    run_dir = Path(work_dir) / "rehearsal_run"
    run_dir.mkdir(parents=True, exist_ok=False)
    identity = {"schema": "qshift-correlated-decoder-v1.2-execution-identity-v1",
                "git_head": None, "mode": "REHEARSAL_FAKE_SAMPLER_NOT_EVIDENCE"}
    return run_pipeline(run_dir, allocation=allocation, sampler=sampler or fake_sampler(),
                        inventory=load_json(INVENTORY_PATH), estimator=estimator,
                        selection=load_json(SELECTION_PATH), selection_sha256="rehearsal",
                        identity=identity, guard=ResourceGuard(LENIENT_LIMITS, run_dir))


def main() -> None:
    import argparse
    from outputs.qshift_correlated_decoder_v1_2.common import CONFIG_PATH, fit_frozen_estimator
    parser = argparse.ArgumentParser()
    parser.add_argument("--v1-repo", type=Path, required=True)
    args = parser.parse_args()
    estimator = fit_frozen_estimator(args.v1_repo, load_json(CONFIG_PATH))
    with tempfile.TemporaryDirectory() as temp:
        result = rehearse(Path(temp), estimator)
        status = load_json(Path(temp) / "rehearsal_run" / K.FILE_STATUS)
    print(json.dumps({"status": status["state"], "decision_on_fake_data": result["decision"]}, indent=2))


if __name__ == "__main__":
    main()
