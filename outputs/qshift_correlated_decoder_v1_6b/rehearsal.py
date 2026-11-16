"""Sampler-free end-to-end rehearsal of the V1.6b pipeline (fake sampler; not evidence).

Uses exact-DEM synthetic draws (numpy) for each condition, with a DECOY hidden support,
never the sealed one. Exercises device learning, freezing, all arms, analysis and manifest.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m  # noqa: E402
from outputs.qshift_correlated_decoder_v1_6b import contract as K  # noqa: E402
from outputs.qshift_correlated_decoder_v1_6b.common import load_json  # noqa: E402
from outputs.qshift_correlated_decoder_v1_6b.run_eval import INVENTORY_PATH, SPEC, ResourceGuard, run_pipeline  # noqa: E402
from outputs.qshift_v1_4b_decoder_optimality.mld import dem_mechanisms  # noqa: E402

DECOY_HIDDEN = (1, 12)   # a decoy for rehearsal only; NOT the sealed hidden support
REHEARSAL_ALLOCATION = K.Allocation(roots_per_q=K.FROZEN_ALLOCATION.roots_per_q, eval_shots_per_root=30,
                                    calibration_shots_per_root=300, device_detector_shots_per_q=3000,
                                    device_labeled_shots_per_q=300)
LENIENT = {"wall_seconds": 3600, "sampled_peak_rss_bytes": 8 * 2**30, "minimum_free_disk_bytes": 0,
           "maximum_run_artifact_bytes": 2**30}


def dem_sampler(supports: dict[str, tuple[int, ...]]):
    mechs = {(c, qi): dem_mechanisms(m.build_candidate_circuit(SPEC, q, supports[c]).detector_error_model(
        decompose_errors=False, approximate_disjoint_errors=True)) for c in K.CONDITIONS for qi, q in enumerate(K.QS)}

    def sample(c: str, qi: int, shots: int, seed: int):
        rng = np.random.default_rng(seed)
        x = np.zeros((shots, 40), dtype=np.uint8)
        y = np.zeros((shots, 1), dtype=np.uint8)
        for mm in mechs[(c, qi)]:
            fire = rng.random(shots) < mm.p
            if mm.detectors:
                x[np.ix_(fire, list(mm.detectors))] ^= 1
            if mm.logical:
                y[fire, 0] ^= 1
        return x, y
    return sample


def rehearse(work_dir: Path, *, supports: dict | None = None, allocation: K.Allocation = REHEARSAL_ALLOCATION) -> dict:
    supports = supports or {"known": K.KNOWN_SUPPORT, "hidden": DECOY_HIDDEN}
    run_dir = Path(work_dir) / "rehearsal_run"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_pipeline(run_dir, allocation=allocation, sampler=dem_sampler(supports), supports=supports,
                        inventory=load_json(INVENTORY_PATH),
                        identity={"git_head": None, "mode": "REHEARSAL_FAKE_SAMPLER_NOT_EVIDENCE"},
                        guard=ResourceGuard(LENIENT, run_dir))


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as temp:
        r = rehearse(Path(temp))
    print({"decision_on_fake_data": r["decision"], "target": r["target_endpoint"]["status"],
           "learned": {c: r["conditions"][c]["learned"] for c in K.CONDITIONS}})
