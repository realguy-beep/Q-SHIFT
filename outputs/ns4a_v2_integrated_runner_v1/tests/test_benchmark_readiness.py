from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import stim

from qshift_ns4a_v2_deterministic.protocol import CANDIDATE_IDS, CONDITIONS, EVALUATION_ARMS
from qshift_ns4a_v2_runner import benchmark


READINESS_DIR = Path(__file__).resolve().parents[2] / "ns4a_v2_final_readiness_v1"


def test_bounded_benchmark_plan_caps_are_sampler_free():
    plan = json.loads((READINESS_DIR / "BENCHMARK_PROTOCOL.json").read_text(encoding="utf-8"))
    assert benchmark.validate_fixture_limits(plan) == {
        "maximum_total_shots": 6_000,
        "maximum_wall_clock_seconds": 600,
        "maximum_output_bytes": 134_217_728,
    }
    assert plan["hard_limits"]["sampler_calls"] == 6
    assert plan["hard_limits"]["maximum_sampler_shots_per_call"] == 1_000
    assert plan["hard_limits"]["sampler_returns_observables"] is False


def test_benchmark_inventory_is_unallocated_and_production_still_requires_its_owner_gate():
    inventory = json.loads((READINESS_DIR / "BENCHMARK_SEED_INVENTORY_TEMPLATE.json").read_text(encoding="utf-8"))
    assert inventory["numeric_seeds_allocated"] is False
    assert all(value is None for value in inventory["seed_by_condition"].values())
    with pytest.raises(benchmark.BenchmarkError, match="seed inventory is missing"):
        benchmark._authorize_benchmark(
            protocol_path=READINESS_DIR / "BENCHMARK_PROTOCOL.json",
            seed_inventory_path=READINESS_DIR / "BENCHMARK_SEED_INVENTORY_V1.json",
            authorization_path=READINESS_DIR / "BENCHMARK_OWNER_APPROVAL_V1.json",
            source_manifest_path=READINESS_DIR / "SOURCE_HASH_MANIFEST_V4.json",
            reserved_seed_values=set(),
        )


def test_missing_benchmark_authorization_blocks_before_model_construction_or_stim(monkeypatch):
    monkeypatch.setattr(stim.Circuit, "compile_detector_sampler",
                        lambda *a, **k: pytest.fail("benchmark sampler must not be reached without approval"))
    monkeypatch.setattr(benchmark, "build_model_catalog",
                        lambda *a, **k: pytest.fail("models must not be constructed before approval"))
    with pytest.raises(benchmark.BenchmarkError):
        benchmark.run_authorized_benchmark(
            repository_root=READINESS_DIR.parents[1],
            protocol_path=READINESS_DIR / "BENCHMARK_PROTOCOL.json",
            seed_inventory_path=READINESS_DIR / "BENCHMARK_SEED_INVENTORY_V1.json",
            authorization_path=READINESS_DIR / "BENCHMARK_OWNER_APPROVAL_V1.json",
            source_manifest_path=READINESS_DIR / "SOURCE_HASH_MANIFEST_V4.json",
            reserved_seed_values=set(),
        )


def test_detector_archive_round_trip_and_tamper_detection_without_labels(tmp_path):
    path = tmp_path / f"{CONDITIONS[0]}.npz"
    ids = {arm: "a" * 64 for arm in EVALUATION_ARMS}
    record = benchmark.write_detector_archive(
        path, condition=CONDITIONS[0],
        detectors=np.zeros((7, 40), dtype=np.uint8),
        candidate_predictions=np.zeros((len(CANDIDATE_IDS), 7, 1), dtype=np.uint8),
        evaluation_predictions=np.zeros((len(EVALUATION_ARMS), 7, 1), dtype=np.uint8),
        benchmark_seed_ref="benchmark-fixture-only:no-numeric-seed",
        sampling_identity_sha256="b" * 64,
        evaluation_identity_sha256_by_arm=ids,
    )
    verified = benchmark.verify_detector_archive(path)
    assert verified["archive_sha256"] == record["archive_sha256"]
    assert verified["shots"] == 7
    assert verified["labels_saved"] is False
    with np.load(path, allow_pickle=False) as data:
        assert "observables" not in data.files
        assert "labels" not in data.files
    with path.open("ab") as stream:
        stream.write(b"tamper")
    with pytest.raises(benchmark.BenchmarkError, match="content/identity"):
        benchmark.verify_detector_archive(path)


def test_benchmark_plan_rejects_larger_or_unreviewed_allocation():
    plan = json.loads((READINESS_DIR / "BENCHMARK_PROTOCOL.json").read_text(encoding="utf-8"))
    plan["maximum_total_shots"] = 6_001
    with pytest.raises(benchmark.BenchmarkError, match="maximum_total_shots"):
        benchmark.validate_fixture_limits(plan)


def test_candidate_execution_manifest_schema_is_not_activated_or_instantiated():
    schema = json.loads((READINESS_DIR / "CANDIDATE_EXECUTION_MANIFEST_SCHEMA_V1.json").read_text(encoding="utf-8"))
    assert schema["$id"] == "qshift-ns4a-v2-candidate-execution-manifest-v1"
    assert set(schema["required"]) == {
        "schema", "status", "experiment_id", "sampling_authorized", "git_commit",
        "protocol_path", "protocol_sha256", "source_manifest_path", "source_manifest_sha256",
        "seed_inventory_path", "seed_inventory_sha256", "historical_seed_screen_path",
        "historical_seed_screen_sha256", "dem_identity_manifest_path", "dem_identity_manifest_sha256",
        "runtime_fingerprint", "runtime_fingerprint_sha256", "output_directory", "resource_limits",
    }
    assert schema["properties"]["sampling_authorized"]["const"] is True
    assert not (READINESS_DIR / "PRODUCTION_SEED_INVENTORY_V1.json").exists()
    assert not (READINESS_DIR / "BENCHMARK_OWNER_APPROVAL_V1.json").exists()
    assert not (READINESS_DIR / "EXECUTION_MANIFEST_V1.json").exists()
