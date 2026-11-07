import numpy as np
import pytest

from headroom import (
    build_decoder, detector_count, fit_detector_model, marginal_scores,
    native_circuit, paired_root_effect, pauli_circuit, pauli_probabilities,
    residual_errors, select_calibration,
)


@pytest.mark.parametrize("distance", [3, 5, 7])
@pytest.mark.parametrize("memory", ["x", "z"])
def test_multidistance_circuit_and_matching_schema(distance, memory):
    c = native_circuit(memory, distance, 0.003, 0.003)
    assert c.num_detectors == detector_count(distance)
    assert c.num_observables == 1
    model, dem, correlated = build_decoder(c, "native")
    assert model.num_detectors == c.num_detectors
    assert model.num_fault_ids == 1
    assert correlated is False
    assert dem.num_detectors == c.num_detectors


def test_pauli_probabilities_keep_total_fault_mass_and_order():
    for regime in ("x_biased", "balanced", "z_biased"):
        p1, p2 = pauli_probabilities(regime, 0.003, 10)
        assert sum(p1) == pytest.approx(0.003)
        assert sum(p2) == pytest.approx(0.003)
        c = pauli_circuit("z", 3, regime, 0.003, 0.003)
        assert c.num_detectors == 24
        assert c.num_observables == 1
        model, dem, correlated = build_decoder(c, "pauli_biased")
        assert model.num_detectors == 24
        assert dem.num_observables == 1
        assert correlated is True


def test_marginal_fit_tie_breaks_to_first_candidate():
    d = np.zeros((8, 2), dtype=np.uint8)
    profiles = np.full((3, 2), 0.25)
    assert fit_detector_model(d, profiles) == 0
    assert marginal_scores(d, profiles).shape == (3,)


def test_pooled_and_specialist_selections_are_calibration_only_inputs():
    def row(predictions, labels):
        return {"residuals": residual_errors(
            labels, np.asarray(predictions, dtype=np.uint8))}
    cal = {
        "r0": [row([[0, 0], [1, 1]], [0, 0])],
        "r1": [row([[1, 1], [0, 0]], [0, 0])],
    }
    selected = select_calibration(cal, ["r0", "r1"], 2)
    assert selected["pooled_fixed_index"] == 0  # equal-rate tie -> lower index
    assert selected["regime_specialist_indices"] == {"r0": 0, "r1": 1}


def test_paired_root_metric_counts_real_shot_disagreements():
    # Candidate and pooled make deliberately different predictions.
    y = np.array([0, 0, 0, 0], dtype=np.uint8)
    p = np.array([[1, 0, 0, 0], [0, 1, 0, 0]], dtype=np.uint8)
    residuals = residual_errors(y, p)
    row0 = {"residuals": residuals[:, :2], "predictions": p[:, :2]}
    row1 = {"residuals": residuals[:, 2:], "predictions": p[:, 2:]}
    result = paired_root_effect({"r": [row0, row1]}, "r", 0, 1, 1000, 7)
    assert result["specialist_only_wrong"] == 1
    assert result["pooled_only_wrong"] == 1
    assert result["prediction_disagreements"] == 2
    assert result["shots"] == 4
