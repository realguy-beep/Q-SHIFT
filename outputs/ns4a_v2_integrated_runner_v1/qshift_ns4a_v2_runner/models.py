"""Approved NS-4A V2 circuits and immutable decoder-model construction."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import stim

from qshift_core_v1.contracts import DecoderMetadata
from qshift_core_v1.pymatching_adapter import PyMatchingDecoder
from qshift_core_v1.research_adapters.beliefmatching_adapter_ns3b import (
    validate_upstream_signature_semantics,
)
from qshift_core_v1.sampling_model_identity import (
    DEMConstructionSettingsV2,
    DecoderModelIdentity,
    SamplingIdentity,
    StimDEMArtifact,
)

from .protocol import CANDIDATE_IDS, CONDITIONS, MODES


PACKAGE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PACKAGE_DIR.parent
REPO_ROOT = OUTPUT_DIR.parents[1]
CONFIG_PATH = REPO_ROOT / "outputs" / "qshift_ns4a_pilot_protocol_v2" / "proposed_config_v2.json"
PHASE3A_DIR = REPO_ROOT / "outputs" / "phase3a_correlated_noise_preflight"
if str(PHASE3A_DIR) not in sys.path:
    sys.path.insert(0, str(PHASE3A_DIR))

from simulator import build_spatial_burst_circuit  # noqa: E402


OBSERVABLE_MEANING = "Stim OBSERVABLE_INCLUDE parity; bit 1 denotes a logical-observable flip"
DEM_SETTINGS = DEMConstructionSettingsV2(
    decompose_errors=True,
    approximate_disjoint_errors=True,
    construction_note="NS-4A V2 frozen settings: Stim Circuit.detector_error_model",
)


class ModelConstructionError(RuntimeError):
    """A frozen candidate could not be constructed without interpretation."""


@dataclass(frozen=True)
class ConditionModel:
    condition_id: str
    circuit: Any
    sampling_identity: SamplingIdentity
    generating_provenance: dict[str, Any]
    dem_artifact: StimDEMArtifact
    assumed_noise_model_id: str
    assumed_noise_provenance: dict[str, Any]


@dataclass(frozen=True)
class ModelCatalog:
    config: dict[str, Any]
    conditions: dict[str, ConditionModel]
    selection_decoders: dict[str, PyMatchingDecoder]
    selection_model_identities_by_condition: dict[str, dict[str, DecoderModelIdentity]]

    def dem_identity_manifest(self) -> dict[str, Any]:
        return {
            "schema": "qshift-ns4a-v2-dem-identity-manifest-v1",
            "conditions": list(CONDITIONS),
            "dem_settings": DEM_SETTINGS.stim_kwargs(),
            "by_condition": {
                condition: {
                    "source_circuit_sha256": row.dem_artifact.record.source_circuit_sha256,
                    "sampling_identity_sha256": row.sampling_identity.identity_sha256,
                    "dem_sha256": row.dem_artifact.record.dem_sha256,
                    "detector_count": row.dem_artifact.record.detector_count,
                    "observable_count": row.dem_artifact.record.observable_count,
                    "detector_order_sha256": row.dem_artifact.record.detector_order_sha256,
                    "observable_semantics_sha256": row.dem_artifact.record.observable_semantics_sha256,
                    "stim_version": row.dem_artifact.record.stim_version,
                    "alias_guard": "PASS",
                }
                for condition, row in self.conditions.items()
            },
            "selection_candidate_order": list(CANDIDATE_IDS),
            "candidate_to_dem_mode": {
                candidate: {
                    "dem_sha256": self.conditions[candidate.split("::", 1)[0]].dem_artifact.record.dem_sha256,
                    "correlation_mode": candidate.endswith("correlation_enabled_pymatching"),
                }
                for candidate in CANDIDATE_IDS
            },
            "beliefmatching_uses_selected_dem_and_same_assumed_noise_provenance_as_selected_pm": True,
        }


def _condition_fields(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = config["experiment"]["selection_conditions"]
    result = {row["id"]: dict(row) for row in rows}
    if tuple(result) != CONDITIONS:
        raise ModelConstructionError("V2 condition order differs from the accepted deterministic protocol module.")
    expected = {
        "balanced_no_burst": ("balanced", 0.0),
        "x_biased_no_burst": ("x_biased", 0.0),
        "z_biased_no_burst": ("z_biased", 0.0),
        "balanced_burst_0.005": ("balanced", 0.005),
        "balanced_burst_0.010": ("balanced", 0.010),
        "balanced_burst_0.015": ("balanced", 0.015),
    }
    for condition, (regime, burst) in expected.items():
        row = result[condition]
        if row.get("regime") != regime or float(row.get("burst_probability", -1)) != burst:
            raise ModelConstructionError(f"V2 condition parameters changed for {condition}.")
    if config["experiment"].get("evaluation_conditions") != rows:
        raise ModelConstructionError("Selection and evaluation condition rosters differ.")
    return result


def _provenance(config: dict[str, Any], condition: dict[str, Any]) -> dict[str, Any]:
    exp = config["experiment"]
    generator = exp["generator"]
    return {
        "schema": "qshift-ns4a-assumed-noise-v2",
        "condition_id": condition["id"],
        "source": "Phase 2B categorical Pauli generator + Phase 3A spatial-burst extension",
        "memory_basis": exp["circuit"]["memory_basis"],
        "distance": exp["circuit"]["distance"],
        "rounds": exp["circuit"]["rounds"],
        "gate_fault_probability": generator["gate_fault_probability"],
        "measurement_flip_probability": generator["measurement_flip_probability"],
        "bias_ratio": generator["bias_ratio"],
        "pauli_regime": condition["regime"],
        "burst_probability_per_mr_boundary": condition["burst_probability"],
        "burst_pair_data_qubits": generator["burst_pair_data_qubits"],
        "burst_events_independent_across_rounds": generator["round_events_independent"],
        "dem_settings": {
            "decompose_errors": True,
            "approximate_disjoint_errors": True,
            "flatten_loops": False,
            "allow_gauge_detectors": False,
            "ignore_decomposition_failures": False,
            "block_decomposition_from_introducing_remnant_edges": False,
        },
    }


def load_frozen_config(path: str | Path = CONFIG_PATH) -> dict[str, Any]:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    exp = payload.get("experiment")
    if (payload.get("schema") != "qshift-ns4a-proposed-pilot-v2"
            or not isinstance(exp, dict)
            or payload.get("sampling_authorized") is not False
            or payload.get("sampling_performed") is not False):
        raise ModelConstructionError("Expected the still-unauthorized NS-4A V2 configuration.")
    if exp["allocation"].get("total_unique_shots") != 304_000:
        raise ModelConstructionError("V2 total-shot allocation changed from 304,000.")
    circuit = exp.get("circuit", {})
    expected_circuit = {
        "code_family": "Stim rotated surface-code memory", "memory_basis": "z",
        "distance": 3, "rounds": 5, "detectors": 40, "observables": 1,
        "stim_version_required": "1.16.0",
    }
    if circuit != expected_circuit:
        raise ModelConstructionError("V2 circuit identity/configuration differs from the approved d=3, five-round circuit.")
    generator = exp.get("generator", {})
    if (generator.get("gate_fault_probability") != 0.003
            or generator.get("measurement_flip_probability") != 0.003
            or generator.get("bias_ratio") != 10.0
            or generator.get("burst_pair_data_qubits") != [8, 10]
            or generator.get("round_events_independent") is not True
            or generator.get("burst_boundaries_per_shot") != 5):
        raise ModelConstructionError("V2 generator probabilities, burst pair, or round assumptions changed.")
    allocation = exp.get("allocation", {})
    expected_allocation = {
        "selection_roots_per_condition": 8,
        "selection_condition_count": 6,
        "selection_unique_shots": 64_000,
        "evaluation_roots_per_condition": 10,
        "evaluation_shots_per_root": 4_000,
        "evaluation_condition_count": 6,
        "evaluation_unique_shots": 240_000,
        "total_unique_shots": 304_000,
        "hard_shot_ceiling": 304_000,
    }
    if any(allocation.get(key) != value for key, value in expected_allocation.items()):
        raise ModelConstructionError("V2 root/shot allocation differs from the frozen 64k/240k/304k design.")
    decoder_models = exp.get("decoder_models", {})
    if decoder_models.get("dem_settings") != {"decompose_errors": True, "approximate_disjoint_errors": True}:
        raise ModelConstructionError("V2 DEM conversion settings changed.")
    if decoder_models.get("selection_grid_size") != 12 or decoder_models.get("beliefmatching_experimental_opt_in_required") is not True:
        raise ModelConstructionError("V2 decoder-grid size or BeliefMatching opt-in changed.")
    grid_families = tuple(decoder_models.get("selection_grid_model_families", ()))
    family_aliases = {
        "balanced_burst_probability_0.005": "balanced_burst_0.005",
        "balanced_burst_probability_0.010": "balanced_burst_0.010",
        "balanced_burst_probability_0.015": "balanced_burst_0.015",
    }
    normalized_families = tuple(family_aliases.get(name, name) for name in grid_families)
    if normalized_families != CONDITIONS or tuple(decoder_models.get("selection_modes", ())) != MODES:
        raise ModelConstructionError("V2 candidate model-family/mode roster does not match the deterministic 12-candidate grid.")
    if exp.get("primary_endpoint", {}).get("confirmatory") is not False:
        raise ModelConstructionError("NS-4A V2 must remain exploratory, not confirmatory.")
    if exp.get("statistics", {}).get("root_stratified_bootstrap_resamples") != 100_000:
        raise ModelConstructionError("V2 primary bootstrap replicate count changed.")
    if tuple(exp["arms"]) != tuple(__import__("qshift_ns4a_v2_deterministic.protocol", fromlist=["EVALUATION_ARMS"]).EVALUATION_ARMS):
        raise ModelConstructionError("V2 evaluation-arm order changed.")
    _condition_fields(payload)
    return payload


def build_model_catalog(config_path: str | Path = CONFIG_PATH) -> ModelCatalog:
    """Construct six DEMs and the frozen 12-candidate PyMatching grid.

    This function constructs circuits/DEMs and decoder objects only. It does
    not call Stim samplers or create random detector/observable events.
    """
    config = load_frozen_config(config_path)
    exp = config["experiment"]
    circuit_spec = exp["circuit"]
    generator = exp["generator"]
    by_condition = _condition_fields(config)
    conditions: dict[str, ConditionModel] = {}
    artifacts: dict[str, StimDEMArtifact] = {}
    assumed: dict[str, tuple[str, dict[str, Any]]] = {}

    for condition_id in CONDITIONS:
        row = by_condition[condition_id]
        circuit = build_spatial_burst_circuit(
            memory_basis=circuit_spec["memory_basis"],
            regime=row["regime"],
            distance=circuit_spec["distance"],
            rounds=circuit_spec["rounds"],
            gate_p=generator["gate_fault_probability"],
            measurement_p=generator["measurement_flip_probability"],
            bias_ratio=generator["bias_ratio"],
            burst_probability=row["burst_probability"],
            burst_pair=tuple(generator["burst_pair_data_qubits"]),
        )
        if (int(circuit.num_detectors) != circuit_spec["detectors"]
                or int(circuit.num_observables) != circuit_spec["observables"]):
            raise ModelConstructionError(f"{condition_id} circuit violates frozen detector/observable dimensions.")
        provenance = _provenance(config, row)
        sampling_identity = SamplingIdentity.from_stim(
            circuit,
            generating_noise_model_id=f"ns4a-v2-generating:{condition_id}",
            generating_noise_provenance=provenance,
            code_family=circuit_spec["code_family"],
            distance=circuit_spec["distance"],
            rounds=circuit_spec["rounds"],
            memory_basis=circuit_spec["memory_basis"],
            observable_interpretations=(OBSERVABLE_MEANING,),
            observable_polarities=(1,),
        )
        artifact = StimDEMArtifact.build(
            circuit,
            DEM_SETTINGS,
            observable_interpretations=(OBSERVABLE_MEANING,),
            observable_polarities=(1,),
        )
        dem = artifact.dem
        if int(dem.num_detectors) != 40 or int(dem.num_observables) != 1:
            raise ModelConstructionError(f"{condition_id} DEM violates [40 detectors,1 observable].")
        # The exact unchanged NS-3B guard must accept all six grid DEMs.
        validate_upstream_signature_semantics(dem)
        assumed_id = f"ns4a-v2-assumed:{condition_id}"
        artifacts[condition_id] = artifact
        assumed[condition_id] = (assumed_id, provenance)
        conditions[condition_id] = ConditionModel(
            condition_id, circuit, sampling_identity, provenance, artifact,
            assumed_id, provenance,
        )

    import pymatching
    selection_decoders: dict[str, PyMatchingDecoder] = {}
    selection_identities: dict[str, dict[str, DecoderModelIdentity]] = {
        condition: {} for condition in CONDITIONS
    }
    for model_condition in CONDITIONS:
        artifact = artifacts[model_condition]
        assumed_id, provenance = assumed[model_condition]
        for mode in MODES:
            correlated = mode == "correlation_enabled_pymatching"
            candidate_id = f"{model_condition}::{mode}"
            decoder = PyMatchingDecoder.from_detector_error_model(
                artifact.dem,
                correlation_mode=correlated,
                name=candidate_id,
                noise_model_id=assumed_id,
            )
            selection_decoders[candidate_id] = decoder
            for generation_condition in CONDITIONS:
                sampling = conditions[generation_condition].sampling_identity
                identity = DecoderModelIdentity.create(
                    sampling,
                    decoder.metadata,
                    dem_record=artifact.record,
                    decoder_assumed_noise_model_id=assumed_id,
                    decoder_assumed_noise_provenance=provenance,
                    correlation_semantics=(
                        "PyMatching correlations enabled at construction and decode_batch"
                        if correlated else "PyMatching correlations disabled at construction and decode_batch"
                    ),
                    static_resource_note=f"Concrete Stim DEM {artifact.record.dem_sha256}; candidate {candidate_id}.",
                )
                selection_identities[generation_condition][candidate_id] = identity

    if tuple(selection_decoders) != CANDIDATE_IDS:
        raise ModelConstructionError("Constructed selection grid order differs from the frozen 12-candidate roster.")
    return ModelCatalog(config, conditions, selection_decoders, selection_identities)


def build_evaluation_bank(catalog: ModelCatalog, condition_id: str, selected_candidate: str):
    """Bind the five fixed evaluation arms to one generating identity."""
    from qshift_core_v1.decoder_runtime_v2 import CheckedDecoderAdapter, CompatibilityAwareDecoderBank
    from qshift_core_v1.research_adapters.beliefmatching_integration_ns2d import register_beliefmatching

    if condition_id not in catalog.conditions or selected_candidate not in CANDIDATE_IDS:
        raise ValueError("Unknown generating condition or selected candidate.")
    sampling = catalog.conditions[condition_id].sampling_identity
    sampling_circuit = catalog.conditions[condition_id].circuit
    selected_family, selected_mode = selected_candidate.split("::", 1)
    other_mode = MODES[1] if selected_mode == MODES[0] else MODES[0]
    model_specs = (
        ("nominal_ordinary_pymatching", CONDITIONS[0], MODES[0]),
        ("nominal_correlation_enabled_pymatching", CONDITIONS[0], MODES[1]),
        ("pooled_selected_fixed_pymatching", selected_family, selected_mode),
        ("matched_selected_dem_pymatching_other_mode_control", selected_family, other_mode),
    )
    bank = CompatibilityAwareDecoderBank(sampling)
    for arm, family, mode in model_specs:
        condition_model = catalog.conditions[family]
        correlated = mode == MODES[1]
        noise_id = condition_model.assumed_noise_model_id
        decoder = PyMatchingDecoder.from_detector_error_model(
            condition_model.dem_artifact.dem,
            correlation_mode=correlated,
            name=arm,
            noise_model_id=noise_id,
        )
        identity = DecoderModelIdentity.create(
            sampling,
            decoder.metadata,
            dem_record=condition_model.dem_artifact.record,
            decoder_assumed_noise_model_id=noise_id,
            decoder_assumed_noise_provenance=condition_model.assumed_noise_provenance,
            correlation_semantics=(
                "PyMatching correlations enabled at construction and decode_batch"
                if correlated else "PyMatching correlations disabled at construction and decode_batch"
            ),
            static_resource_note=f"Concrete Stim DEM {condition_model.dem_artifact.record.dem_sha256}; evaluation arm {arm}.",
        )
        checked = CheckedDecoderAdapter(decoder, model_identity=identity, sampling_identity=sampling)
        bank.register(checked)

    selected_model = catalog.conditions[selected_family]
    registration = register_beliefmatching(
        bank,
        sampling_circuit=sampling_circuit,
        sampling_identity=sampling,
        dem_artifact=selected_model.dem_artifact,
        assumed_noise_model_id=selected_model.assumed_noise_model_id,
        assumed_noise_provenance=selected_model.assumed_noise_provenance,
        information_reference_decoder="pooled_selected_fixed_pymatching",
        experimental_opt_in=True,
    )
    expected_registered = (
        "nominal_ordinary_pymatching",
        "nominal_correlation_enabled_pymatching",
        "pooled_selected_fixed_pymatching",
        "matched_selected_dem_pymatching_other_mode_control",
        "beliefmatching",
    )
    if tuple(sorted(bank.names())) != tuple(sorted(expected_registered)):
        registration.adapter.close()
        raise ModelConstructionError(f"Registered implementations differ from the four PyMatching models plus NS-3B name: {bank.names()!r}.")
    return bank, registration


def evaluation_decoder_views(bank: Any, circuit: Any) -> dict[str, Any]:
    """Map registered implementation names explicitly to frozen arm labels."""
    from .runner import _CheckedDecoderView

    registered_by_arm = {
        "nominal_ordinary_pymatching": "nominal_ordinary_pymatching",
        "nominal_correlation_enabled_pymatching": "nominal_correlation_enabled_pymatching",
        "pooled_selected_fixed_pymatching": "pooled_selected_fixed_pymatching",
        "matched_selected_dem_pymatching_other_mode_control": "matched_selected_dem_pymatching_other_mode_control",
        "beliefmatching_same_selected_dem": "beliefmatching",
    }
    if set(registered_by_arm) != set(__import__("qshift_ns4a_v2_deterministic.protocol", fromlist=["EVALUATION_ARMS"]).EVALUATION_ARMS):
        raise ModelConstructionError("Explicit implementation-to-arm map differs from frozen arm roster.")
    return {arm: _CheckedDecoderView(bank.adapter(registered), circuit)
            for arm, registered in registered_by_arm.items()}
