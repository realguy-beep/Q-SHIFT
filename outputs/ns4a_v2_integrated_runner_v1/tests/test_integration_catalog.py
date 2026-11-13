from __future__ import annotations

import pytest

from qshift_ns4a_v2_deterministic.protocol import CANDIDATE_IDS, CONDITIONS, EVALUATION_ARMS
from qshift_ns4a_v2_runner.models import (
    build_evaluation_bank,
    build_model_catalog,
    evaluation_decoder_views,
)


@pytest.fixture(scope="module")
def catalog():
    return build_model_catalog()


def test_catalog_builds_all_six_dems_and_twelve_ordered_candidates(catalog):
    assert tuple(catalog.conditions) == CONDITIONS
    assert tuple(catalog.selection_decoders) == CANDIDATE_IDS
    assert len(catalog.conditions) == 6
    assert len(catalog.selection_decoders) == 12
    assert all(c.dem_artifact.record.detector_count == 40 for c in catalog.conditions.values())
    assert all(c.dem_artifact.record.observable_count == 1 for c in catalog.conditions.values())
    assert all(d.metadata.detector_count == 40 and d.metadata.observable_count == 1
               for d in catalog.selection_decoders.values())


@pytest.mark.parametrize("condition", CONDITIONS)
def test_evaluation_bank_uses_selected_dem_parity_and_five_explicit_arm_labels(condition, catalog):
    selected = "balanced_burst_0.010::correlation_enabled_pymatching"
    bank, registration = build_evaluation_bank(catalog, condition, selected)
    try:
        assert set(bank.names()) == {
            "nominal_ordinary_pymatching",
            "nominal_correlation_enabled_pymatching",
            "pooled_selected_fixed_pymatching",
            "matched_selected_dem_pymatching_other_mode_control",
            "beliefmatching",
        }
        selected_pm = bank.adapter("pooled_selected_fixed_pymatching").model_identity
        matched_pm = bank.adapter("matched_selected_dem_pymatching_other_mode_control").model_identity
        belief = bank.adapter("beliefmatching").model_identity
        assert selected_pm.dem_record.dem_sha256 == matched_pm.dem_record.dem_sha256
        assert selected_pm.dem_record.dem_sha256 == belief.dem_record.dem_sha256
        assert selected_pm.decoder_assumed_noise_provenance_json == belief.decoder_assumed_noise_provenance_json
        assert selected_pm.decoder_assumed_noise_model_id == belief.decoder_assumed_noise_model_id
        views = evaluation_decoder_views(bank, catalog.conditions[condition].circuit)
        assert tuple(views) == EVALUATION_ARMS
        assert views["beliefmatching_same_selected_dem"].metadata.name == "beliefmatching"
    finally:
        registration.adapter.close()
