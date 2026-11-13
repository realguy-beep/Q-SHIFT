from __future__ import annotations

import numpy as np
import pytest
import ast
from pathlib import Path

from qshift_ns4a_v2_deterministic.audit_saved_arrays import IndependentAuditError, audit_saved_arrays
from qshift_ns4a_v2_deterministic.paired_evaluation import PairedEvaluationError, run_paired_evaluation_batch
from qshift_ns4a_v2_deterministic.protocol import CONDITIONS, EVALUATION_ARMS, make_root_id
from qshift_ns4a_v2_deterministic.sample_schema import (
    ArchiveValidationError, make_sample_ids, validate_archive_mapping, validate_paired_sample_ids,
)
from .helpers import LabelProbe, build_archive_arrays, evaluation_decoder_map


def test_paired_evaluation_identity_and_label_isolation():
    condition = CONDITIONS[0]
    root_id = make_root_id("evaluation", condition, 0)
    ids = make_sample_ids("evaluation", condition, root_id, 4_000)
    detectors = np.zeros((4_000, 40), dtype=np.uint8)
    detectors[::2, 3] = 1
    labels = LabelProbe(np.zeros((4_000, 1), dtype=np.uint8))
    outputs = {
        EVALUATION_ARMS[0]: np.zeros((4_000, 1), dtype=np.uint8),
        EVALUATION_ARMS[1]: np.zeros((4_000, 1), dtype=np.uint8),
        EVALUATION_ARMS[2]: np.zeros((4_000, 1), dtype=np.uint8),
        EVALUATION_ARMS[3]: np.zeros((4_000, 1), dtype=np.uint8),
        EVALUATION_ARMS[4]: np.ones((4_000, 1), dtype=np.uint8),
    }
    import hashlib
    expected_hash = hashlib.sha256(detectors.tobytes(order="C")).hexdigest()
    decoders = evaluation_decoder_map(4_000, outputs, labels, expected_hash)
    result = run_paired_evaluation_batch(
        condition_id=condition, root_index=0, root_id=root_id, detectors=detectors,
        detector_sample_ids=ids, labels=labels, label_sample_ids=ids,
        prediction_sample_ids=ids, decoders=decoders,
    )
    assert labels.read is True
    assert result["shots"] == 4_000
    assert result["errors_by_arm"][EVALUATION_ARMS[2]] == 0
    assert result["errors_by_arm"][EVALUATION_ARMS[4]] == 4_000
    assert result["primary_paired_discordances"] == {
        "BM_wrong_PM_correct": 4_000, "BM_correct_PM_wrong": 0,
    }
    assert all(decoder.calls == 1 for decoder in decoders.values())


def test_paired_evaluation_rejects_row_identity_and_does_not_read_labels_on_decode_error():
    condition = CONDITIONS[0]
    root_id = make_root_id("evaluation", condition, 0)
    ids = make_sample_ids("evaluation", condition, root_id, 4_000)
    labels = LabelProbe(np.zeros((4_000, 1), dtype=np.uint8))
    decoders = evaluation_decoder_map(4_000, {arm: np.zeros((4_000, 1), np.uint8) for arm in EVALUATION_ARMS}, labels)
    with pytest.raises(PairedEvaluationError, match="row IDs"):
        run_paired_evaluation_batch(condition_id=condition, root_index=0, root_id=root_id,
            detectors=np.zeros((4_000, 40), np.uint8), detector_sample_ids=ids,
            labels=labels, label_sample_ids=ids[:-1], prediction_sample_ids=ids, decoders=decoders)
    assert labels.read is False
    with pytest.raises(PairedEvaluationError, match="invalid binary predictions"):
        bad = evaluation_decoder_map(4_000, {arm: np.zeros((4_000, 1), np.uint8) for arm in EVALUATION_ARMS})
        original = bad[EVALUATION_ARMS[2]]
        class MutatedPredictionDecoder:
            metadata = original.metadata
            def decode(self, detector_input):
                result = original.decode(detector_input)
                object.__setattr__(result, "bits", np.full((4_000, 1), 2, dtype=np.uint8))
                return result
        bad[EVALUATION_ARMS[2]] = MutatedPredictionDecoder()
        run_paired_evaluation_batch(condition_id=condition, root_index=0, root_id=root_id,
            detectors=np.zeros((4_000, 40), np.uint8), detector_sample_ids=ids,
            labels=labels, label_sample_ids=ids, prediction_sample_ids=ids, decoders=bad)
    assert labels.read is False


