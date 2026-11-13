from __future__ import annotations

import hashlib
import json

import numpy as np
import pytest

from qshift_ns4a_v2_deterministic.protocol import CANDIDATE_IDS, CONDITIONS, make_root_id, selection_shots
from qshift_ns4a_v2_deterministic.selection import SelectionRootScore, choose_global_candidate
from qshift_ns4a_v2_deterministic.sample_schema import make_sample_ids
from qshift_ns4a_v2_runner.archive_store import (
    TransactionError,
    build_archive_arrays,
    commit_root_archive,
    archive_path,
)
from qshift_ns4a_v2_runner.run_state import (
    RunDirectoryLock,
    RunStateError,
    RunStateStore,
)


H1 = "a" * 64
H2 = "b" * 64


def _selection_arrays(condition=CONDITIONS[0], root_index=0):
    root = make_root_id("selection", condition, root_index)
    shots = selection_shots(CONDITIONS.index(condition), root_index)
    detectors = np.zeros((shots, 40), dtype=np.uint8)
    labels = np.zeros((shots, 1), dtype=np.uint8)
    predictions = np.zeros((len(CANDIDATE_IDS), shots, 1), dtype=np.uint8)
    ids = {candidate: hashlib.sha256(candidate.encode()).hexdigest() for candidate in CANDIDATE_IDS}
    return build_archive_arrays(
        partition="selection", condition_id=condition, root_id=root,
        detectors=detectors, observables=labels, predictions=predictions,
        model_identity_sha256_by_candidate=ids,
        sampling_identity_sha256=H1,
        root_seed_ref=f"fixture-only:no-seed:selection:{condition}:r{root_index:02d}",
        extra_metadata={"synthetic_fixture": True},
    )


def _new_store(path, *, fixture=True):
    state = RunStateStore(path, protocol_sha256=H1, source_manifest_sha256=H2, fixture_mode=fixture)
    state.initialize()
    return state


def test_run_lock_rejects_second_process_token_until_owner_releases(tmp_path):
    first = RunDirectoryLock(tmp_path)
    second = RunDirectoryLock(tmp_path)
    first.acquire()
    try:
        with pytest.raises(RunStateError, match="lock exists"):
            second.acquire()
    finally:
        first.release()
    second.acquire()
    second.release()


def test_archive_commit_and_exact_inflight_recovery_without_duplicate_sampling(tmp_path):
    state = _new_store(tmp_path)
    condition = CONDITIONS[0]
    root_id = make_root_id("selection", condition, 0)
    shots = selection_shots(0, 0)
    seed_ref = "fixture-only:no-seed:selection:balanced_no_burst:r00"
    state.begin_root(partition="selection", condition_id=condition, root_index=0,
                     shots=shots, seed=None, root_seed_ref=seed_ref)
    record = commit_root_archive(tmp_path, _selection_arrays(), root_seed_ref=seed_ref)
    # Simulate termination after archive+marker commit but before checkpoint CAS.
    restarted = RunStateStore(tmp_path, protocol_sha256=H1, source_manifest_sha256=H2, fixture_mode=True)
    restarted.recover_committed_inflight()
    payload = restarted.read()
    assert payload["state"] == "paused"
    assert payload["in_flight_root"] is None
    assert len(payload["committed_roots"]) == 1
    assert payload["committed_roots"][0]["root_id"] == root_id
    assert payload["committed_roots"][0]["archive_sha256"] == record["archive_sha256"]
    with pytest.raises(TransactionError, match="already exists"):
        commit_root_archive(tmp_path, _selection_arrays(), root_seed_ref=seed_ref)


def test_inflight_sampler_without_committed_bytes_is_ambiguous_and_fails_closed(tmp_path):
    state = _new_store(tmp_path)
    condition = CONDITIONS[0]
    state.begin_root(partition="selection", condition_id=condition, root_index=0,
                     shots=selection_shots(0, 0), seed=None,
                     root_seed_ref="fixture-only:no-seed:selection:balanced_no_burst:r00")
    recovered = RunStateStore(tmp_path, protocol_sha256=H1, source_manifest_sha256=H2, fixture_mode=True)
    with pytest.raises(RunStateError, match="resampling is ambiguous"):
        recovered.recover_committed_inflight()
    assert recovered.read()["in_flight_root"]["root_id"] == make_root_id("selection", condition, 0)


