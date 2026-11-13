from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pytest

from qshift_ns4a_v2_deterministic.protocol import CANDIDATE_IDS, CONDITIONS, selection_shots
from qshift_ns4a_v2_deterministic.sampling_guard import SamplingNotAuthorized, activate_sampling
from qshift_ns4a_v2_deterministic.seed_plan import (
    ANALYSIS_STREAMS, SeedInventoryError, required_root_keys, validate_seed_inventory,
)
from qshift_ns4a_v2_deterministic.selection import SelectionRootScore
from qshift_ns4a_v2_deterministic.selection_rank import selection_rank_bootstrap


def _all_tie_records():
    records = []
    for ci, condition in enumerate(CONDITIONS):
        for ri in range(8):
            records.append(SelectionRootScore(condition, ri, f"selection:{condition}:r{ri:02d}",
                selection_shots(ci, ri), {candidate: 0 for candidate in CANDIDATE_IDS}))
    return records


def test_selection_rank_bootstrap_preserves_candidate_pairing_and_reports_ties():
    result = selection_rank_bootstrap(_all_tie_records(), np.random.default_rng(88001))
    assert result["replicates"] == 20_000
    assert tuple(result["candidate_order"]) == CANDIDATE_IDS
    assert result["replicate_frequency_with_any_top_tie"] == 1.0
    assert result["top_score_tie_frequency"] == {candidate: 1.0 for candidate in CANDIDATE_IDS}
    # Stable deterministic order resolves ties, so the first candidate is rank
    # one in every replicate and all candidate score values are identical.
    assert result["top_rank_frequency"][CANDIDATE_IDS[0]] == 1.0
    assert all(score["numerator"] == 0 for score in result["observed_scores"].values())


def test_seed_plan_validates_fixture_inventory_without_allocating_any_seed_file():
    root_entries = []
    for i, (partition, condition, root_index) in enumerate(required_root_keys(), start=1):
        root_entries.append({"partition": partition, "condition_id": condition,
                             "root_index": root_index, "seed": i})
    analysis_entries = [{"stream": name, "seed": 1_000 + i} for i, name in enumerate(ANALYSIS_STREAMS)]
    fixture = {"status": "candidate_frozen", "numeric_seeds_allocated": True,
               "root_seeds": root_entries, "analysis_seeds": analysis_entries}
    result = validate_seed_inventory(fixture, historical_seeds=[9_999], historical_coverage_complete=True)
    assert result == {"selection_roots": 48, "evaluation_roots": 60,
                      "analysis_streams": 6, "total_unique_seed_values": 114,
                      "historical_values_screened": 1}
    duplicate = dict(fixture)
    duplicate["analysis_seeds"] = list(analysis_entries)
    duplicate["analysis_seeds"][0] = {"stream": ANALYSIS_STREAMS[0], "seed": 1}
    with pytest.raises(SeedInventoryError, match="duplicate seed"):
        validate_seed_inventory(duplicate, historical_seeds=[], historical_coverage_complete=True)
    with pytest.raises(SeedInventoryError, match="coverage is incomplete"):
        validate_seed_inventory(fixture, historical_seeds=[], historical_coverage_complete=False)
    with pytest.raises(SeedInventoryError, match="collide"):
        validate_seed_inventory(fixture, historical_seeds=[1], historical_coverage_complete=True)


def test_sampling_activation_is_fail_closed_and_test_sources_expose_no_sampler_api():
    with pytest.raises(SamplingNotAuthorized, match="unimplemented and unauthorized"):
        activate_sampling()
    package = Path(__file__).parents[1]
    forbidden_calls = {"compile_sampler", "compile_detector_sampler", "sample"}
    for path in [*package.glob("qshift_ns4a_v2_deterministic/*.py"), *package.glob("tests/*.py")]:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(alias.name != "stim" for alias in node.names), path
            if isinstance(node, ast.ImportFrom):
                assert node.module != "stim", path
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in forbidden_calls, (path, node.lineno, node.func.attr)
