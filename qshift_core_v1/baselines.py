"""Deterministic reference decoders used for contract fixtures and comparisons."""
from __future__ import annotations

import numpy as np

from .contracts import DecoderMetadata, DecoderPrediction, binary_matrix


class IdentityObservableDecoder:
    """Predict no logical flip; this is a scoring reference, not a circuit."""

    def __init__(self, detector_count: int, observable_count: int = 1):
        self.metadata = DecoderMetadata(
            name="identity_no_decode",
            implementation="Q-SHIFT zero-prediction reference",
            version="1.0.0",
            detector_count=detector_count,
            observable_count=observable_count,
            experimental=False,
            construction_provenance="Always predicts observable mask zero; models no inferred correction.",
        )

    def decode(self, detectors: np.ndarray) -> DecoderPrediction:
        detector_bits = binary_matrix(
            detectors, name="detectors", columns=self.metadata.detector_count
        )
        return DecoderPrediction(
            bits=np.zeros((len(detector_bits), self.metadata.observable_count), dtype=np.uint8),
            metadata=self.metadata,
            elapsed_seconds=0.0,
        )
