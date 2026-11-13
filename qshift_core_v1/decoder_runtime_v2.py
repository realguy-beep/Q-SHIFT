"""NS-2C checked decoder execution and paired evaluation.

This is an additive runtime layer over the NS-2B sampling/model identity
contracts.  It does not select or alter decoder algorithms.  Model
assumptions and provenance remain explicit in ``DecoderModelIdentity``.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import time
from typing import Any, Mapping, Protocol, runtime_checkable

import numpy as np

from .contracts import DecoderMetadata, DecoderPrediction, DecoderProtocol, binary_matrix
from .controller import DecoderRegistry, SafeDecoderSelector
from .sampling_model_identity import (
    ALLOWED_SCOPES,
    DecoderModelIdentity,
    DetectorBatch,
    SamplingIdentity,
    assert_model_compatible,
    decode_model_checked,
    validate_batch,
)


@runtime_checkable
class DecoderAdapter(Protocol):
    """Typed boundary presented to the multi-decoder execution harness."""

    @property
    def name(self) -> str: ...

    @property
    def version(self) -> str: ...

    @property
    def model_identity(self) -> DecoderModelIdentity: ...

    @property
    def sampling_identity(self) -> SamplingIdentity: ...

    def predict(self, batch: DetectorBatch) -> "DecoderExecution": ...


@dataclass(frozen=True)
class DecoderExecution:
    """One decoder attempt; a failure has no prediction and is never replaced."""

    decoder_name: str
    decoder_version: str
    model_identity_sha256: str
    model_information: Mapping[str, Any]
    status: str
    wall_seconds: float
    decoder_reported_seconds: float | None
    prediction: DecoderPrediction | None
    failure_type: str | None = None
    failure_message: str | None = None

    def __post_init__(self) -> None:
        if self.status not in {"ok", "failed"}:
            raise ValueError("Execution status must be 'ok' or 'failed'.")
        if not np.isfinite(self.wall_seconds) or self.wall_seconds < 0:
            raise ValueError("wall_seconds must be finite and nonnegative.")
        if self.decoder_reported_seconds is not None and (
            not np.isfinite(self.decoder_reported_seconds) or self.decoder_reported_seconds < 0
        ):
            raise ValueError("decoder_reported_seconds must be finite and nonnegative or None.")
        if self.status == "ok":
            if not isinstance(self.prediction, DecoderPrediction):
                raise TypeError("Successful execution requires a DecoderPrediction.")
            if self.failure_type is not None or self.failure_message is not None:
                raise ValueError("Successful execution cannot contain failure details.")
        elif self.prediction is not None or not self.failure_type:
            raise ValueError("Failed execution must have an error type and no prediction.")

    def to_dict(self) -> dict[str, Any]:
        prediction_sha256 = None
        prediction_shape = None
        if self.prediction is not None:
            prediction_shape = list(self.prediction.bits.shape)
            prediction_sha256 = hashlib.sha256(self.prediction.bits.tobytes(order="C")).hexdigest()
        return {
            "decoder_name": self.decoder_name,
            "decoder_version": self.decoder_version,
            "model_identity_sha256": self.model_identity_sha256,
            "model_information": dict(self.model_information),
            "status": self.status,
            "wall_seconds": self.wall_seconds,
            "decoder_reported_seconds": self.decoder_reported_seconds,
            "prediction_shape": prediction_shape,
            "prediction_sha256": prediction_sha256,
            "failure_type": self.failure_type,
            "failure_message": self.failure_message,
        }


class CheckedDecoderAdapter:
    """Adapt an existing detector-in decoder to the NS-2C typed boundary.

    The wrapper verifies the exact NS-2B model/circuit identity, gives the
    implementation a defensive detector copy, checks returned metadata and
    dimensions, detaches the output from decoder-owned memory, and captures
    both wall-clock and decoder-reported timing.  Ordinary inference errors
    become explicit failed records; no fallback prediction is fabricated.
    """

    def __init__(
        self,
        implementation: DecoderProtocol,
        *,
        model_identity: DecoderModelIdentity,
        sampling_identity: SamplingIdentity,
    ) -> None:
        assert_model_compatible(model_identity, sampling_identity)
        metadata = getattr(implementation, "metadata", None)
        if not isinstance(metadata, DecoderMetadata) or metadata != model_identity.metadata:
            raise ValueError("Implementation metadata must exactly match the declared model identity.")
        if not callable(getattr(implementation, "decode", None)):
            raise TypeError("Implementation must provide decode(detectors).")
        self._implementation = implementation
        self._model_identity = model_identity
        self._sampling_identity = sampling_identity

    @property
    def name(self) -> str:
        return self._model_identity.metadata.name

    @property
    def version(self) -> str:
        return self._model_identity.metadata.version

    @property
    def model_identity(self) -> DecoderModelIdentity:
        return self._model_identity

    @property
    def sampling_identity(self) -> SamplingIdentity:
        return self._sampling_identity

    def predict(self, batch: DetectorBatch) -> DecoderExecution:
        metadata = self._model_identity.metadata
        started = time.perf_counter()
        try:
            checked = decode_model_checked(
                self._implementation, self._model_identity, self._sampling_identity, batch
            )
            # decode_model_checked detaches from model-owned storage. Mark this
            # execution's array read-only so downstream policies cannot alter it.
            stable_bits = np.array(checked.bits, dtype=np.uint8, order="C", copy=True)
            stable_bits.setflags(write=False)
            prediction = DecoderPrediction(stable_bits, checked.metadata, checked.elapsed_seconds)
            return DecoderExecution(
                decoder_name=self.name,
                decoder_version=self.version,
                model_identity_sha256=self._model_identity.identity_sha256,
                model_information=self._model_identity.to_dict(),
                status="ok",
                wall_seconds=max(0.0, time.perf_counter() - started),
                decoder_reported_seconds=checked.elapsed_seconds,
                prediction=prediction,
            )
        except Exception as exc:
            return DecoderExecution(
                decoder_name=metadata.name,
                decoder_version=metadata.version,
                model_identity_sha256=self._model_identity.identity_sha256,
                model_information=self._model_identity.to_dict(),
                status="failed",
                wall_seconds=max(0.0, time.perf_counter() - started),
                decoder_reported_seconds=None,
                prediction=None,
                failure_type=type(exc).__name__,
                failure_message=str(exc),
            )


class CompatibilityAwareDecoderBank:
    """Registers compatible decoder adapters while preserving the V1 selector.

    Experimental decoders are rejected unless ``experimental_opt_in=True``
    is passed for that registration.  The fixed fallback remains governed by
    the existing ``SafeDecoderSelector`` and is never silently substituted by
    the paired evaluator.
    """

    def __init__(self, sampling_identity: SamplingIdentity) -> None:
        if not isinstance(sampling_identity, SamplingIdentity):
            raise TypeError("sampling_identity must be SamplingIdentity.")
        self.sampling_identity = sampling_identity
        self._adapters: dict[str, CheckedDecoderAdapter] = {}
        self._registry = DecoderRegistry()

    def register(
        self, adapter: DecoderAdapter, *, experimental_opt_in: bool = False
    ) -> None:
        if not isinstance(adapter, CheckedDecoderAdapter):
            raise TypeError("Register a CheckedDecoderAdapter so identity and output checks cannot be skipped.")
        if type(experimental_opt_in) is not bool:
            raise TypeError("experimental_opt_in must be bool.")
        if adapter.sampling_identity.identity_sha256 != self.sampling_identity.identity_sha256:
            raise ValueError("Adapter targets a different sampling identity.")
        assert_model_compatible(adapter.model_identity, self.sampling_identity)
        if adapter.model_identity.metadata.experimental and not experimental_opt_in:
            raise PermissionError("Experimental decoder registration requires explicit opt-in.")
        if adapter.name in self._adapters:
            raise ValueError(f"Decoder {adapter.name!r} is already registered.")
        self._registry.register(adapter.name, adapter._implementation)
        self._adapters[adapter.name] = adapter

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._adapters))

    def adapter(self, name: str) -> CheckedDecoderAdapter:
        try:
            return self._adapters[name]
        except KeyError as exc:
            raise KeyError(f"Unknown decoder {name!r}.") from exc

    def selector(self, *, fallback_name: str, **kwargs: Any) -> SafeDecoderSelector:
        """Reuse the accepted fixed-fallback and hysteresis selector unchanged."""
        return SafeDecoderSelector(self._registry, fallback_name=fallback_name, **kwargs)


def evaluate_paired_batch(
    bank: CompatibilityAwareDecoderBank,
    batch: DetectorBatch,
    *,
    decoder_names: tuple[str, ...],
    baseline_name: str,
    scope: str,
    sample_id: str,
    observables: Any | None = None,
) -> dict[str, Any]:
    """Run all requested decoders on identical bytes, then optionally score.

    Labels are validated and read only after every decoder call has completed;
    only detector batches reach decoder implementations.  A failed arm keeps
    its failure record and receives no substitute prediction.  Prediction-only
    disagreements remain reportable even when labels are unavailable.
    """
    if not isinstance(scope, str):
        raise ValueError("scope must be a string.")
    if scope not in ALLOWED_SCOPES:
        if scope == "protected-test":
            raise PermissionError("This development evaluator refuses protected-test scope.")
        raise ValueError(f"Unsupported scope {scope!r}.")
    if not isinstance(sample_id, str) or not sample_id.strip():
        raise ValueError("sample_id is required.")
    if (not isinstance(decoder_names, tuple) or not decoder_names
            or any(not isinstance(name, str) or not name.strip() for name in decoder_names)):
        raise ValueError("decoder_names must be a nonempty tuple of unique names.")
    if len(set(decoder_names)) != len(decoder_names):
        raise ValueError("decoder_names must contain unique names.")
    if not isinstance(baseline_name, str) or not baseline_name.strip():
        raise ValueError("baseline_name must be a nonempty string.")
    if baseline_name not in decoder_names:
        raise ValueError("decoder_names must include baseline_name.")
    if any(name not in bank.names() for name in decoder_names):
        raise ValueError("All decoders must be registered before evaluation.")
    validate_batch(batch, bank.sampling_identity)
    detector_digest = batch.content_sha256
    detector_bytes = validate_batch(batch, bank.sampling_identity).tobytes(order="C")

    executions: dict[str, DecoderExecution] = {}
    for name in decoder_names:
        adapter = bank.adapter(name)
        if adapter.sampling_identity.identity_sha256 != batch.sampling_identity_sha256:
            raise ValueError(f"Decoder {name!r} is incompatible with this detector batch.")
        executions[name] = adapter.predict(batch)
        if validate_batch(batch, bank.sampling_identity).tobytes(order="C") != detector_bytes:
            raise RuntimeError("Detector batch changed during paired evaluation.")

    # The label object is not touched until all implementations have returned.
    labels: np.ndarray | None = None
    label_digest: str | None = None
    if observables is not None:
        source = np.asarray(observables)
        if source.ndim == 1:
            source = source[:, None]
        labels = binary_matrix(source, name="observables", columns=len(bank.sampling_identity.observable_ids))
        if labels.shape[0] != batch.shape[0]:
            raise ValueError("Observable shot count differs from detector batch.")
        label_digest = hashlib.sha256(labels.tobytes(order="C")).hexdigest()

    successful: dict[str, np.ndarray] = {
        name: execution.prediction.bits
        for name, execution in executions.items()
        if execution.status == "ok" and execution.prediction is not None
    }
    per_decoder: dict[str, dict[str, Any]] = {}
    error_masks: dict[str, np.ndarray] = {}
    for name, execution in executions.items():
        row = execution.to_dict()
        row["shots"] = batch.shape[0]
        row["errors"] = None
        row["logical_error_rate"] = None
        if labels is not None and name in successful:
            wrong = np.any(successful[name] != labels, axis=1)
            error_masks[name] = wrong
            errors = int(np.count_nonzero(wrong))
            row["errors"] = errors
            row["logical_error_rate"] = errors / len(labels)
        per_decoder[name] = row

    paired: dict[str, dict[str, Any]] = {}
    if baseline_name not in successful:
        baseline_reason = "baseline execution failed; paired comparisons unavailable"
        for name in decoder_names:
            if name != baseline_name:
                paired[name] = {"available": False, "reason": baseline_reason}
    else:
        base_prediction = successful[baseline_name]
        base_errors = error_masks.get(baseline_name)
        for name in decoder_names:
            if name == baseline_name:
                continue
            if name not in successful:
                paired[name] = {"available": False, "reason": "decoder execution failed"}
                continue
            candidate = successful[name]
            row = {
                "available": True,
                "shots": batch.shape[0],
                "prediction_disagreements": int(np.count_nonzero(np.any(candidate != base_prediction, axis=1))),
                "candidate_only_failures": None,
                "baseline_only_failures": None,
            }
            candidate_errors = error_masks.get(name)
            if labels is not None and base_errors is not None and candidate_errors is not None:
                row["candidate_only_failures"] = int(np.count_nonzero(candidate_errors & ~base_errors))
                row["baseline_only_failures"] = int(np.count_nonzero(~candidate_errors & base_errors))
            paired[name] = row

    model_ids = {name: bank.adapter(name).model_identity.identity_sha256 for name in decoder_names}
    sample_identity = {
        "schema": "qshift-paired-decoder-batch-v2",
        "scope": scope,
        "sample_id": sample_id,
        "sampling_identity_sha256": bank.sampling_identity.identity_sha256,
        "detector_content_sha256": detector_digest,
        "detector_shape": list(batch.shape),
        "detector_convention": "unpacked-binary-uint8 [shots, detectors], declared NS-2B detector order",
        "observable_content_sha256": label_digest,
        "decoder_model_identity_sha256": model_ids,
        "hash_note": "Hashes identify supplied content but do not prove upstream provenance, authorization, or leakage absence.",
    }
    return {
        "schema_version": 2,
        "scope": scope,
        "sample_id": sample_id,
        "shots": batch.shape[0],
        "baseline": baseline_name,
        "sample_identity": sample_identity,
        "records": per_decoder,
        "paired_vs_baseline": paired,
        "label_isolation": "Decoder implementations received detector-only defensive copies; labels were first read after all decoder calls.",
        "failure_policy": "Failed decoders have no prediction; no fallback or substitute prediction is inserted.",
    }


class DeterministicParityDecoder:
    """Tiny integration fixture, not a quantum error-correction decoder.

    Each output is the XOR of a declared nonempty set of detector columns.
    This provides known predictions for contract tests without sampling.
    """

    def __init__(self, metadata: DecoderMetadata, detector_groups: tuple[tuple[int, ...], ...]):
        if len(detector_groups) != metadata.observable_count or not detector_groups:
            raise ValueError("One nonempty detector group is required per observable.")
        normalized: list[tuple[int, ...]] = []
        for group in detector_groups:
            if (not isinstance(group, tuple) or not group
                    or any(type(index) is not int or not 0 <= index < metadata.detector_count for index in group)):
                raise ValueError("Each parity group must contain valid detector-column indices.")
            normalized.append(group)
        self.metadata = metadata
        self.detector_groups = tuple(normalized)

    def decode(self, detectors: np.ndarray) -> DecoderPrediction:
        bits = binary_matrix(detectors, name="fixture detectors", columns=self.metadata.detector_count)
        predictions = np.zeros((len(bits), self.metadata.observable_count), dtype=np.uint8)
        for observable, group in enumerate(self.detector_groups):
            predictions[:, observable] = np.bitwise_xor.reduce(bits[:, group], axis=1)
        return DecoderPrediction(predictions, self.metadata, elapsed_seconds=0.0)
