"""Opt-in NS-3B BeliefMatching registration through the NS-2C runtime.

This module composes the published adapter; it does not alter its collision
guard or its model. Construction is intentionally gated twice: callers must
request this function with ``experimental_opt_in=True``, and the NS-2C bank
must accept experimental registration.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import time
from numbers import Integral
from typing import Any, Mapping

import stim

from qshift_core_v1.decoder_runtime_v2 import CheckedDecoderAdapter, CompatibilityAwareDecoderBank
from qshift_core_v1.sampling_model_identity import (
    DEMConstructionSettingsV2,
    DecoderModelIdentity,
    SamplingIdentity,
    StimDEMArtifact,
)

from .beliefmatching_adapter_ns3b import BeliefMatchingAdapter


EXPECTED_UPSTREAM_VERSION = "0.2.0"
EXPECTED_UPSTREAM_COMMIT = "4458c278bbec273c8c1a26411dadccc49222f8ef"


@dataclass(frozen=True)
class BeliefMatchingRegistration:
    """Created registration plus measured adapter/identity construction time."""

    adapter: BeliefMatchingAdapter
    checked_adapter: CheckedDecoderAdapter
    model_identity: DecoderModelIdentity
    construction_seconds: float


def register_beliefmatching(
    bank: CompatibilityAwareDecoderBank,
    *,
    sampling_circuit: stim.Circuit,
    sampling_identity: SamplingIdentity,
    dem_artifact: StimDEMArtifact,
    assumed_noise_model_id: str,
    assumed_noise_provenance: Mapping[str, Any],
    information_reference_decoder: str,
    experimental_opt_in: bool = False,
    max_bp_iters: int = 20,
) -> BeliefMatchingRegistration:
    """Construct, NS-2C-bind, and register the experimental candidate.

    The concrete decomposed DEM must have been built with the NS-3B handoff's
    ``decompose_errors=True, approximate_disjoint_errors=True`` conversion.
    Caller-supplied provenance is serialized identically into the upstream and
    NS-2C model identities. ``information_reference_decoder`` names an already
    registered comparator; its sampling identity, concrete DEM digest, and
    declared noise model/provenance must match. This verifies declared
    information parity, not equivalence of decoder representations. The
    upstream detector-support/logical-signature guard is invoked unchanged.
    """
    if type(experimental_opt_in) is not bool or not experimental_opt_in:
        raise PermissionError("BeliefMatching construction requires experimental_opt_in=True.")
    if not isinstance(bank, CompatibilityAwareDecoderBank):
        raise TypeError("bank must be a CompatibilityAwareDecoderBank.")
    if not isinstance(sampling_identity, SamplingIdentity):
        raise TypeError("sampling_identity must be SamplingIdentity.")
    if not isinstance(sampling_circuit, stim.Circuit):
        raise TypeError("sampling_circuit must be a Stim Circuit.")
    if not isinstance(dem_artifact, StimDEMArtifact):
        raise TypeError("dem_artifact must be a verified StimDEMArtifact.")
    if bank.sampling_identity.identity_sha256 != sampling_identity.identity_sha256:
        raise ValueError("Decoder bank and supplied sampling identity differ.")
    if hashlib.sha256(str(sampling_circuit).encode("utf-8")).hexdigest() != sampling_identity.circuit_sha256:
        raise ValueError("Sampling circuit does not match the declared SamplingIdentity.")
    if str(stim.__version__) != sampling_identity.stim_version:
        raise ValueError("Installed Stim version differs from the SamplingIdentity.")
    settings = dem_artifact.record.settings
    if not isinstance(settings, DEMConstructionSettingsV2):
        raise TypeError("DEM record lacks NS-2B DEMConstructionSettingsV2.")
    if settings.decompose_errors is not True or type(settings.approximate_disjoint_errors) is not bool or settings.approximate_disjoint_errors is not True:
        raise ValueError(
            "BeliefMatching integration requires the declared decomposed DEM with "
            "approximate_disjoint_errors=True."
        )
    if (settings.flatten_loops or settings.allow_gauge_detectors
            or settings.ignore_decomposition_failures
            or settings.block_decomposition_from_introducing_remnant_edges):
        raise ValueError("Unsupported DEM conversion flags for the validated NS-3B integration.")
    if not isinstance(assumed_noise_model_id, str) or not assumed_noise_model_id.strip():
        raise ValueError("assumed_noise_model_id must be explicit.")
    if not isinstance(assumed_noise_provenance, Mapping) or not assumed_noise_provenance:
        raise ValueError("assumed_noise_provenance must be a nonempty mapping.")
    if (isinstance(max_bp_iters, bool) or not isinstance(max_bp_iters, Integral)
            or max_bp_iters < 1):
        raise ValueError("max_bp_iters must be a positive integer.")
    try:
        provenance_json = json.dumps(
            dict(assumed_noise_provenance), sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("assumed_noise_provenance must be finite JSON-compatible data.") from exc
    if not isinstance(information_reference_decoder, str) or not information_reference_decoder.strip():
        raise ValueError("An information_reference_decoder must be explicitly named.")
    try:
        reference_model = bank.adapter(information_reference_decoder).model_identity
    except KeyError as exc:
        raise ValueError(
            f"Information reference decoder {information_reference_decoder!r} is not registered."
        ) from exc
    if reference_model.sampling_identity_sha256 != sampling_identity.identity_sha256:
        raise ValueError("Information reference targets a different sampling identity.")
    if reference_model.dem_record.dem_sha256 != dem_artifact.record.dem_sha256:
        raise ValueError("BeliefMatching and information reference must use the same concrete DEM.")
    if reference_model.decoder_assumed_noise_model_id != assumed_noise_model_id:
        raise ValueError("BeliefMatching and information reference noise-model IDs differ.")
    if reference_model.decoder_assumed_noise_provenance_json != provenance_json:
        raise ValueError("BeliefMatching and information reference noise provenance differ.")

    started = time.perf_counter()
    adapter: BeliefMatchingAdapter | None = None
    try:
        adapter = BeliefMatchingAdapter.from_dem(
            decoder_dem=dem_artifact.dem,
            sampling_circuit=sampling_circuit,
            generating_noise_identity=sampling_identity.generating_noise_model_id,
            assumed_noise_provenance=provenance_json,
            enabled=True,
            max_bp_iters=int(max_bp_iters),
        )
        model = adapter.bind_ns2c(
            sampling_identity=sampling_identity,
            dem_record=dem_artifact.record,
            assumed_noise_model_id=assumed_noise_model_id,
            assumed_noise_provenance=dict(assumed_noise_provenance),
            upstream_version=EXPECTED_UPSTREAM_VERSION,
            upstream_commit=EXPECTED_UPSTREAM_COMMIT,
        )
        checked = CheckedDecoderAdapter(
            adapter, model_identity=model, sampling_identity=sampling_identity,
        )
        bank.register(checked, experimental_opt_in=True)
        elapsed = max(0.0, time.perf_counter() - started)
        if not math.isfinite(elapsed):
            raise RuntimeError("Nonfinite construction duration.")
        return BeliefMatchingRegistration(adapter, checked, model, elapsed)
    except Exception:
        if adapter is not None:
            adapter.close()
        raise
