"""Validated, detector-in / observable-prediction-out decoder contracts."""
from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Real
from typing import Any, Protocol, runtime_checkable

import numpy as np


def binary_matrix(values: Any, *, name: str, columns: int | None = None) -> np.ndarray:
    """Return a contiguous uint8 binary matrix without silently coercing values."""
    array = np.asarray(values)
    if array.ndim != 2:
        raise ValueError(f"{name} must have shape [shots, bits], got {array.shape}.")
    if columns is not None and array.shape[1] != columns:
        raise ValueError(f"{name} must have {columns} columns, got {array.shape[1]}.")
    if array.dtype.kind not in "biuf":
        raise ValueError(f"{name} must contain numeric binary values.")
    if not np.isfinite(array).all() or np.any((array != 0) & (array != 1)):
        raise ValueError(f"{name} must contain only finite 0/1 values.")
    return np.ascontiguousarray(array, dtype=np.uint8)


@dataclass(frozen=True)
class DecoderMetadata:
    name: str
    implementation: str
    version: str
    detector_count: int
    observable_count: int
    noise_model_id: str | None = None
    correlation_mode: bool | None = None
    experimental: bool = False
    construction_provenance: str = "unspecified"

    def __post_init__(self) -> None:
        if any(not isinstance(value, str) or not value.strip()
               for value in (self.name, self.implementation, self.version)):
            raise ValueError("Decoder name, implementation, and version are required.")
        for field_name, value in (("detector_count", self.detector_count),
                                  ("observable_count", self.observable_count)):
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{field_name} must be an integer.")
        if self.detector_count <= 0 or self.observable_count <= 0:
            raise ValueError("Detector and observable counts must be positive.")
        if self.correlation_mode is not None and type(self.correlation_mode) is not bool:
            raise ValueError("correlation_mode must be true, false, or None for non-matching decoders.")
        if type(self.experimental) is not bool:
            raise ValueError("experimental must be a bool.")
        if self.noise_model_id is not None and not isinstance(self.noise_model_id, str):
            raise ValueError("noise_model_id must be text or None.")
        if not isinstance(self.construction_provenance, str):
            raise ValueError("construction_provenance must be text.")


@dataclass(frozen=True)
class DecoderPrediction:
    """Binary predictions have explicit [shots, observables] shape."""

    bits: np.ndarray
    metadata: DecoderMetadata
    elapsed_seconds: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, DecoderMetadata):
            raise TypeError("metadata must be DecoderMetadata.")
        bits = binary_matrix(
            self.bits, name="decoder prediction", columns=self.metadata.observable_count
        )
        object.__setattr__(self, "bits", bits)
        if self.elapsed_seconds is not None:
            value = self.elapsed_seconds
            if (isinstance(value, bool) or not isinstance(value, Real)
                    or not math.isfinite(value) or value < 0):
                raise ValueError("elapsed_seconds must be a finite nonnegative real number, not bool.")


@runtime_checkable
class DecoderProtocol(Protocol):
    metadata: DecoderMetadata

    def decode(self, detectors: np.ndarray) -> DecoderPrediction:
        """Predict observable-flip bits from detector events only."""
