from __future__ import annotations

import json

import numpy as np

from qshift_core_v1.contracts import DecoderMetadata, DecoderPrediction
from qshift_ns4a_v2_deterministic.protocol import CANDIDATE_IDS, EVALUATION_ARMS
from qshift_ns4a_v2_deterministic.sample_schema import ARCHIVE_SCHEMA, make_sample_ids, sample_id_sequence_sha256


class LabelProbe:
    def __init__(self, values):
        self.values = np.asarray(values, dtype=np.uint8)
        self.read = False

    def __array__(self, dtype=None, copy=None):
        self.read = True
        array = self.values if dtype is None else self.values.astype(dtype, copy=False)
        return np.array(array, copy=True) if copy else array


class FakeDecoder:
    def __init__(self, name: str, bits, label_probe: LabelProbe | None = None, expected_input_sha: str | None = None):
        self.metadata = DecoderMetadata(name=name, implementation="deterministic-test-double", version="fixture-1",
                                        detector_count=40, observable_count=1)
        self.bits = np.asarray(bits, dtype=np.uint8)
        self.label_probe = label_probe
        self.expected_input_sha = expected_input_sha
        self.calls = 0

    def decode(self, detectors):
        self.calls += 1
        assert detectors.shape[1] == 40
        assert detectors.flags.writeable is False
        if self.label_probe is not None:
            assert self.label_probe.read is False
        if self.expected_input_sha is not None:
            import hashlib
            assert hashlib.sha256(detectors.tobytes(order="C")).hexdigest() == self.expected_input_sha
        return DecoderPrediction(np.array(self.bits, copy=True), self.metadata, elapsed_seconds=0.0)


def selection_decoder_map(shots: int, label_probe=None, input_sha=None):
    return {
        candidate: FakeDecoder(candidate, np.zeros((shots, 1), dtype=np.uint8), label_probe, input_sha)
        for candidate in CANDIDATE_IDS
    }


def evaluation_decoder_map(shots: int, bits_by_arm: dict[str, np.ndarray], label_probe=None, input_sha=None):
    return {
        arm: FakeDecoder(arm, bits_by_arm[arm], label_probe, input_sha)
        for arm in EVALUATION_ARMS
    }


def build_archive_arrays(*, partition: str, condition: str, root_index: int, detectors: np.ndarray,
                         labels: np.ndarray, predictions: np.ndarray, candidate_ids: tuple[str, ...]):
    root_id = f"{partition}:{condition}:r{root_index:02d}"
    sample_ids = make_sample_ids(partition, condition, root_id, len(detectors))
    metadata = {
        "sampling_identity_sha256": "a" * 64,
        "model_identity_sha256_by_candidate": {name: (hexchar * 64) for name, hexchar in zip(candidate_ids, "0123456789abcdef"[:len(candidate_ids)])},
        "row_identity_sha256": sample_id_sequence_sha256(sample_ids),
        "root_seed_ref": f"fixture/{partition}/{condition}/r{root_index:02d}",
    }
    return {
        "schema_version": np.asarray(ARCHIVE_SCHEMA),
        "partition": np.asarray(partition),
        "condition_id": np.asarray(condition),
        "root_id": np.asarray(root_id),
        "sample_ids": np.asarray(sample_ids, dtype="U"),
        "detectors": np.asarray(detectors, dtype=np.uint8),
        "observables": np.asarray(labels, dtype=np.uint8),
        "candidate_ids": np.asarray(candidate_ids, dtype="U"),
        "predictions": np.asarray(predictions, dtype=np.uint8),
        "metadata_json": np.asarray(json.dumps(metadata, sort_keys=True, separators=(",", ":"))),
    }, root_id
