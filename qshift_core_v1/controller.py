"""Versioned decoder registry and causal, confidence-aware selection hook."""
from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Integral, Real
from typing import Mapping

from .contracts import DecoderMetadata, DecoderProtocol


@dataclass(frozen=True)
class NoiseEstimate:
    """Detector-derived estimate carried as provenance, not as truth labels."""

    parameters: Mapping[str, float]
    confidence: float
    calibration_shots: int
    source: str = "detector_only"

    def __post_init__(self) -> None:
        if not isinstance(self.source, str) or self.source != "detector_only":
            raise ValueError("Deployable selection accepts detector-only estimates.")
        if isinstance(self.confidence, bool) or not isinstance(self.confidence, Real):
            raise ValueError("Estimate confidence must be numeric.")
        if not 0.0 <= self.confidence <= 1.0 or not math.isfinite(self.confidence):
            raise ValueError("Estimate confidence must be finite and in [0, 1].")
        if isinstance(self.calibration_shots, bool) or not isinstance(self.calibration_shots, Integral):
            raise ValueError("calibration_shots must be an integer.")
        if self.calibration_shots < 0:
            raise ValueError("calibration_shots must be nonnegative.")
        if not isinstance(self.parameters, Mapping) or not self.parameters:
            raise ValueError("At least one estimated noise parameter is required.")
        for name, value in self.parameters.items():
            if (not isinstance(name, str) or not name.strip() or isinstance(value, bool)
                    or not isinstance(value, Real) or not math.isfinite(value)):
                raise ValueError(f"Estimated noise parameter {name!r} must be named and finite.")


@dataclass(frozen=True)
class SelectionProposal:
    decoder_name: str
    confidence: float
    based_on_through_block: int
    reason: str
    estimate: NoiseEstimate | None = None


@dataclass(frozen=True)
class SelectionDecision:
    block_index: int
    selected_decoder: str
    requested_decoder: str | None
    switched: bool
    fallback_used: bool
    confidence: float | None
    reason: str
    estimated_noise: Mapping[str, float] | None
    configured_noise: Mapping[str, float] | None


class DecoderRegistry:
    """Name-to-decoder registry with a required, non-experimental fallback."""

    def __init__(self) -> None:
        self._decoders: dict[str, DecoderProtocol] = {}

    def register(self, name: str, decoder: DecoderProtocol) -> None:
        if not isinstance(name, str) or not name.strip() or name in self._decoders:
            raise ValueError(f"Decoder name is empty or already registered: {name!r}.")
        if not hasattr(decoder, "metadata") or not callable(getattr(decoder, "decode", None)):
            raise TypeError("Registered decoder must satisfy DecoderProtocol.")
        if not isinstance(decoder.metadata, DecoderMetadata):
            raise TypeError("Registered decoder must expose DecoderMetadata.")
        if decoder.metadata.name != name:
            raise ValueError("Registry name must match decoder metadata.name.")
        self._decoders[name] = decoder

    def get(self, name: str) -> DecoderProtocol:
        try:
            return self._decoders[name]
        except KeyError as exc:
            raise KeyError(f"Unknown decoder {name!r}.") from exc

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._decoders))