def test_root_archive_corruption_detected_before_resume(tmp_path):
    state = _new_store(tmp_path)
    condition = CONDITIONS[0]
    state.begin_root(partition="selection", condition_id=condition, root_index=0,
                     shots=selection_shots(0, 0), seed=None,
                     root_seed_ref="fixture-only:no-seed:selection:balanced_no_burst:r00")
    row = commit_root_archive(
        tmp_path, _selection_arrays(),
        root_seed_ref="fixture-only:no-seed:selection:balanced_no_burst:r00",
    )
    state.commit_root(row, seed=None)
    path = archive_path(tmp_path, "selection", condition, make_root_id("selection", condition, 0))
    with path.open("ab") as stream:
        stream.write(b"corruption")
    restarted = RunStateStore(tmp_path, protocol_sha256=H1, source_manifest_sha256=H2, fixture_mode=True)
    with pytest.raises(RunStateError, match="archive is invalid|hash"):
        restarted.validate_resume(protocol_sha256=H1, source_manifest_sha256=H2)


def test_evaluation_cannot_begin_before_immutable_selection_freeze(tmp_path):
    state = _new_store(tmp_path)
    with pytest.raises(RunStateError, match="evaluation is prohibited"):
        state.require_frozen_selection()


def test_duplicate_root_and_reused_seed_ref_rejected(tmp_path):
    state = _new_store(tmp_path)
    condition = CONDITIONS[0]
    root_id = make_root_id("selection", condition, 0)
    shots = selection_shots(0, 0)
    ref = "fixture-only:no-seed:selection:balanced_no_burst:r00"
    state.begin_root(partition="selection", condition_id=condition, root_index=0,
                     shots=shots, seed=50, root_seed_ref=ref)
    row = commit_root_archive(tmp_path, _selection_arrays(), root_seed_ref=ref)
    state.commit_root(row, seed=50)
    with pytest.raises(RunStateError, match="already committed"):
        state.begin_root(partition="selection", condition_id=condition, root_index=0,
                         shots=shots, seed=60, root_seed_ref="other-ref")
    with pytest.raises(RunStateError, match="seed was already consumed"):
        state.begin_root(partition="selection", condition_id=condition, root_index=1,
                         shots=selection_shots(0, 1), seed=50, root_seed_ref="other-ref")


def test_persisted_wall_clock_deadline_survives_store_recreation(tmp_path):
    epoch = [1_000.0]
    state = RunStateStore(
        tmp_path, protocol_sha256=H1, source_manifest_sha256=H2,
        fixture_mode=True, wall_clock_seconds=30, epoch_clock=lambda: epoch[0],
    )
    state.initialize()
    epoch[0] = 1_010.0
    restarted = RunStateStore(
        tmp_path, protocol_sha256=H1, source_manifest_sha256=H2,
        fixture_mode=True, wall_clock_seconds=30, epoch_clock=lambda: epoch[0],
    )
    assert restarted.remaining_wall_clock_seconds() == 20.0
    epoch[0] = 1_031.0
    with pytest.raises(RunStateError, match="deadline has expired"):
        restarted.remaining_wall_clock_seconds()


def test_completion_rejects_incomplete_roster_even_with_selection_and_audit_flags(tmp_path):
    state = _new_store(tmp_path)
    payload = state.read()
    payload["selection_frozen"] = True
    payload["selected_candidate"] = CANDIDATE_IDS[0]
    payload["selection_freeze_sha256"] = H1
    payload["independent_audit_verified"] = True
    payload["independent_audit_sha256"] = H2
    state._write(payload)
    with pytest.raises(RunStateError, match="all 48 selection and 60 evaluation roots"):
        state.mark_completed()


def _commit_complete_tied_selection(state, root_dir):
    """Build a deterministic all-zero selection archive roster; no sampler used."""
    records = []
    for condition_index, condition in enumerate(CONDITIONS):
        for root_index in range(8):
            root_id = make_root_id("selection", condition, root_index)
            shots = selection_shots(condition_index, root_index)
            seed_ref = f"fixture-only:no-seed:selection:{condition}:r{root_index:02d}"
            detectors = np.zeros((shots, 40), dtype=np.uint8)
            labels = np.zeros((shots, 1), dtype=np.uint8)
            predictions = np.zeros((len(CANDIDATE_IDS), shots, 1), dtype=np.uint8)
            identities = {candidate: hashlib.sha256(candidate.encode()).hexdigest() for candidate in CANDIDATE_IDS}
            state.begin_root(partition="selection", condition_id=condition, root_index=root_index,
                             shots=shots, seed=None, root_seed_ref=seed_ref)
            arrays = build_archive_arrays(
                partition="selection", condition_id=condition, root_id=root_id,
                detectors=detectors, observables=labels, predictions=predictions,
                model_identity_sha256_by_candidate=identities,
                sampling_identity_sha256=H1, root_seed_ref=seed_ref,
                extra_metadata={"synthetic_fixture": True},
            )
            marker = commit_root_archive(root_dir, arrays, root_seed_ref=seed_ref)
            state.commit_root(marker, seed=None)
            records.append(SelectionRootScore(
                condition, root_index, root_id, shots,
                {candidate: 0 for candidate in CANDIDATE_IDS},
            ))
    winner = choose_global_candidate(records)
    winner["selection_archive_sha256"] = {
        archive_path(root_dir, "selection", condition, make_root_id("selection", condition, root_index)).name:
        hashlib.sha256(archive_path(root_dir, "selection", condition,
                                    make_root_id("selection", condition, root_index)).read_bytes()).hexdigest()
        for condition in CONDITIONS for root_index in range(8)
    }
    return winner


