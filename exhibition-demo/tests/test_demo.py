from __future__ import annotations

import threading
import time

import numpy as np
import pytest
from fastapi.testclient import TestClient

import server


@pytest.fixture(autouse=True)
def clear_job_registry():
    with server._job_lock:
        server._jobs.clear()
    yield
    with server._job_lock:
        server._jobs.clear()


def wait_for_job(client: TestClient, job_id: str, timeout: float = 120.0) -> dict:
    deadline = time.monotonic() + timeout
    latest = None
    while time.monotonic() < deadline:
        response = client.get(f"/api/run/{job_id}")
        assert response.status_code == 200
        latest = response.json()
        if latest["status"] in {"completed", "error"}:
            return latest
        time.sleep(0.05)
    raise AssertionError(f"Run did not finish within {timeout}s; last status={latest}")


def start_real_run(client: TestClient, shots: int, burst: float) -> dict:
    response = client.post("/api/run", json={"shots": shots, "burst": burst})
    assert response.status_code == 202, response.text
    job = wait_for_job(client, response.json()["id"])
    assert job["status"] == "completed", job
    assert job["generated_shots"] == shots
    assert job["completed_shots"] == shots
    assert job["calibration_shots_completed"] == 2_000
    assert job["profile_reference_shots"] == 20_400
    assert job["elapsed_seconds"] > 0
    assert job["evaluation_seconds"] >= 0
    assert job["fixed_errors"] == int(job["fixed_errors"])
    assert job["adaptive_errors"] == int(job["adaptive_errors"])
    assert job["fixed_ler"] == pytest.approx(job["fixed_errors"] / shots)
    assert job["adaptive_ler"] == pytest.approx(job["adaptive_errors"] / shots)
    assert job["prediction_disagreements"] <= shots
    return job