class SafeDecoderSelector:
    """Apply proposals only after earlier-block evidence and confidence checks.

    Low confidence, missing estimates, invalid proposals, and unsupported
    configurations return to the registered fixed fallback immediately. A
    non-fallback change requires confidence, hysteresis, and dwell gates.
    """

    def __init__(
        self,
        registry: DecoderRegistry,
        *,
        fallback_name: str,
        minimum_confidence: float = 0.8,
        hysteresis_blocks: int = 2,
        minimum_dwell_blocks: int = 2,
        allow_experimental: bool = False,
    ) -> None:
        self.registry = registry
        fallback = registry.get(fallback_name)
        if fallback.metadata.experimental:
            raise ValueError("The fixed fallback must not be marked experimental.")
        if isinstance(minimum_confidence, bool) or not isinstance(minimum_confidence, Real):
            raise ValueError("minimum_confidence must be numeric.")
        if not math.isfinite(minimum_confidence) or not 0.0 <= minimum_confidence <= 1.0:
            raise ValueError("minimum_confidence must be in [0, 1].")
        if (isinstance(hysteresis_blocks, bool) or not isinstance(hysteresis_blocks, Integral)
                or isinstance(minimum_dwell_blocks, bool) or not isinstance(minimum_dwell_blocks, Integral)
                or hysteresis_blocks < 1 or minimum_dwell_blocks < 1):
            raise ValueError("Hysteresis and dwell lengths must be positive.")
        self.fallback_name = fallback_name
        self.minimum_confidence = minimum_confidence
        self.hysteresis_blocks = hysteresis_blocks
        self.minimum_dwell_blocks = minimum_dwell_blocks
        if type(allow_experimental) is not bool:
            raise ValueError("allow_experimental must be a bool.")
        self.allow_experimental = allow_experimental
        self.current_name = fallback_name
        self._last_block = -1
        self._age = 0
        self._pending_name: str | None = None
        self._pending_count = 0

    def choose(
        self,
        current_block: int,
        proposal: SelectionProposal | None,
        *,
        configured_noise: Mapping[str, float] | None = None,
    ) -> SelectionDecision:
        if (isinstance(current_block, bool) or not isinstance(current_block, Integral)
                or current_block < 0 or current_block <= self._last_block):
            raise ValueError("current_block must be a nonnegative, strictly increasing integer.")
        current_block = int(current_block)
        configured_record = None
        if configured_noise is not None:
            if not isinstance(configured_noise, Mapping):
                raise ValueError("configured_noise must be a mapping of numeric parameters.")
            configured_record = {}
            for name, value in configured_noise.items():
                if (not isinstance(name, str) or not name.strip() or isinstance(value, bool)
                        or not isinstance(value, Real) or not math.isfinite(value)):
                    raise ValueError("configured_noise values must be named finite numbers.")
                configured_record[name] = float(value)
        invalid_proposal = proposal is not None and not isinstance(proposal, SelectionProposal)
        if invalid_proposal:
            proposal = None
        self._last_block = current_block
        previous = self.current_name
        self._age += 1
        requested = proposal.decoder_name if proposal else None
        confidence = proposal.confidence if proposal else None
        estimate = proposal.estimate if proposal and isinstance(proposal.estimate, NoiseEstimate) else None
        estimated_noise = dict(estimate.parameters) if estimate else None
        if (proposal is not None and estimate is not None
                and isinstance(proposal.confidence, Real) and not isinstance(proposal.confidence, bool)):
            confidence = min(proposal.confidence, estimate.confidence)

        reason = "invalid proposal; fixed fallback" if invalid_proposal else "no proposal; fixed fallback"
        target = self.fallback_name
        if proposal is not None:
            if (isinstance(proposal.confidence, bool) or not isinstance(proposal.confidence, Real)
                    or not math.isfinite(proposal.confidence) or not 0.0 <= proposal.confidence <= 1.0):
                reason = "invalid confidence; fixed fallback"
            elif not isinstance(proposal.decoder_name, str) or not proposal.decoder_name.strip():
                reason = "invalid decoder name; fixed fallback"
            elif not isinstance(proposal.reason, str):
                reason = "invalid proposal reason; fixed fallback"
            elif (isinstance(proposal.based_on_through_block, bool)
                  or not isinstance(proposal.based_on_through_block, Integral)
                  or proposal.based_on_through_block < 0
                  or proposal.based_on_through_block >= current_block):
                reason = "non-causal proposal rejected; fixed fallback"
            elif not isinstance(proposal.estimate, NoiseEstimate):
                reason = "missing or unsupported detector estimate; fixed fallback"
            elif confidence < self.minimum_confidence:
                reason = "confidence below threshold; fixed fallback"
            else:
                try:
                    candidate = self.registry.get(proposal.decoder_name)
                except KeyError:
                    candidate = None
                if candidate is None or (candidate.metadata.experimental and not self.allow_experimental):
                    reason = "unsupported decoder proposal; fixed fallback"
                else:
                    target = proposal.decoder_name
                    reason = proposal.reason or "accepted detector-only proposal"

        if target == self.fallback_name:
            self.current_name = self.fallback_name
            self._pending_name = None
            self._pending_count = 0
            self._age = 0
            reason = reason or "fixed fallback"
        elif target == self.current_name:
            self._pending_name = None
            self._pending_count = 0
        else:
            if self._pending_name == target:
                self._pending_count += 1
            else:
                self._pending_name = target
                self._pending_count = 1
            if self._age >= self.minimum_dwell_blocks and self._pending_count >= self.hysteresis_blocks:
                self.current_name = target
                self._age = 0
                self._pending_name = None
                self._pending_count = 0
            else:
                reason = "proposal pending hysteresis/dwell; retained current decoder"

        switched = previous != self.current_name
        return SelectionDecision(
            block_index=current_block,
            selected_decoder=self.current_name,
            requested_decoder=requested,
            switched=switched,
            fallback_used=self.current_name == self.fallback_name,
            confidence=confidence,
            reason=reason,
            estimated_noise=estimated_noise,
            configured_noise=configured_record,
        )