def test_archive_schema_rejects_bad_dimensions_dtype_and_duplicate_sample_ids():
    arrays, _ = build_archive_arrays(partition="selection", condition=CONDITIONS[0], root_index=0,
        detectors=np.zeros((1_334, 40), np.uint8), labels=np.zeros((1_334, 1), np.uint8),
        predictions=np.zeros((12, 1_334, 1), np.uint8), candidate_ids=__import__(
            "qshift_ns4a_v2_deterministic.protocol", fromlist=["CANDIDATE_IDS"]).CANDIDATE_IDS)
    assert validate_archive_mapping(arrays).detectors.shape == (1_334, 40)
    wrong = dict(arrays)
    wrong["detectors"] = np.zeros((1_334, 39), np.uint8)
    with pytest.raises(ArchiveValidationError, match="dimensions"):
        validate_archive_mapping(wrong)
    wrong = dict(arrays)
    wrong["predictions"] = np.zeros((12, 1_334, 1), np.int8)
    with pytest.raises(ArchiveValidationError, match="uint8"):
        validate_archive_mapping(wrong)
    wrong = dict(arrays)
    sample_ids = np.array(wrong["sample_ids"], copy=True)
    sample_ids[1] = sample_ids[0]
    wrong["sample_ids"] = sample_ids
    with pytest.raises(ArchiveValidationError):
        validate_archive_mapping(wrong)


def test_independent_saved_array_audit_recomputes_tiny_six_cell_fixture(tmp_path):
    paths = []
    roots = []
    for ci, condition in enumerate(CONDITIONS):
        # Root zero is an extra-shot root in all six cells.
        shots = 1_334
        partition = "selection"
        from qshift_ns4a_v2_deterministic.protocol import CANDIDATE_IDS
        root_id = f"selection:{condition}:r00"
        detectors = np.zeros((shots, 40), dtype=np.uint8)
        labels = np.zeros((shots, 1), dtype=np.uint8)
        predictions = np.zeros((12, shots, 1), dtype=np.uint8)
        # Fixed deterministic counts, with candidate zero better only in one
        # cell, demonstrate that the independent auditor derives its own score.
        predictions[0, :ci + 1, 0] = 1
        archive, _ = build_archive_arrays(partition=partition, condition=condition, root_index=0,
            detectors=detectors, labels=labels, predictions=predictions, candidate_ids=CANDIDATE_IDS)
        path = tmp_path / f"{ci}.npz"
        np.savez_compressed(path, **archive)
        paths.append(path)
        roots.append((partition, condition, 0))
    audited = audit_saved_arrays(paths, partition="selection", expected_root_keys=roots)
    assert audited["audit"] == "PASS"
    assert audited["verified_roots"] == 6
    assert audited["unique_shots"] == 6 * 1_334
    from qshift_ns4a_v2_deterministic.protocol import CANDIDATE_IDS
    assert audited["selection"]["selected_candidate"] == CANDIDATE_IDS[1]
    with pytest.raises(IndependentAuditError, match="coverage mismatch"):
        audit_saved_arrays(paths[:-1], partition="selection", expected_root_keys=roots)
    with pytest.raises(IndependentAuditError, match="duplicates sample IDs"):
        audit_saved_arrays([paths[0], paths[0], *paths[1:]], partition="selection", expected_root_keys=roots)


def test_independent_saved_array_audit_recomputes_paired_evaluation_counts(tmp_path):
    paths = []
    roots = []
    for ci, condition in enumerate(CONDITIONS):
        partition = "evaluation"
        shots = 4_000
        root_id = f"evaluation:{condition}:r00"
        labels = np.zeros((shots, 1), dtype=np.uint8)
        predictions = np.zeros((len(EVALUATION_ARMS), shots, 1), dtype=np.uint8)
        predictions[4, :ci + 1, 0] = 1
        predictions[2, ci + 1:ci + 3, 0] = 1
        archive, _ = build_archive_arrays(partition=partition, condition=condition, root_index=0,
            detectors=np.zeros((shots, 40), dtype=np.uint8), labels=labels,
            predictions=predictions, candidate_ids=EVALUATION_ARMS)
        path = tmp_path / f"e{ci}.npz"
        np.savez_compressed(path, **archive)
        paths.append(path)
        roots.append((partition, condition, 0))
    audited = audit_saved_arrays(paths, partition="evaluation", expected_root_keys=roots)
    assert audited["verified_roots"] == 6 and audited["unique_shots"] == 24_000
    assert audited["per_arm"][EVALUATION_ARMS[4]]["errors"] == sum(range(1, 7))
    assert audited["primary"]["paired_discordances_by_condition"][CONDITIONS[0]] == {
        "BM_wrong_PM_correct": 1, "BM_correct_PM_wrong": 2,
    }


def test_independent_auditor_does_not_import_runner_aggregation_or_checkpoint_code():
    path = Path(__file__).parents[1] / "qshift_ns4a_v2_deterministic" / "audit_saved_arrays.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
        elif isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
    assert not any(name.endswith(("selection", "statistics", "checkpoint")) for name in imported)
