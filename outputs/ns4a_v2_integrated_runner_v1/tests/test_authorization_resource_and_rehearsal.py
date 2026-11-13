from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import copy

import pytest
import stim

from qshift_ns4a_v2_runner.cli import main
from qshift_ns4a_v2_runner.dry_rehearsal import run_full_deterministic_rehearsal
from qshift_ns4a_v2_runner.integrity import (
    EXECUTION_RUN_DIRECTORY, IntegrityError, execution_output_path,
    load_authorized_execution, runtime_fingerprint,
)
from qshift_ns4a_v2_runner.resource_guard import ResourceGuard, ResourceLimitError
from qshift_ns4a_v2_runner.runner import StimRootSampler
from qshift_ns4a_v2_runner.audit import RunAuditError, audit_run_directory
from qshift_ns4a_v2_runner.models import build_evaluation_bank, build_model_catalog, evaluation_model_identity_map
from qshift_ns4a_v2_deterministic.protocol import CANDIDATE_IDS, CONDITIONS


@dataclass
class Disk:
    free: int


def test_resource_guard_stops_at_deadline_rss_and_disk(tmp_path):
    now = [0.0]
    guard = ResourceGuard(tmp_path, wall_clock_seconds=1, peak_rss_bytes=10,
                          free_disk_reserve_bytes=100, clock=lambda: now[0],
                          rss_provider=lambda: 5, disk_usage_provider=lambda _p: Disk(200))
    guard.start()
    now[0] = 2
    with pytest.raises(ResourceLimitError, match="wall-clock"):
        guard.check("statistical analysis")

    guard = ResourceGuard(tmp_path, peak_rss_bytes=10, free_disk_reserve_bytes=100,
                          clock=lambda: 0.0, rss_provider=lambda: 11,
                          disk_usage_provider=lambda _p: Disk(200))
    guard.started_at = 0.0
    with pytest.raises(ResourceLimitError, match="RSS"):
        guard.check("decoder construction")

    guard = ResourceGuard(tmp_path, peak_rss_bytes=10, free_disk_reserve_bytes=100,
                          clock=lambda: 0.0, rss_provider=lambda: 5,
                          disk_usage_provider=lambda _p: Disk(99))
    guard.started_at = 0.0
    with pytest.raises(ResourceLimitError, match="disk"):
        guard.check("archive write")


def test_execute_mode_without_final_manifest_and_owner_record_is_blocked(tmp_path):
    with pytest.raises(SystemExit) as exc:
        main(["--mode", "execute"])
    assert exc.value.code == 2
    with pytest.raises(IntegrityError, match="both required"):
        load_authorized_execution(tmp_path / "manifest.json", tmp_path / "approval.json", repository_root=tmp_path)
    with pytest.raises(PermissionError, match="capability"):
        StimRootSampler(None)
    assert execution_output_path(tmp_path, EXECUTION_RUN_DIRECTORY) == (
        tmp_path / "outputs/ns4a_v2_integrated_runner_v1/production_run"
    )
    with pytest.raises(IntegrityError, match="arbitrary paths"):
        execution_output_path(tmp_path, "outputs/stage5/should-never-be-selected")


def test_runtime_fingerprint_checks_entire_lock_and_pinned_beliefmatching_checkout():
    fingerprint = runtime_fingerprint()
    assert fingerprint["python"] == "3.12.10"
    assert fingerprint["locked_distribution_count"] == 23
    assert fingerprint["distributions"]["numpy"] == "2.2.6"
    assert fingerprint["distributions"]["stim"] == "1.16.0"
    assert fingerprint["distributions"]["pymatching"] == "2.4.0"
    assert fingerprint["beliefmatching_upstream_commit"] == "4458c278bbec273c8c1a26411dadccc49222f8ef"
    assert fingerprint["beliefmatching_core_source_sha256_lf"] == (
        "03229b09559f7059aa6bd7bd6ce80ee1190b41e702f49625ef511074ff42238f"
    )


