"""PyMatching adapter with explicit and consistent correlation configuration."""
from __future__ import annotations

import time
from typing import Any

import numpy as np

from .contracts import DecoderMetadata, DecoderPrediction, binary_matrix


class PyMatchingDecoder:
    """Wrap a PyMatching model and always use its declared correlation mode.

    Prefer :meth:`from_detector_error_model`, which constructs the graph and
    binds decoding to one explicit correlation setting. ``from_existing`` is
    a compatibility path for a legacy model whose construction setting has
    been checked at the call site; it refuses a declared construction/decode
    mismatch.
    """

    def __init__(self, matching: Any, metadata: DecoderMetadata):
        if not callable(getattr(matching, "decode_batch", None)):
            raise TypeError("matching must provide decode_batch().")
        actual_detectors = getattr(matching, "num_detectors", None)
        if actual_detectors is not None and int(actual_detectors) != metadata.detector_count:
            raise ValueError(
                f"Matching graph has {actual_detectors} detectors; metadata declares "
                f"{metadata.detector_count}."
            )
        self._matching = matching
        self.metadata = metadata

    @classmethod
    def from_detector_error_model(
        cls,
        dem: Any,
        *,
        correlation_mode: bool,
        name: str = "pymatching",
        noise_model_id: str | None = None,
        experimental: bool = False,
    ) -> "PyMatchingDecoder":
        if type(correlation_mode) is not bool:
            raise TypeError("correlation_mode must be an explicit bool.")
        import pymatching

        matching = pymatching.Matching.from_detector_error_model(
            dem, enable_correlations=correlation_mode
        )
        metadata = DecoderMetadata(
            name=name,
            implementation="PyMatching",
            version=str(pymatching.__version__),
            detector_count=int(dem.num_detectors),
            observable_count=int(dem.num_observables),
            noise_model_id=noise_model_id,
            correlation_mode=correlation_mode,
            experimental=experimental,
            construction_provenance="constructed from the supplied Stim DEM",
        )
        return cls(matching, metadata)

    @classmethod
    def from_existing(
        cls,
        matching: Any,
        *,
        detector_count: int,
        observable_count: int,
        constructed_with_correlations: bool,
        name: str = "pymatching-legacy-adapter",
        noise_model_id: str | None = None,
        experimental: bool = False,
        construction_provenance: str = "caller-verified legacy construction",
    ) -> "PyMatchingDecoder":
        """Adapt an existing model while requiring its build mode explicitly."""
        if type(constructed_with_correlations) is not bool:
            raise TypeError("constructed_with_correlations must be an explicit bool.")
        import pymatching

        metadata = DecoderMetadata(
            name=name,
            implementation="PyMatching",
            version=str(pymatching.__version__),
            detector_count=int(detector_count),
            observable_count=int(observable_count),
            noise_model_id=noise_model_id,
            correlation_mode=constructed_with_correlations,
            experimental=experimental,
            construction_provenance=construction_provenance,
        )
        return cls(matching, metadata)

    def decode(self, detectors: np.ndarray) -> DecoderPrediction:
        detector_bits = binary_matrix(
            detectors, name="detectors", columns=self.metadata.detector_count
        )
        start = time.perf_counter()
        try:
            raw = self._matching.decode_batch(
                detector_bits,
                enable_correlations=self.metadata.correlation_mode,
            )
        except Exception as exc:
            mode = self.metadata.correlation_mode
            raise RuntimeError(
                f"PyMatching decoder {self.metadata.name!r} failed with "
                f"enable_correlations={mode}."
            ) from exc
        elapsed = time.perf_counter() - start
        predictions = np.asarray(raw)
        if predictions.ndim == 1 and self.metadata.observable_count == 1:
            predictions = predictions[:, None]
        predictions = binary_matrix(
            predictions,
            name="observable predictions",
            columns=self.metadata.observable_count,
        )
        if len(predictions) != len(detector_bits):
            raise ValueError(
                "PyMatching returned a different shot count from the detector input."
            )
        return DecoderPrediction(
            bits=predictions,
            metadata=self.metadata,
            elapsed_seconds=elapsed,
        )
