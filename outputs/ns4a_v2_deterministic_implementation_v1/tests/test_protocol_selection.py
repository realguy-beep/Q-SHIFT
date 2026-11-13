from __future__ import annotations

from fractions import Fraction
from dataclasses import replace

import numpy as np
import pytest

from qshift_ns4a_v2_deterministic.protocol import (
    CANDIDATE_IDS, CONDITIONS, EVALUATION_UNIQUE_SHOTS, SELECTION_UNIQUE_SHOTS,
    TOTAL_UNIQUE_SHOTS, make_root_id, selection_shots, validate_allocation,
)
from qshift_ns4a_v2_deterministic.sample_schema import make_sample_ids
from qshift_ns4a_v2_deterministic.selection import (
    SelectionError, SelectionRootScore, choose_global_candidate, run_and_score_selection_batch,
    selection_scores,
)
from .helpers import LabelProbe, selection_decoder_map


def _records(errors_by_candidate=None):
    errors_by_candidate = errors_by_candidate or {candidate: 10 for candidate in CANDIDATE_IDS}
    out = []
    for ci, condition in enumerate(CONDITIONS):
        for ri in range(8):
            shots = selection_shots(ci, ri)
            out.append(SelectionRootScore(condition, ri, make_root_id("selection", condition, ri), shots,
                                          dict(errors_by_candidate)))
    return out


def test_allocation_arithmetic_and_exact_shot_schedule():
    assert validate_allocation() == {"selection": 64_000, "evaluation": 240_000, "total": 304_000}
    assert (SELECTION_UNIQUE_SHOTS, EVALUATION_UNIQUE_SHOTS, TOTAL_UNIQUE_SHOTS) == (64_000, 240_000, 304_000)
    for ci in range(6):
        assert sum(selection_shots(ci, ri) for ri in range(8)) == (10_667 if ci < 4 else 10_666)
        assert sum(selection_shots(ci, ri) for ri in range(8)) == 8 * 1_333 + (3 if ci < 4 else 2)


def test_twelve_candidate_completeness_and_exact_deterministic_tie_order():
    errors = {candidate: 10 for candidate in CANDIDATE_IDS}
    errors[CANDIDATE_IDS[0]] = errors[CANDIDATE_IDS[1]] = 3
    records = _records(errors)
    score_pairs = selection_scores(records)
    assert tuple(name for name, _ in score_pairs) == CANDIDATE_IDS
    result = choose_global_candidate(records)
    assert result["selected_candidate"] == CANDIDATE_IDS[0]
    assert result["exact_tie_set"] == CANDIDATE_IDS[:2]
    # Each condition gives each root equal weight; the 1,333/1,334 shot
    # allocation is not used as a shot-weighted condition denominator.
    score = Fraction(*map(int, result["score_fraction_by_candidate"][CANDIDATE_IDS[0]].split("/")))
    expected = sum((Fraction(3, 1_333 + int(r < (3 if ci < 4 else 2))) for ci in range(6) for r in range(8)), Fraction()) / 48
    assert score == expected


def test_selection_decoders_get_same_detector_bytes_and_never_read_labels_early():
    condition = CONDITIONS[0]
    root_id = make_root_id("selection", condition, 0)
    shots = selection_shots(0, 0)
    detectors = np.zeros((shots, 40), dtype=np.uint8)
    detectors[::2, 7] = 1
    labels = LabelProbe(np.zeros((shots, 1), dtype=np.uint8))
    ids = make_sample_ids("selection", condition, root_id, shots)
    import hashlib
    expected_hash = hashlib.sha256(detectors.tobytes(order="C")).hexdigest()
    decoders = selection_decoder_map(shots, labels, expected_hash)
    result = run_and_score_selection_batch(
        condition_id=condition, root_index=0, root_id=root_id, detectors=detectors,
        detector_sample_ids=ids, labels=labels, label_sample_ids=ids, prediction_sample_ids=ids,
        decoders=decoders,
    )
    assert labels.read is True
    assert all(decoder.calls == 1 for decoder in decoders.values())
    assert result.root_score.shots == shots
    assert result.root_score.errors_by_candidate == {candidate: 0 for candidate in CANDIDATE_IDS}
    assert result.detector_sha256 == expected_hash


def test_selection_rejects_misaligned_labels_missing_candidate_and_duplicate_roots():
    condition = CONDITIONS[0]
    root_id = make_root_id("selection", condition, 0)
    shots = selection_shots(0, 0)
    detectors = np.zeros((shots, 40), dtype=np.uint8)
    ids = make_sample_ids("selection", condition, root_id, shots)
    decoders = selection_decoder_map(shots)
    with pytest.raises(SelectionError, match="row IDs"):
        run_and_score_selection_batch(condition_id=condition, root_index=0, root_id=root_id, detectors=detectors,
            detector_sample_ids=ids, labels=np.zeros((shots, 1), np.uint8), label_sample_ids=ids[:-1],
            prediction_sample_ids=ids, decoders=decoders)
    with pytest.raises(SelectionError, match="12 candidates"):
        run_and_score_selection_batch(condition_id=condition, root_index=0, root_id=root_id, detectors=detectors,
            detector_sample_ids=ids, labels=np.zeros((shots, 1), np.uint8), label_sample_ids=ids,
            prediction_sample_ids=ids, decoders={k: v for i, (k, v) in enumerate(decoders.items()) if i})
    records = _records()
    with pytest.raises(SelectionError, match="duplicate selection root-condition"):
        selection_scores(records + [records[0]])
    duplicate_cross_cell_id = replace(records[8], root_id=records[0].root_id)
    with pytest.raises(SelectionError, match="does not match"):
        selection_scores(records[:8] + [duplicate_cross_cell_id] + records[9:])
    with pytest.raises(SelectionError, match="does not match"):
        selection_scores(records[:1] + [replace(records[1], root_id=records[0].root_id)] + records[2:])
