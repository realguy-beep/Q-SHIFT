from __future__ import annotations

import numpy as np
import pytest

from qshift_ns4a_v2_deterministic.protocol import CONDITIONS, EVALUATION_ARMS
from qshift_ns4a_v2_deterministic.statistics import (
    SECONDARY_CONTRASTS, EvaluationRootCounts, StatisticsError, holm_adjust,
    leave_one_root_out, paired_root_differences, primary_bootstrap, primary_point_estimate,
    root_sign_flip, root_t_interval_sensitivity, secondary_sign_flip_holm,
    relative_error_reduction, validate_independent_rngs,
)


def _evaluation_records(delta_fn=None):
    delta_fn = delta_fn or (lambda c, r: (c - 2) + (r % 3) - 1)
    out = []
    for ci, condition in enumerate(CONDITIONS):
        for ri in range(10):
            base = 50 + ri
            delta = delta_fn(ci, ri)
            counts = {
                "nominal_ordinary_pymatching": base,
                "nominal_correlation_enabled_pymatching": base + 1,
                "pooled_selected_fixed_pymatching": base,
                "matched_selected_dem_pymatching_other_mode_control": base + 1,
                "beliefmatching_same_selected_dem": base + delta,
            }
            out.append(EvaluationRootCounts(condition, ri, f"evaluation:{condition}:r{ri:02d}", 4_000, counts))
    return out


def test_equal_condition_point_estimate_and_paired_root_differences():
    records = _evaluation_records(lambda c, r: c + r)
    delta = paired_root_differences(records, "beliefmatching_same_selected_dem", "pooled_selected_fixed_pymatching")
    expected = sum(np.mean([c + r for r in range(10)]) / 4_000 for c in range(6)) / 6
    assert np.isclose(primary_point_estimate(records), expected)
    assert np.allclose(delta, np.asarray([[c + r for r in range(10)] for c in range(6)]) / 4_000)


def test_primary_bootstrap_has_100k_linear_quantiles_and_preserves_paired_root_units():
    records = _evaluation_records(lambda c, r: (c - 2) * (r % 4))
    result = primary_bootstrap(records, np.random.default_rng(20261113))  # deterministic unit-test-only seed
    assert result.replicates == 100_000
    assert result.quantile_method == "linear"
    expected = np.quantile(result.bootstrap_distribution, [0.025, 0.975], method="linear")
    assert np.allclose((result.lower_95, result.upper_95), expected)
    scaled = result.bootstrap_distribution * 240_000
    assert np.allclose(scaled, np.rint(scaled), atol=1e-7)


def test_zero_errors_all_ties_and_relative_reduction_edge_case():
    records = _evaluation_records(lambda _c, _r: 0)
    for row in records:
        row.errors_by_arm["beliefmatching_same_selected_dem"] = 0
        row.errors_by_arm["pooled_selected_fixed_pymatching"] = 0
    result = primary_bootstrap(records, np.random.default_rng(20261114))
    assert result.point_estimate == 0
    assert (result.lower_95, result.upper_95) == (0, 0)
    sf = root_sign_flip(np.zeros((6, 10)), np.random.default_rng(20261115))
    assert sf.extreme_assignments == 100_000 and sf.p_value == 1.0
    assert root_t_interval_sensitivity(records)["status"].startswith("degenerate")
    assert relative_error_reduction(0.0, 0.0) is None
    assert relative_error_reduction(0.0, 0.1) == 1.0
    with pytest.raises(StatisticsError, match=r"in \[0,1\]"):
        relative_error_reduction(-0.1, 0.2)


def test_signflip_add_one_and_holm_exact_three_order():
    differences = np.ones((6, 10), dtype=np.float64) / 4_000
    result = root_sign_flip(differences, np.random.default_rng(77))
    assert result.assignments == 100_000 and result.two_sided and result.add_one
    assert result.p_value == (result.extreme_assignments + 1) / 100_001
    assert 0 < result.p_value <= 1
    raw = {SECONDARY_CONTRASTS[0]: 0.01, SECONDARY_CONTRASTS[1]: 0.04, SECONDARY_CONTRASTS[2]: 0.03}
    assert holm_adjust(raw, expected_names=SECONDARY_CONTRASTS) == {
        SECONDARY_CONTRASTS[0]: 0.03, SECONDARY_CONTRASTS[1]: 0.06, SECONDARY_CONTRASTS[2]: 0.06,
    }
    with pytest.raises(StatisticsError, match="exactly the three"):
        holm_adjust({SECONDARY_CONTRASTS[0]: 0.1}, expected_names=SECONDARY_CONTRASTS)


def test_independent_contrast_rng_states_and_secondary_arm_mapping():
    duplicate = {name: np.random.default_rng(5) for name in SECONDARY_CONTRASTS}
    with pytest.raises(StatisticsError, match="states collide"):
        validate_independent_rngs(duplicate, SECONDARY_CONTRASTS)
    rngs = {name: np.random.default_rng(10 + i) for i, name in enumerate(SECONDARY_CONTRASTS)}
    validate_independent_rngs(rngs, SECONDARY_CONTRASTS)
    records = _evaluation_records()
    result = secondary_sign_flip_holm(records, rngs, selected_mode="ordinary_pymatching")
    assert result["family_size"] == 3 and result["selected_mode"] == "ordinary_pymatching"
    assert tuple(result["raw_p_values"].keys()) == SECONDARY_CONTRASTS
    rngs2 = {name: np.random.default_rng(20 + i) for i, name in enumerate(SECONDARY_CONTRASTS)}
    result2 = secondary_sign_flip_holm(records, rngs2, selected_mode="correlation_enabled_pymatching")
    assert result2["other_mode"] == "ordinary_pymatching"


def test_root_sensitivities_and_duplicate_missing_fail_closed():
    records = _evaluation_records()
    assert len(leave_one_root_out(records)) == 60
    interval = root_t_interval_sensitivity(records)
    assert interval["status"] == "welch_satterthwaite_root_level_sensitivity_only"
    with pytest.raises(StatisticsError, match="duplicate"):
        primary_point_estimate(records + [records[0]])
    with pytest.raises(StatisticsError, match="must have root indices"):
        primary_point_estimate(records[:-1])
    wrong_root = list(records)
    wrong_root[0] = EvaluationRootCounts(wrong_root[0].condition_id, wrong_root[0].root_index,
        "evaluation:wrong-cell:r00", wrong_root[0].shots, wrong_root[0].errors_by_arm)
    with pytest.raises(StatisticsError, match="does not match"):
        primary_point_estimate(wrong_root)
