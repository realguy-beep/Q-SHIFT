"""Tests for exhibition features that do not generate random circuit shots."""
from __future__ import annotations

import numpy as np
from fastapi.testclient import TestClient

import server


def test_three_decoder_arms_receive_the_same_fixture_and_return_paired_errors():
    class SpyDecoder:
        def __init__(self, output):
            self.output = np.asarray(output, dtype=np.uint8)
            self.seen = None

        def decode_batch(self, detectors):
            self.seen = np.array(detectors, copy=True)
            return self.output

    detectors = np.zeros((2, 40), dtype=np.uint8)
    detectors[0, 8] = 1
    detectors[1, 10] = 1
    original = detectors.copy()
    labels = np.asarray([0, 1], dtype=np.uint8)
    arms = [SpyDecoder([0, 0]), SpyDecoder([1, 1]), SpyDecoder([0, 1])]
    result = server.decode_paired(detectors, labels, *arms[:2], privileged_decoder=arms[2])
    assert all(np.array_equal(arm.seen, original) for arm in arms)
    assert np.array_equal(detectors, original)
    assert result == {
        "fixed_errors": 1,
        "adaptive_errors": 1,
        "prediction_disagreements": 2,
        "privileged_errors": 0,
    }


def test_fixture_is_a_deterministic_dem_mechanism_not_a_sample():
    first = server.deterministic_dem_fixture()
    second = server.deterministic_dem_fixture()
    assert first == second
    assert first["fixture_kind"].startswith("single DEM mechanism; deterministic")
    assert first["representation"].startswith("decomposed approximate DEM")
    assert first["detector_indices"]
    assert len(first["syndrome"]) == 40
    assert set(first["syndrome"]) <= {0, 1}
    assert first["predicted_observable_correction"] in (0, 1)
    assert isinstance(first["logical_success_for_fixture"], bool)
    assert "not an exact circuit-level sampled history" in first["limitation"]


def test_fixture_endpoint_returns_same_deterministic_result():
    with TestClient(server.app) as client:
        response = client.get("/api/fixture")
    assert response.status_code == 200
    assert response.json() == server.deterministic_dem_fixture()


def test_privileged_reference_is_reported_separately_in_run_state_schema():
    with server._job_lock:
        server._jobs["fixture"] = {
            "id": "fixture",
            "status": "completed",
            "phase": "complete",
            "privileged_errors": 2,
            "privileged_ler": 0.002,
        }
    try:
        snapshot = server._snapshot("fixture")
    finally:
        with server._job_lock:
            server._jobs.pop("fixture", None)
    assert snapshot["privileged_errors"] == 2
    assert snapshot["privileged_ler"] == 0.002
