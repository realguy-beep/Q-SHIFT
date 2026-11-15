"""Sampler-free V1.3 preflight. Writes PREFLIGHT.json; never calls a Stim sampler.

Checks environment, V1 training-archive reuse, estimator refit, seeds and the
static selection; runs the fake-sampler end-to-end rehearsal with the real
estimator; and projects evaluation runtime by timing all eight arms on 2,000
already-exposed V1.2 selection-set detector rows (detectors only).
"""
from __future__ import annotations

import argparse
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402

from outputs.qshift_correlated_decoder_feasibility_v1_1.model import (  # noqa: E402
    build_base_circuit,
    build_candidate_circuit,
    build_decomposed_dem,
    build_matching,
    extract_burst_events,
)
from outputs.qshift_correlated_decoder_v1_3 import contract as K  # noqa: E402
from outputs.qshift_correlated_decoder_v1_3.common import (  # noqa: E402
    CONFIG_PATH,
    atomic_json,
    fit_frozen_estimator,
    load_detectors_only,
    load_json,
    sha256_file,
)
from outputs.qshift_correlated_decoder_v1_3.multi_prior import ModeAwareFiveFactor  # noqa: E402
from outputs.qshift_correlated_decoder_v1_3.rehearsal import REHEARSAL_ALLOCATION, rehearse  # noqa: E402
from outputs.qshift_correlated_decoder_v1_3.run_eval import (  # noqa: E402
    INVENTORY_PATH,
    PREFLIGHT_PATH,
    SELECTION_PATH,
    check_environment,
    check_inventory,
    check_v1_reuse,
)


def time_arms(rows: np.ndarray, selection: dict) -> dict:
    """Time all eight arms on fixture rows (worst case: every five-factor prior nonzero)."""
    sel = selection["selected"]
    base = build_matching(build_decomposed_dem(build_base_circuit()))
    t = time.perf_counter()
    matchings = [(build_matching(build_decomposed_dem(build_candidate_circuit(sel[K.SEL_ASTAR]["q"]))),
                  sel[K.SEL_ASTAR]["correlations"]),
                 (build_matching(build_decomposed_dem(build_candidate_circuit(sel[K.SEL_ASTAR_ALT]["q"]))),
                  sel[K.SEL_ASTAR_ALT]["correlations"]),
                 (build_matching(build_decomposed_dem(build_candidate_circuit(0.0195))), True)]
    build_seconds = time.perf_counter() - t
    t = time.perf_counter()
    for m, c in matchings:  # Astar, AstarAlt, A2sw (ON branch)
        m.decode_batch(rows, enable_correlations=c)
    matching_seconds = time.perf_counter() - t
    events = extract_burst_events()
    boff_q = max(float(sel[K.SEL_BOFFSTATIC_Q]), 0.00125)  # force the slower nonzero path
    t = time.perf_counter()
    ModeAwareFiveFactor(base, events, correlations=True).decode_rows(
        rows, {"B": 0.0195, "Bstatic": K.V1_2_BSTATIC_Q})
    ModeAwareFiveFactor(base, events, correlations=False).decode_rows(
        rows, {"Boff": 0.0195, "BoffStatic": boff_q, "Coff": 0.02})
    five_seconds = time.perf_counter() - t
    return {"rows": len(rows), "matching_three_arms_seconds": matching_seconds,
            "five_factor_two_families_seconds": five_seconds, "three_matching_builds_seconds": build_seconds}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v1-repo", type=Path, required=True)
    parser.add_argument("--v1-2-run", type=Path, required=True, help="V1.2 pilot_runs/attempt_001 (read-only)")
    args = parser.parse_args()
    config = load_json(CONFIG_PATH)
    env = check_environment(config)
    reuse = check_v1_reuse(args.v1_repo)
    estimator = fit_frozen_estimator(args.v1_repo, config)
    inventory = load_json(INVENTORY_PATH)
    check_inventory(inventory)
    selection = load_json(SELECTION_PATH)

    started = time.perf_counter()
    with tempfile.TemporaryDirectory() as temp:
        rehearsal_result = rehearse(Path(temp), estimator)
        rehearsal_status = load_json(Path(temp) / "rehearsal_run" / K.FILE_STATUS)
    rehearsal_seconds = time.perf_counter() - started
    if rehearsal_status["state"] != K.STATE_COMPLETED:
        raise RuntimeError("end-to-end rehearsal did not complete")

    timing_archive = args.v1_2_run.resolve() / "evaluation" / "eval_q2_r00.npz"
    if sha256_file(timing_archive) != selection["selection_set"]["archives"]["eval_q2_r00.npz"]:
        raise RuntimeError("timing fixture archive does not match the selection record")
    rows = load_detectors_only(timing_archive, 4000)[:2000]
    timing = time_arms(rows, selection)
    alloc = K.FROZEN_ALLOCATION
    per_shot = (timing["matching_three_arms_seconds"] + timing["five_factor_two_families_seconds"]) / timing["rows"]
    projected_eval = per_shot * alloc.eval_shots
    projected_builds = timing["three_matching_builds_seconds"] / 3 * (alloc.roots + 2)
    projected_other = 60.0  # sampling, archives, guard checks, analysis: conservative allowance
    projected_total = projected_eval + projected_builds + projected_other
    cap = config["resource_limits"]["wall_seconds"]
    limit = cap * config["resource_limits"]["preflight_projection_max_fraction_of_cap"]
    within = projected_total <= limit

    record = {
        "schema": "qshift-correlated-decoder-v1.3-preflight-v1",
        "status": "PASS" if within else "FAIL_RUNTIME_PROJECTION",
        "sampler_calls": 0,
        "environment": env,
        "v1_training_reuse_matches_v1_1_record": True,
        "v1_reuse_archive_count": reuse.get("archive_count"),
        "estimator": {"slope": estimator.slope, "intercept": estimator.intercept,
                      "matches_frozen_v1_1_fit": True},
        "seed_inventory_sha256": sha256_file(INVENTORY_PATH),
        "static_selection_sha256": sha256_file(SELECTION_PATH),
        "static_selection": selection["selected"],
        "rehearsal": {"allocation": REHEARSAL_ALLOCATION.as_dict(), "state": rehearsal_status["state"],
                      "seconds": rehearsal_seconds, "sampler": "deterministic numpy fake; not evidence",
                      "decision_on_fake_data_meaningless": rehearsal_result["decision"]},
        "runtime_projection": {
            "fixture": "V1.2 eval_q2_r00.npz first 2,000 detector rows (already-exposed selection data)",
            **timing, "per_shot_all_arms_seconds": per_shot,
            "projected_evaluation_inference_seconds": projected_eval,
            "projected_model_build_seconds": projected_builds,
            "allowance_other_seconds": projected_other,
            "projected_total_seconds": projected_total,
            "cap_seconds": cap, "required_max_seconds": limit, "within_cap": within,
            "note": "timing projection only; no statistical or performance claim",
        },
    }
    atomic_json(PREFLIGHT_PATH, record)
    print({"status": record["status"], "projected_total_seconds": round(projected_total, 1),
           "required_max_seconds": limit, "rehearsal": rehearsal_status["state"]})


if __name__ == "__main__":
    main()