def test_selection_freeze_rejects_valid_but_mismatched_candidate_and_accepts_recomputed_winner(tmp_path):
    state = _new_store(tmp_path)
    winner = _commit_complete_tied_selection(state, tmp_path)
    assert winner["selected_candidate"] == CANDIDATE_IDS[0]
    wrong = dict(winner, selected_candidate=CANDIDATE_IDS[1])
    with pytest.raises(RunStateError, match="selection winner or its archive hashes disagree"):
        state.freeze_selection(wrong)
    state.freeze_selection(winner)
    selected, _ = state.require_frozen_selection()
    assert selected == CANDIDATE_IDS[0]


def test_checkpoint_selected_candidate_tampering_is_detected_against_frozen_winner(tmp_path):
    state = _new_store(tmp_path)
    winner = _commit_complete_tied_selection(state, tmp_path)
    state.freeze_selection(winner)
    raw = json.loads(state.checkpoint_path.read_text(encoding="utf-8"))
    raw["selected_candidate"] = CANDIDATE_IDS[1]
    state.checkpoint_path.write_text(json.dumps(raw), encoding="utf-8")
    restarted = RunStateStore(tmp_path, protocol_sha256=H1, source_manifest_sha256=H2, fixture_mode=True)
    with pytest.raises(RunStateError, match="selection winner/checkpoint identity mismatch"):
        restarted.require_frozen_selection()


def test_tampered_checkpoint_archive_binding_is_detected_before_resume(tmp_path):
    state = _new_store(tmp_path)
    condition = CONDITIONS[0]
    ref = f"fixture-only:no-seed:selection:{condition}:r00"
    state.begin_root(partition="selection", condition_id=condition, root_index=0,
                     shots=selection_shots(0, 0), seed=None, root_seed_ref=ref)
    row = commit_root_archive(tmp_path, _selection_arrays(), root_seed_ref=ref)
    state.commit_root(row, seed=None)
    raw = json.loads(state.checkpoint_path.read_text(encoding="utf-8"))
    raw["committed_roots"][0]["archive_sha256"] = "0" * 64
    state.checkpoint_path.write_text(json.dumps(raw), encoding="utf-8")
    restarted = RunStateStore(tmp_path, protocol_sha256=H1, source_manifest_sha256=H2, fixture_mode=True)
    with pytest.raises(RunStateError, match="checkpoint schema validation|checkpoint/commit-marker mismatch"):
        restarted.validate_resume(protocol_sha256=H1, source_manifest_sha256=H2)


def test_interrupted_archive_marker_write_is_not_recovered_or_resampled(tmp_path, monkeypatch):
    import qshift_ns4a_v2_runner.archive_store as archive_module

    state = _new_store(tmp_path)
    condition = CONDITIONS[0]
    ref = f"fixture-only:no-seed:selection:{condition}:r00"
    state.begin_root(partition="selection", condition_id=condition, root_index=0,
                     shots=selection_shots(0, 0), seed=None, root_seed_ref=ref)
    monkeypatch.setattr(archive_module, "atomic_write_json",
                        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("injected marker-write interruption")))
    with pytest.raises(TransactionError, match="injected marker-write interruption"):
        commit_root_archive(tmp_path, _selection_arrays(), root_seed_ref=ref)
    path = archive_path(tmp_path, "selection", condition, make_root_id("selection", condition, 0))
    assert path.is_file()
    assert not path.with_suffix(".commit.json").exists()
    restarted = RunStateStore(tmp_path, protocol_sha256=H1, source_manifest_sha256=H2, fixture_mode=True)
    with pytest.raises(RunStateError, match="archive/marker pair is incomplete"):
        restarted.recover_committed_inflight()
