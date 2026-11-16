"""Sampler-free V1.6b preflight. Writes PREFLIGHT.json; never opens the sealed hidden burst.

Checks environment and seeds; runs the fake-sampler rehearsal (decoy hidden support); and
projects runtime by timing every arm on 2,000 already-exposed V1.2 detector rows. Because
the hidden support is sealed, the hidden condition is projected with the SLOWEST exact
decoder over all 15 signature classes x both logical effects.
Usage: preflight.py <V1.2 pilot_runs/attempt_001>
"""
from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m  # noqa: E402
from outputs.qshift_correlated_decoder_v1_6 import learner as L  # noqa: E402
from outputs.qshift_correlated_decoder_v1_6b import contract as K  # noqa: E402
from outputs.qshift_correlated_decoder_v1_6b.common import CONFIG_PATH, atomic_json, load_json, sha256_file  # noqa: E402
from outputs.qshift_correlated_decoder_v1_6b.rehearsal import rehearse  # noqa: E402
from outputs.qshift_correlated_decoder_v1_6b.run_eval import (  # noqa: E402
    INVENTORY_PATH, PREFLIGHT_PATH, SPEC, _exact, _matcher, check_environment, check_inventory)


def time_decoder(fn, rows) -> float:
    t = time.perf_counter()
    fn(rows)
    return (time.perf_counter() - t) / len(rows)


def main() -> None:
    v12 = Path(sys.argv[1]).resolve()
    config = load_json(CONFIG_PATH)
    env = check_environment(config)
    check_inventory(load_json(INVENTORY_PATH))
    with np.load(v12 / "evaluation" / "eval_q2_r00.npz", allow_pickle=False) as z:
        rows = np.asarray(z["detectors"][:2000], dtype=np.uint8)
    classes = L.signature_classes()
    widths = {}
    for i, c in enumerate(classes):
        for flip in (0, 1):
            widths[(i, flip)] = _exact(c.representative(flip), 0.02).max_width
    worst = max(widths, key=widths.get)
    known_support = K.KNOWN_SUPPORT
    exact_known = time_decoder(lambda x: _exact(known_support, 0.02).decode(x, batch=256), rows)
    exact_worst = time_decoder(lambda x: _exact(classes[worst[0]].representative(worst[1]), 0.02).decode(x, batch=256), rows)
    am = _matcher(known_support, K.STATIC_MATCHING_Q)
    matching = time_decoder(lambda x: [am.decode_batch(x, enable_correlations=c) for c in (False, True, True)], rows)
    five = m.FiveFactorDecoder(m.build_matching(m.build_decomposed_dem(m.build_base_circuit(SPEC))),
                               m.extract_burst_events(SPEC, known_support), SPEC.detectors, correlations=False)
    five_t = time_decoder(lambda x: five.decode_rows(x, {"x": K.BOFFSTATIC_Q}), rows)
    started = time.perf_counter()
    with tempfile.TemporaryDirectory() as temp:
        rehearsal = rehearse(Path(temp))
    rehearsal_seconds = time.perf_counter() - started
    per_cond = K.FROZEN_ALLOCATION.eval_shots_per_condition
    projected = {"known": per_cond * (matching + five_t + 2 * exact_known),
                 "hidden_worst_case": per_cond * (matching + five_t + 2 * exact_worst)}
    allowance = 300.0  # device learning (exact flip stage), builds, sampling, archives, analysis
    total = sum(projected.values()) + allowance
    cap = config["resource_limits"]["wall_seconds"]
    limit = cap * config["resource_limits"]["preflight_projection_max_fraction_of_cap"]
    record = {
        "schema": "qshift-correlated-decoder-v1.6b-preflight-v1", "status": "PASS" if total <= limit else "FAIL_RUNTIME_PROJECTION",
        "sampler_calls": 0, "hidden_burst_opened": False, "environment": env,
        "seed_inventory_sha256": sha256_file(INVENTORY_PATH),
        "exact_width_by_class_and_flip": {f"{i}:{f}": w for (i, f), w in sorted(widths.items())},
        "worst_case_class_flip": list(worst), "worst_case_width": widths[worst],
        "rehearsal": {"state": "completed", "seconds": rehearsal_seconds, "decoy_hidden_support": [1, 12],
                      "learned": {c: rehearsal["conditions"][c]["learned"] for c in K.CONDITIONS},
                      "sampler": "exact-DEM numpy draws; not evidence"},
        "runtime_projection": {"fixture": "V1.2 eval_q2_r00.npz first 2,000 detector rows (already exposed)",
                               "seconds_per_shot": {"exact_known": exact_known, "exact_worst_case": exact_worst,
                                                    "three_matching_arms": matching, "five_factor": five_t},
                               "projected_seconds": projected, "allowance_seconds": allowance,
                               "projected_total_seconds": total, "cap_seconds": cap, "required_max_seconds": limit,
                               "within_cap": total <= limit, "note": "timing projection only; no performance claim"},
    }
    atomic_json(PREFLIGHT_PATH, record)
    print({"status": record["status"], "projected_total_seconds": round(total), "required_max": limit,
           "worst_width": widths[worst], "known_width": _exact(known_support, 0.02).max_width})


if __name__ == "__main__":
    main()