def test_cli_default_is_sampler_free_dry_run(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr("qshift_ns4a_v2_runner.cli.run_full_deterministic_rehearsal",
                        lambda: calls.append("dry") or {"status": "fixture"})
    monkeypatch.setattr("qshift_ns4a_v2_runner.runner.StimRootSampler.sample",
                        lambda *a, **k: pytest.fail("sampler must not be invoked by default mode"))
    assert main([]) == 0
    assert calls == ["dry"]
    assert '"status": "fixture"' in capsys.readouterr().out


def test_full_108_root_rehearsal_uses_no_stim_sampler_and_saved_arrays_reaudit(tmp_path, monkeypatch):
    monkeypatch.setattr(stim.Circuit, "compile_detector_sampler",
                        lambda *a, **k: pytest.fail("deterministic rehearsal invoked Stim sampler"))
    run_directory = tmp_path / "full-fixture-run"
    result = run_full_deterministic_rehearsal(output_directory=run_directory)
    assert result["status"] == "PASS_SYNTHETIC_FIXTURE_ONLY"
    assert result["stim_sampler_calls"] == 0
    assert result["generated_experimental_events"] == 0
    assert result["fixture_rows"] == 304_000
    assert result["selection_fixture_rows"] == 64_000
    assert result["evaluation_fixture_rows"] == 240_000
    assert result["selection_roots"] == 48
    assert result["evaluation_roots"] == 60
    assert len(result["candidates_exercised"]) == 12
    assert len(result["evaluation_arms_exercised"]) == 5
    assert result["independent_auditor"] == "PASS"
    assert result["independently_recomputed_total_rows"] == 304_000
    assert result["checkpoint_state"] == "completed"
    assert result["temporary_outputs_removed"] is False

    # Reconstruct expected identities independently after rehearsal shutdown,
    # then reopen every saved archive and commit marker.
    catalog = build_model_catalog()
    selected = result["selected_candidate_on_fixture_only"]
    assert selected in CANDIDATE_IDS
    evaluation_models = {}
    for condition in CONDITIONS:
        bank, registration = build_evaluation_bank(catalog, condition, selected)
        try:
            evaluation_models[condition] = evaluation_model_identity_map(bank)
        finally:
            registration.adapter.close()
    from qshift_ns4a_v2_runner.runner import _expected_audit_bindings
    bindings = _expected_audit_bindings(catalog, evaluation_models)
    checkpoint = json.loads((run_directory / "checkpoint.json").read_text(encoding="utf-8"))
    independent = audit_run_directory(run_directory, checkpoint, **bindings)
    saved_report = json.loads((run_directory / "INDEPENDENT_AUDIT.json").read_text(encoding="utf-8"))
    assert independent["audit"] == "PASS"
    assert independent["verified_roots"] == 108
    assert independent["total_shots"] == 304_000
    assert independent["total_shots"] == saved_report["total_shots"]
    assert len(list((run_directory / "roots").glob("*.npz"))) == 108
    assert len(list((run_directory / "roots").glob("*.commit.json"))) == 108
    for partition, expected_count in (("selection", 48), ("evaluation", 60)):
        rows = independent[f"{partition}_archive_audit"]["per_root"]
        assert len(rows) == expected_count
        for row in rows:
            path = run_directory / "roots" / f"{partition}__{row['condition_id']}__r{row['root_index']:02d}.npz"
            assert hashlib.sha256(path.read_bytes()).hexdigest() == row["archive_sha256"]

    bad_model_binding = copy.deepcopy(bindings)
    bad_model_binding["expected_model_identity_sha256_by_partition_condition"]["selection"][CONDITIONS[0]][CANDIDATE_IDS[0]] = "0" * 64
    with pytest.raises(RunAuditError, match="decoder/DEM identity"):
        audit_run_directory(run_directory, checkpoint, **bad_model_binding)
    bad_seed_binding = copy.deepcopy(bindings)
    bad_seed_binding["expected_seed_bindings"][("evaluation", CONDITIONS[0], 0)]["root_seed_ref"] = "fixture-only:wrong-reference"
    with pytest.raises(RunAuditError, match="seed-inventory identity"):
        audit_run_directory(run_directory, checkpoint, **bad_seed_binding)
