"""Experimental Q-SHIFT adapter for upstream beliefmatching 0.2.0.

This adapter accepts a separately constructed decoder DEM. It never samples,
never fits hidden noise parameters, and keeps generating-circuit identity
metadata separate from the decoder-model identity.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib.metadata
from typing import Callable, Sequence

import numpy as np


UPSTREAM_VERSION = "0.2.0"
UPSTREAM_COMMIT = "4458c278bbec273c8c1a26411dadccc49222f8ef"
UPSTREAM_CORE_SOURCE_SHA256_LF = "03229b09559f7059aa6bd7bd6ce80ee1190b41e702f49625ef511074ff42238f"


class BeliefMatchingContractError(ValueError):
    """Input/output does not satisfy the detector/observable contract."""


class BeliefMatchingConstructionError(RuntimeError):
    """Upstream decoder could not be constructed from the declared DEM."""


class BeliefMatchingDisabledError(RuntimeError):
    """The experimental adapter was not explicitly enabled."""


@dataclass(frozen=True)
class DecoderModelIdentity:
    sampling_circuit_sha256: str
    generating_noise_identity: str
    decoder_dem_sha256: str
    assumed_noise_provenance: str
    detector_ids: tuple[int, ...]
    observable_ids: tuple[int, ...]
    observable_semantics: str

    @property
    def identity(self) -> str:
        payload = "\n".join((
            self.decoder_dem_sha256,
            self.assumed_noise_provenance,
            ",".join(map(str, self.detector_ids)),
            ",".join(map(str, self.observable_ids)),
            self.observable_semantics,
        )).encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()
        return f"beliefmatching-dem-sha256:{digest}"


def _stim_model_bytes(model) -> bytes:
    return str(model).encode("utf-8")


def validate_upstream_signature_semantics(dem) -> None:
    """Reject DEM constructs the pinned upstream converter silently aliases.

    BeliefMatching 0.2.0 keys its hyperedge and edge dictionaries by detector
    support alone, then stores a single observable support per key. Distinct
    observable signatures on the same detector support would therefore be
    overwritten. It also treats a component's target lists as sets, so repeated
    targets inside a decomposed component are unsafe. Fail closed on these
    deterministic representation hazards.
    """
    hyperedge_obs: dict[frozenset[int], set[frozenset[int]]] = {}
    edge_obs: dict[frozenset[int], set[frozenset[int]]] = {}

    def xor(values: list[int]) -> frozenset[int]:
        parity: set[int] = set()
        for value in values:
            if value in parity:
                parity.remove(value)
            else:
                parity.add(value)
        return frozenset(parity)

    for inst in dem.flattened():
        if inst.type != "error":
            if inst.type not in ("detector", "logical_observable"):
                raise BeliefMatchingContractError(
                    f"unsupported DEM instruction for pinned belief-matching: {inst.type}"
                )
            continue
        detector_parts: list[list[int]] = [[]]
        observable_parts: list[list[int]] = [[]]
        for target in inst.targets_copy():
            if target.is_separator():
                detector_parts.append([])
                observable_parts.append([])
            elif target.is_relative_detector_id():
                detector_parts[-1].append(int(target.val))
            elif target.is_logical_observable_id():
                observable_parts[-1].append(int(target.val))
            else:
                raise BeliefMatchingContractError(f"unsupported DEM target: {target!r}")
        if any(len(set(part)) != len(part) for part in detector_parts + observable_parts):
            raise BeliefMatchingContractError(
                "repeated targets inside a decomposed error component are not safe for pinned upstream parsing"
            )
        edge_supports = [xor(part) for part in detector_parts]
        edge_logicals = [xor(part) for part in observable_parts]
        event_support = xor([d for part in detector_parts for d in part])
        event_logical = xor([o for part in observable_parts for o in part])
        hyperedge_obs.setdefault(event_support, set()).add(event_logical)
        for edge_support, edge_logical in zip(edge_supports, edge_logicals):
            if len(edge_support) > 2:
                raise BeliefMatchingContractError(
                    "each decomposed component must target at most two detectors"
                )
            edge_obs.setdefault(edge_support, set()).add(edge_logical)

    for label, signatures in (("hyperedge", hyperedge_obs), ("edge", edge_obs)):
        conflict = next((support for support, logicals in signatures.items() if len(logicals) > 1), None)
        if conflict is not None:
            raise BeliefMatchingContractError(
                f"pinned upstream implementation aliases {label} detector support "
                f"{tuple(sorted(conflict))} across different observable signatures"
            )


def make_model_identity(*, sampling_circuit, generating_noise_identity: str,
                        decoder_dem, assumed_noise_provenance: str) -> DecoderModelIdentity:
    import stim
    if not isinstance(sampling_circuit, stim.Circuit):
        raise BeliefMatchingContractError("sampling_circuit must be a Stim Circuit")
    if not generating_noise_identity.strip():
        raise BeliefMatchingContractError("generating_noise_identity must be explicit")
    if not assumed_noise_provenance.strip():
        raise BeliefMatchingContractError("assumed_noise_provenance must be explicit")
    n_det = int(decoder_dem.num_detectors)
    n_obs = int(decoder_dem.num_observables)
    if n_det < 1 or n_obs < 1:
        raise BeliefMatchingContractError("DEM must contain detectors and observables")
    if int(sampling_circuit.num_detectors) != n_det:
        raise BeliefMatchingContractError("sampling-circuit detector count differs from decoder DEM")
    if int(sampling_circuit.num_observables) != n_obs:
        raise BeliefMatchingContractError("sampling-circuit observable count differs from decoder DEM")
    circuit_sha = hashlib.sha256(_stim_model_bytes(sampling_circuit)).hexdigest()
    dem_sha = hashlib.sha256(_stim_model_bytes(decoder_dem)).hexdigest()
    return DecoderModelIdentity(
        sampling_circuit_sha256=circuit_sha,
        generating_noise_identity=generating_noise_identity,
        decoder_dem_sha256=dem_sha,
        assumed_noise_provenance=assumed_noise_provenance,
        detector_ids=tuple(range(n_det)),
        observable_ids=tuple(range(n_obs)),
        observable_semantics="Stim OBSERVABLE_INCLUDE parity; output bit 1 predicts the corresponding observable flip",
    )


def _upstream_factory(dem, *, max_bp_iters: int):
    try:
        from beliefmatching import BeliefMatching
        import beliefmatching.belief_matching as upstream_core
    except Exception as exc:  # package import can fail due to native/dependency issues
        raise BeliefMatchingConstructionError(
            f"failed to import pinned beliefmatching dependency: {type(exc).__name__}: {exc}"
        ) from exc
    installed_version = importlib.metadata.version("beliefmatching")
    if installed_version != UPSTREAM_VERSION:
        raise BeliefMatchingConstructionError(
            f"expected beliefmatching {UPSTREAM_VERSION}, found {installed_version}"
        )
    with open(upstream_core.__file__, "rb") as source_file:
        source_digest = hashlib.sha256(source_file.read().replace(b"\r\n", b"\n")).hexdigest()
    if source_digest != UPSTREAM_CORE_SOURCE_SHA256_LF:
        raise BeliefMatchingConstructionError(
            "installed beliefmatching implementation source hash does not match "
            f"pinned commit {UPSTREAM_COMMIT}"
        )
    try:
        return BeliefMatching.from_detector_error_model(dem, max_bp_iters=max_bp_iters)
    except Exception as exc:
        raise BeliefMatchingConstructionError(
            f"upstream construction failed for DEM sha256="
            f"{hashlib.sha256(_stim_model_bytes(dem)).hexdigest()}: {type(exc).__name__}: {exc}"
        ) from exc


class BeliefMatchingAdapter:
    """Batch-decoder adapter returning uint8 [shots, observables] predictions.

    `enabled` defaults to False. Construction of the upstream candidate only
    occurs after explicit enablement. Detector and observable columns retain
    Stim's contiguous D0..Dn-1 and L0..Lm-1 order.
    """

    def __init__(self, decoder, identity: DecoderModelIdentity, *, enabled: bool = False):
        self._decoder = decoder
        self.identity = identity
        self.enabled = bool(enabled)
        self.metadata = None
        self.model_identity = None
        self.sampling_identity = None

    @classmethod
    def from_dem(cls, *, decoder_dem, sampling_circuit, generating_noise_identity: str,
                 assumed_noise_provenance: str, enabled: bool = False,
                 max_bp_iters: int = 20,
                 factory: Callable = _upstream_factory) -> "BeliefMatchingAdapter":
        identity = make_model_identity(
            sampling_circuit=sampling_circuit,
            generating_noise_identity=generating_noise_identity,
            decoder_dem=decoder_dem,
            assumed_noise_provenance=assumed_noise_provenance,
        )
        if max_bp_iters < 1:
            raise BeliefMatchingContractError("max_bp_iters must be positive")
        if not enabled:
            return cls(None, identity, enabled=False)
        validate_upstream_signature_semantics(decoder_dem)
        # BeliefMatching's model matrix has the exact Stim detector/observable
        # dimensions. Its upstream code requires a decomposed DEM.
        try:
            decoder = factory(decoder_dem, max_bp_iters=max_bp_iters)
        except BeliefMatchingConstructionError:
            raise
        except Exception as exc:
            raise BeliefMatchingConstructionError(
                f"belief-matching construction failed: {type(exc).__name__}: {exc}"
            ) from exc
        return cls(decoder, identity, enabled=True)

    def bind_ns2c(self, *, sampling_identity, dem_record,
                  assumed_noise_model_id: str, assumed_noise_provenance: dict,
                  upstream_version: str = "0.2.0",
                  upstream_commit: str = "4458c278bbec273c8c1a26411dadccc49222f8ef"):
        """Bind to the existing qshift_core_v1 identity/decoder contract.

        The caller supplies the canonical NS-2B sampling identity and concrete
        Stim DEM construction record. They remain distinct from this adapter's
        assumed decoder noise model. Returns the corresponding model identity.
        """
        if not self.enabled or self._decoder is None:
            raise BeliefMatchingDisabledError("cannot bind a disabled adapter")
        if upstream_version != UPSTREAM_VERSION or upstream_commit != UPSTREAM_COMMIT:
            raise BeliefMatchingContractError("NS-2C binding must retain the tested upstream version and commit")
        try:
            from qshift_core_v1.contracts import DecoderMetadata
            from qshift_core_v1.sampling_model_identity import DecoderModelIdentity as NS2CModelIdentity
        except Exception as exc:
            raise BeliefMatchingContractError(
                "qshift_core_v1 decoder contract is unavailable: "
                f"{type(exc).__name__}: {exc}"
            ) from exc
        if self.identity.sampling_circuit_sha256 != sampling_identity.circuit_sha256:
            raise BeliefMatchingContractError("sampling circuit identity differs from NS-2C sampling identity")
        if self.identity.generating_noise_identity != sampling_identity.generating_noise_model_id:
            raise BeliefMatchingContractError("generating-noise identity differs from NS-2C sampling identity")
        if self.identity.decoder_dem_sha256 != dem_record.dem_sha256:
            raise BeliefMatchingContractError("decoder DEM identity differs from its construction record")
        if (dem_record.detector_count != len(self.identity.detector_ids)
                or dem_record.observable_count != len(self.identity.observable_ids)):
            raise BeliefMatchingContractError("DEM construction record dimensions differ from the decoder")
        if dem_record.detector_order_sha256 != sampling_identity.detector_order_sha256:
            raise BeliefMatchingContractError("DEM and sampling detector ordering fingerprints differ")
        if dem_record.observable_semantics_sha256 != sampling_identity.observable_semantics_sha256:
            raise BeliefMatchingContractError("DEM and sampling observable semantics differ")
        if not isinstance(assumed_noise_model_id, str) or not assumed_noise_model_id.strip():
            raise BeliefMatchingContractError("assumed_noise_model_id must be explicit")
        if not isinstance(assumed_noise_provenance, dict) or not assumed_noise_provenance:
            raise BeliefMatchingContractError("assumed_noise_provenance must be a nonempty mapping")

        self.metadata = DecoderMetadata(
            name="beliefmatching",
            implementation="official-upstream BeliefMatching",
            version=f"{upstream_version}+{upstream_commit[:12]}",
            detector_count=dem_record.detector_count,
            observable_count=dem_record.observable_count,
            noise_model_id=assumed_noise_model_id,
            correlation_mode=None,
            experimental=True,
            construction_provenance=(
                f"BeliefMatching {upstream_version} at {upstream_commit}; "
                f"decomposed Stim DEM sha256={dem_record.dem_sha256}"
            ),
        )
        self.model_identity = NS2CModelIdentity.create(
            sampling_identity,
            self.metadata,
            dem_record=dem_record,
            decoder_assumed_noise_model_id=assumed_noise_model_id,
            decoder_assumed_noise_provenance=assumed_noise_provenance,
            correlation_semantics=None,
            requires_detector_coordinates=False,
            static_resource_sha256=(),
            static_resource_note="No learned weights; concrete decomposed DEM is retained in dem_record.",
        )
        self.sampling_identity = sampling_identity
        return self.model_identity

    def decode_batch(self, syndromes: np.ndarray, *, detector_ids: Sequence[int] | None = None,
                     observable_ids: Sequence[int] | None = None) -> np.ndarray:
        if not self.enabled or self._decoder is None:
            raise BeliefMatchingDisabledError("belief-matching adapter is disabled by default")
        if detector_ids is not None and tuple(detector_ids) != self.identity.detector_ids:
            raise BeliefMatchingContractError("detector column IDs/order mismatch")
        if observable_ids is not None and tuple(observable_ids) != self.identity.observable_ids:
            raise BeliefMatchingContractError("observable IDs/order mismatch")
        x = np.asarray(syndromes)
        n_det = len(self.identity.detector_ids)
        n_obs = len(self.identity.observable_ids)
        if x.ndim != 2 or x.shape[1] != n_det:
            raise BeliefMatchingContractError(f"syndromes must have shape [shots,{n_det}]")
        if x.dtype.kind not in "biuf" or not np.isfinite(x).all() or np.any((x != 0) & (x != 1)):
            raise BeliefMatchingContractError("syndromes must contain only finite binary values")
        predictions = np.asarray(self._decoder.decode_batch(np.array(x, dtype=np.uint8, copy=True)))
        if predictions.shape != (x.shape[0], n_obs):
            raise BeliefMatchingContractError(
                f"upstream predictions must have shape {(x.shape[0], n_obs)}, got {predictions.shape}"
            )
        if predictions.dtype.kind not in "biuf" or not np.isfinite(predictions).all():
            raise BeliefMatchingContractError("upstream predictions must be finite binary values")
        if np.any((predictions != 0) & (predictions != 1)):
            raise BeliefMatchingContractError("upstream predictions contain nonbinary values")
        return np.array(predictions, dtype=np.uint8, copy=True)

    def decode(self, detectors: np.ndarray):
        """NS-2C DecoderProtocol entry point: detector matrix to predictions."""
        if self.metadata is None or self.model_identity is None or self.sampling_identity is None:
            raise BeliefMatchingContractError("bind_ns2c must be called before NS-2C protocol use")
        try:
            from qshift_core_v1.contracts import DecoderPrediction
        except Exception as exc:
            raise BeliefMatchingContractError(
                f"qshift_core_v1 DecoderPrediction unavailable: {type(exc).__name__}: {exc}"
            ) from exc
        import time
        started = time.perf_counter()
        bits = self.decode_batch(
            detectors,
            detector_ids=self.identity.detector_ids,
            observable_ids=self.identity.observable_ids,
        )
        return DecoderPrediction(
            bits, self.metadata, elapsed_seconds=max(0.0, time.perf_counter() - started)
        )

    def close(self) -> None:
        """Release the adapter's reference; upstream exposes no close method."""
        decoder = self._decoder
        self._decoder = None
        self.enabled = False
        close = getattr(decoder, "close", None)
        if callable(close):
            close()

    def __enter__(self):
        if not self.enabled:
            raise BeliefMatchingDisabledError("belief-matching adapter is disabled by default")
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False
