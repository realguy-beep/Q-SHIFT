"""Select the V1.2 static baselines (Astar, Bstatic) on the V1.1 evaluation arrays.

Sampler-free. Reads the committed V1.1 attempt_001 archives read-only after
verifying every archive hash against its status call journal, decodes them with
matching and five-factor decoders over a frozen q grid, and writes
STATIC_SELECTION.json. These arrays were already analyzed in V1.1; they are a
selection set only and are disjoint from every V1.2 evaluation seed.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from outputs.qshift_correlated_decoder_feasibility_v1_1.model import (  # noqa: E402
    build_base_circuit,
    build_candidate_circuit,
    build_decomposed_dem,
    build_matching,
    extract_burst_events,
)
from outputs.qshift_correlated_decoder_v1_2.common import (  # noqa: E402
    CONFIG_PATH,
    atomic_json,
    load_json,
    sha256_file,
)
from outputs.qshift_correlated_decoder_v1_2.contract import QS  # noqa: E402
from outputs.qshift_correlated_decoder_v1_2.multi_prior import MultiPriorFiveFactor  # noqa: E402

OUT_PATH = ROOT / "STATIC_SELECTION.json"
V1_1_ROOTS = 10
V1_1_SHOTS = 2000


def select_q(errors_by_q: dict[float, int]) -> float:
    """Minimum total errors (equal shots per condition => equal-weight mean); ties to smaller q."""
    if not errors_by_q:
        raise ValueError("empty selection grid")
    return min(errors_by_q, key=lambda q: (errors_by_q[q], q))


def load_selection_set(run_dir: Path):
    status = load_json(run_dir / "status.json")
    calls = status.get("sampler_calls_started", [])
    if len(calls) != 30 or any(c.get("state") != "committed" for c in calls):
        raise ValueError("V1.1 selection run does not have exactly 30 committed calls")
    by_key = {c["key"]: c for c in calls}
    data = {}
    for qi, q in enumerate(QS):
        for ri in range(V1_1_ROOTS):
            call = by_key[f"evaluation:q{q:.2f}:root{ri:02d}"]
            path = run_dir / "evaluation" / f"eval_q{qi}_r{ri:02d}.npz"
            if call.get("archive") != f"evaluation/{path.name}" or sha256_file(path) != call.get("archive_sha256"):
                raise ValueError(f"V1.1 archive identity mismatch: {path.name}")
            with np.load(path, allow_pickle=False) as archive:
                x = np.asarray(archive["detectors"], dtype=np.uint8)
                y = np.asarray(archive["observables"], dtype=np.uint8)
            if x.shape != (V1_1_SHOTS, 40) or y.shape != (V1_1_SHOTS, 1):
                raise ValueError(f"V1.1 archive shape mismatch: {path.name}")
            data[(qi, ri)] = (x, y[:, 0], call["archive_sha256"])
    return status, data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v1-1-run", type=Path, required=True,
                        help="path to V1.1 pilot_runs/attempt_001 (read-only)")
    args = parser.parse_args()
    run_dir = args.v1_1_run.resolve()
    if OUT_PATH.exists():
        raise FileExistsError("STATIC_SELECTION.json exists; selection is run once and never overwritten")
    config = load_json(CONFIG_PATH)
    before = {p.relative_to(run_dir).as_posix(): sha256_file(p) for p in sorted(run_dir.rglob("*")) if p.is_file()}
    models = load_json(run_dir / "models_frozen.json")
    pooled = float(models["A_global_qhat"])
    grid = sorted(set(float(q) for q in config["static_selection"]["grid"]) | {pooled})
    _, data = load_selection_set(run_dir)

    started = time.perf_counter()
    matchings = {q: build_matching(build_decomposed_dem(build_candidate_circuit(q))) for q in grid}
    five = MultiPriorFiveFactor(build_matching(build_decomposed_dem(build_base_circuit())), extract_burst_events())
    priors = {f"{q!r}": q for q in grid}
    matching_errors = {q: {str(c): 0 for c in QS} for q in grid}
    five_errors = {q: {str(c): 0 for c in QS} for q in grid}
    for (qi, _), (x, y, _) in sorted(data.items()):
        cond = str(QS[qi])
        for q in grid:
            pred = np.asarray(matchings[q].decode_batch(x, enable_correlations=True), dtype=np.uint8).reshape(-1)
            matching_errors[q][cond] += int(np.count_nonzero(pred != y))
        decoded = five.decode_rows(x, priors)
        for q in grid:
            five_errors[q][cond] += int(np.count_nonzero(decoded[f"{q!r}"][:, 0] != y))
    seconds = time.perf_counter() - started

    m_totals = {q: sum(v.values()) for q, v in matching_errors.items()}
    f_totals = {q: sum(v.values()) for q, v in five_errors.items()}
    astar = select_q(m_totals)
    bstatic = select_q(f_totals)
    shots_per_condition = V1_1_ROOTS * V1_1_SHOTS

    def table(errors):
        return [{"q": q, "errors_by_condition": errors[q],
                 "equal_weight_mean_ler": sum(errors[q].values()) / (len(QS) * shots_per_condition),
                 "max_condition_ler": max(errors[q].values()) / shots_per_condition}
                for q in grid]

    after = {p.relative_to(run_dir).as_posix(): sha256_file(p) for p in sorted(run_dir.rglob("*")) if p.is_file()}
    if before != after:
        raise RuntimeError("V1.1 selection run changed during selection")
    record = {
        "schema": "qshift-correlated-decoder-v1.2-static-selection-v1",
        "selection_set": {
            "path_role": "V1.1 pilot_runs/attempt_001 (read-only)",
            "archives": {f"eval_q{qi}_r{ri:02d}.npz": data[(qi, ri)][2] for (qi, ri) in sorted(data)},
            "shots": len(data) * V1_1_SHOTS,
            "files_unchanged_before_after": True,
            "file_count": len(before),
            "status": "already-exposed V1.1 evaluation data; labels read for selection only",
        },
        "grid": grid,
        "grid_extra_point_v1_1_pooled_qhat": pooled,
        "criterion": config["static_selection"]["criterion"],
        "matching": table(matching_errors),
        "five_factor": table(five_errors),
        "selected": {"Astar_static_q": astar, "Bstatic_static_q": bstatic},
        "minimax_descriptive": {
            "matching": min(grid, key=lambda q: (max(matching_errors[q].values()), q)),
            "five_factor": min(grid, key=lambda q: (max(five_errors[q].values()), q)),
        },
        "decode_seconds": seconds,
        "sampler_calls": 0,
        "v1_2_evaluation_data_accessed": False,
    }
    atomic_json(OUT_PATH, record)
    print({"Astar_static_q": astar, "Bstatic_static_q": bstatic, "seconds": round(seconds, 1),
           "matching_totals": {q: m_totals[q] for q in grid}, "five_factor_totals": {q: f_totals[q] for q in grid}})


if __name__ == "__main__":
    main()