def test_health_and_served_page():
    with TestClient(server.app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["engine"] == "ready"
        assert health.json()["stim"] == "1.16.0"
        assert health.json()["pymatching"] == "2.4.0"
        page = client.get("/")
        assert page.status_code == 200
        assert "LIVE SIMULATION" in page.text or "LIVE SIMULATOR" in page.text
        assert "FROZEN RESEARCH" in page.text


def test_circuit_dimensions_and_burst_insertion():
    no_burst = server.make_circuit(0.0)
    burst = server.make_circuit(0.008)
    assert (no_burst.num_detectors, no_burst.num_observables) == (40, 1)
    assert (burst.num_detectors, burst.num_observables) == (40, 1)
    assert "E(0.008) X8 X10" not in str(no_burst)
    assert str(burst).count("E(0.008) X8 X10") == 5


def test_pymatching_correlation_configuration_regression():
    decoder = server.build_decoder(0.008)
    detectors = server.make_circuit(0.008).compile_detector_sampler(seed=127).sample(32)
    # The known failure occurs if the correlation-enabled flag is passed to this
    # ordinary decoder. The application path must omit it and decode successfully.
    with pytest.raises(ValueError, match="decoder has not been configured to decode using correlations"):
        decoder.decode_batch(detectors, enable_correlations=True)
    predictions = decoder.decode_batch(detectors)
    assert np.asarray(predictions).reshape(-1).shape == (32,)


def test_both_decoder_arms_receive_identical_detector_rows():
    class SpyDecoder:
        def __init__(self, output):
            self.output = np.asarray(output, dtype=np.uint8)
            self.seen = None

        def decode_batch(self, detectors):
            self.seen = np.array(detectors, copy=True)
            return self.output

    detectors = np.array([[0, 1] * 20, [1, 0] * 20], dtype=np.uint8)
    labels = np.array([[0], [1]], dtype=np.uint8)
    fixed = SpyDecoder([0, 0])
    adaptive = SpyDecoder([1, 1])
    result = server.decode_paired(detectors, labels, fixed, adaptive)
    assert np.array_equal(fixed.seen, detectors)
    assert np.array_equal(adaptive.seen, detectors)
    assert result == {"fixed_errors": 1, "adaptive_errors": 1, "prediction_disagreements": 2}


def test_api_rejects_unsupported_inputs():
    with TestClient(server.app) as client:
        assert client.post("/api/run", json={"shots": 2_500, "burst": 0.008}).status_code == 422
        assert client.post("/api/run", json={"shots": 1_000, "burst": 0.006}).status_code == 422
        assert client.post("/api/run", json={"shots": "1000", "burst": 0.008}).status_code == 422


def test_real_1000_shot_run_at_burst_008():
    with TestClient(server.app) as client:
        job = start_real_run(client, 1_000, 0.008)
        assert job["burst"] == 0.008


def test_real_5000_shot_run_at_burst_008():
    with TestClient(server.app) as client:
        job = start_real_run(client, 5_000, 0.008)
        assert job["burst"] == 0.008


def test_real_10000_shot_run_at_burst_008():
    with TestClient(server.app) as client:
        job = start_real_run(client, 10_000, 0.008)
        assert job["burst"] == 0.008


def test_real_zero_burst_run():
    with TestClient(server.app) as client:
        job = start_real_run(client, 1_000, 0.0)
        assert job["burst"] == 0.0


def test_backend_failure_is_visible_and_next_run_can_retry(monkeypatch, caplog):
    original = server.build_decoder
    attempts = 0

    def fail_once(probability):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("injected decoder build failure")
        return original(probability)

    monkeypatch.setattr(server, "build_decoder", fail_once)
    with TestClient(server.app) as client:
        first = client.post("/api/run", json={"shots": 1_000, "burst": 0.008})
        failed = wait_for_job(client, first.json()["id"])
        assert failed["status"] == "error"
        assert "injected decoder build failure" in failed["error"]
        assert "run failed" in caplog.text

        retry = client.post("/api/run", json={"shots": 1_000, "burst": 0.008})
        assert retry.status_code == 202
        completed = wait_for_job(client, retry.json()["id"])
        assert completed["status"] == "completed"
        assert completed["completed_shots"] == 1_000


def test_repeated_concurrent_request_is_rejected(monkeypatch):
    entered = threading.Event()
    release = threading.Event()

    def held_worker(job_id, req):
        entered.set()
        assert release.wait(timeout=5)
        with server._job_lock:
            server._jobs[job_id].update(status="completed", phase="complete", completed_shots=0)

    monkeypatch.setattr(server, "_worker", held_worker)
    with TestClient(server.app) as client:
        first = client.post("/api/run", json={"shots": 1_000, "burst": 0.008})
        assert first.status_code == 202
        assert entered.wait(timeout=3)
        second = client.post("/api/run", json={"shots": 1_000, "burst": 0.008})
        assert second.status_code == 429
        release.set()
        assert wait_for_job(client, first.json()["id"])["status"] == "completed"


def test_generated_and_completed_counts_stay_distinct_on_decode_failure(monkeypatch):
    def fail_decode(*args, **kwargs):
        raise RuntimeError("injected batch decode failure")

    monkeypatch.setattr(server, "decode_paired", fail_decode)
    with TestClient(server.app) as client:
        started = client.post("/api/run", json={"shots": 1_000, "burst": 0.008})
        failed = wait_for_job(client, started.json()["id"])
        assert failed["status"] == "error"
        assert failed["generated_shots"] == 500
        assert failed["completed_shots"] == 0


def test_frontend_progress_and_offline_assets_are_explicit():
    html = (server.ROOT / "index.html").read_text(encoding="utf-8")
    assert "j.completed_shots" in html
    assert "j.generated_shots" in html
    assert "sessionStorage" in html
    assert "hasLiveSample=true" in html
    assert "enable_correlations" not in html
    assert 'src="http://' not in html and 'src="https://' not in html
