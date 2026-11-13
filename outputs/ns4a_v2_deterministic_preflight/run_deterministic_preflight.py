from __future__ import annotations

import hashlib
import importlib.metadata
import importlib.util
import json
import platform
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pymatching
import stim

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PHASE2B = ROOT / "outputs" / "phase2b_pauli_bias"
PHASE3A = ROOT / "outputs" / "phase3a_correlated_noise_preflight"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(PHASE2B) not in sys.path:
    sys.path.insert(0, str(PHASE2B))
if str(PHASE3A) not in sys.path:
    sys.path.insert(0, str(PHASE3A))

from simulator import build_spatial_burst_circuit
from qshift_core_v1.circuit_identity import CircuitIdentity, DEMConstructionSettings
from qshift_core_v1.contracts import DecoderMetadata, DecoderPrediction
from qshift_core_v1.decoder_runtime_v2 import (
    CheckedDecoderAdapter,
    CompatibilityAwareDecoderBank,
    evaluate_paired_batch,
)
from qshift_core_v1.pymatching_adapter import PyMatchingDecoder
from qshift_core_v1.research_adapters.beliefmatching_adapter_ns3b import (
    BeliefMatchingAdapter,
    BeliefMatchingConstructionError,
    BeliefMatchingContractError,
    make_model_identity,
    validate_upstream_signature_semantics,
)
from qshift_core_v1.research_adapters.beliefmatching_integration_ns2d import register_beliefmatching
from qshift_core_v1.sampling_model_identity import (
    DEMConstructionSettingsV2,
    DecoderModelIdentity,
    SamplingIdentity,
    StimDEMArtifact,
    TrustedDetectorBatchAdapter,
    assert_model_compatible,
)

CONFIG_PATH = OUT.parent / "qshift_ns4a_pilot_protocol_v2" / "proposed_config_v2.json"
CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
EXP = CONFIG["experiment"]
GEN = EXP["generator"]
SETTINGS = DEMConstructionSettingsV2(
    decompose_errors=True,
    approximate_disjoint_errors=True,
    construction_note="NS-4A V2 requested preflight: Stim detector_error_model",
)
OBSERVABLE_MEANING = "Stim OBSERVABLE_INCLUDE parity; bit 1 denotes predicted logical-observable flip"
SYNTHETIC = np.zeros((3, 40), dtype=np.uint8)
SYNTHETIC[1, [0, 3, 7]] = 1
SYNTHETIC[2, [12, 19, 34]] = 1


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def instruction_signature(circuit: stim.Circuit) -> str:
    rows = []
    ignored = {"CORRELATED_ERROR", "E"}
    probability_instructions = {
        "PAULI_CHANNEL_1", "PAULI_CHANNEL_2", "X_ERROR", "Z_ERROR",
        "DEPOLARIZE1", "DEPOLARIZE2",
    }
    for inst in circuit.flattened():
        if inst.name in ignored:
            continue
        targets = tuple(str(t) for t in inst.targets_copy())
        args = () if inst.name in probability_instructions else tuple(inst.gate_args_copy())
        rows.append((inst.name, targets, args))
    return sha256(json.dumps(rows, separators=(",", ":"), ensure_ascii=False).encode())


def build_provenance(condition: dict) -> tuple[str, dict, str]:
    model_id = f"ns4a-v2-assumed:{condition['id']}"
    provenance = {
        "schema": "qshift-ns4a-assumed-noise-v2",
        "condition_id": condition["id"],
        "source": "Phase 2B categorical Pauli generator + Phase 3A spatial-burst extension",
        "memory_basis": EXP["circuit"]["memory_basis"],
        "distance": EXP["circuit"]["distance"],
        "rounds": EXP["circuit"]["rounds"],
        "gate_fault_probability": GEN["gate_fault_probability"],
        "measurement_flip_probability": GEN["measurement_flip_probability"],
        "bias_ratio": GEN["bias_ratio"],
        "pauli_regime": condition["regime"],
        "burst_probability_per_mr_boundary": condition["burst_probability"],
        "burst_pair_data_qubits": GEN["burst_pair_data_qubits"],
        "burst_events_independent_across_rounds": GEN["round_events_independent"],
        "dem_settings": {
            "decompose_errors": True,
            "approximate_disjoint_errors": True,
        },
    }
    encoded = json.dumps(provenance, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return model_id, provenance, encoded


class FakeUpstreamDecoder:
    def decode_batch(self, detectors: np.ndarray) -> np.ndarray:
        return np.zeros((detectors.shape[0], 1), dtype=np.uint8)


class InputSpy:
    def __init__(self, metadata: DecoderMetadata):
        self.metadata = metadata
        self.seen: list[bytes] = []
        self.seen_shapes: list[tuple[int, ...]] = []

    def decode(self, detectors: np.ndarray) -> DecoderPrediction:
        array = np.asarray(detectors)
        self.seen.append(array.tobytes(order="C"))
        self.seen_shapes.append(tuple(array.shape))
        return DecoderPrediction(np.zeros((len(array), 1), dtype=np.uint8), self.metadata, 0.0)


def main() -> int:
    if CONFIG.get("sampling_authorized") is not False or CONFIG.get("sampling_performed") is not False:
        raise RuntimeError("V2 configuration crossed its sampling authorization boundary.")
    if EXP["allocation"]["total_unique_shots"] != 304000:
        raise RuntimeError("Unexpected V2 allocation value.")
    if len(EXP["evaluation_conditions"]) != 6:
        raise RuntimeError("Expected exactly six V2 evaluation conditions.")
    expected_settings = {
        "decompose_errors": True,
        "flatten_loops": False,
        "allow_gauge_detectors": False,
        "approximate_disjoint_errors": True,
        "ignore_decomposition_failures": False,
        "block_decomposition_from_introducing_remnant_edges": False,
    }
    if SETTINGS.stim_kwargs() != expected_settings:
        raise RuntimeError(f"DEM settings differ from the V2 protocol: {SETTINGS.stim_kwargs()}")

    env = {
        "python": platform.python_version(),
        "stim": stim.__version__,
        "pymatching": pymatching.__version__,
        "numpy": np.__version__,
        "beliefmatching_spec": importlib.util.find_spec("beliefmatching") is not None,
    }
    try:
        env["beliefmatching_distribution"] = importlib.metadata.version("beliefmatching")
    except importlib.metadata.PackageNotFoundError:
        env["beliefmatching_distribution"] = None

    rows: list[dict] = []
    circuits: list[stim.Circuit] = []
    sampling_ids: list[SamplingIdentity] = []
    artifacts: list[StimDEMArtifact] = []
    structure_hashes: list[str] = []
    detector_order_hashes: list[str] = []
    dem_order_hashes: list[str] = []
    observable_hashes: list[str] = []
    failure_tests = {
        "input_spy_receives_detector_only": False,
        "wrong_detector_order_rejected": False,
        "wrong_detector_shape_rejected": False,
        "experimental_opt_in_false_rejected_without_registration": False,
        "missing_dependency_failure_leaves_bank_unchanged": False,
    }

    for condition in EXP["evaluation_conditions"]:
        condition_id = condition["id"]
        model_id, provenance, provenance_json = build_provenance(condition)
        circuit = build_spatial_burst_circuit(
            memory_basis=EXP["circuit"]["memory_basis"],
            regime=condition["regime"],
            distance=EXP["circuit"]["distance"],
            rounds=EXP["circuit"]["rounds"],
            gate_p=GEN["gate_fault_probability"],
            measurement_p=GEN["measurement_flip_probability"],
            bias_ratio=GEN["bias_ratio"],
            burst_probability=condition["burst_probability"],
            burst_pair=tuple(GEN["burst_pair_data_qubits"]),
        )
        flat = circuit.flattened()
        counts = Counter(inst.name for inst in flat)
        mr_count = counts["MR"]
        burst_count = counts["CORRELATED_ERROR"] + counts["E"]
        expected_bursts = EXP["circuit"]["rounds"] if condition["burst_probability"] > 0 else 0
        circuit_ok = (
            circuit.num_detectors == 40
            and circuit.num_observables == 1
            and mr_count == EXP["circuit"]["rounds"]
            and burst_count == expected_bursts
            and counts["PAULI_CHANNEL_1"] > 0
            and counts["PAULI_CHANNEL_2"] > 0
        )
        if not circuit_ok:
            raise RuntimeError(
                f"{condition_id}: circuit invariant failure: detectors={circuit.num_detectors}, "
                f"observables={circuit.num_observables}, MR={mr_count}, bursts={burst_count}, "
                f"expected_bursts={expected_bursts}"
            )
        structure_hash = instruction_signature(circuit)
        sampling = SamplingIdentity.from_stim(
            circuit,
            generating_noise_model_id=f"ns4a-v2-generating:{condition_id}",
            generating_noise_provenance=provenance,
            code_family="stim:surface_code:rotated_memory_z",
            distance=3,
            rounds=5,
            memory_basis="z",
            observable_interpretations=(OBSERVABLE_MEANING,),
            observable_polarities=(1,),
        )
        artifact = StimDEMArtifact.build(
            circuit,
            SETTINGS,
            observable_interpretations=(OBSERVABLE_MEANING,),
            observable_polarities=(1,),
        )
        dem = artifact.dem
        if dem.num_detectors != 40 or dem.num_observables != 1:
            raise RuntimeError(f"{condition_id}: DEM dimensions differ from required circuit dimensions.")
        circuit_identity = CircuitIdentity.from_stim(
            circuit,
            dem,
            code_family="stim:surface_code:rotated_memory_z",
            distance=3,
            rounds=5,
            memory_basis="z",
            observable_interpretations=(OBSERVABLE_MEANING,),
            noise_model_id=f"ns4a-v2-generating:{condition_id}",
            noise_model_record=provenance,
            dem_settings=DEMConstructionSettings(
                decompose_errors=True,
                approximate_disjoint_errors=True,
                construction_note="NS-4A V2 requested preflight",
            ),
        )
        guard_status = "PASS"
        guard_error = None
        try:
            validate_upstream_signature_semantics(dem)
        except Exception as exc:
            guard_status = "FAIL"
            guard_error = f"{type(exc).__name__}: {exc}"

        dem_text = str(dem)
        dem_bytes_sha = sha256(dem_text.encode("utf-8"))
        if dem_bytes_sha != artifact.record.dem_sha256:
            raise RuntimeError(f"{condition_id}: canonical DEM byte digest differs from record.")
        model_identity = make_model_identity(
            sampling_circuit=circuit,
            generating_noise_identity=sampling.generating_noise_model_id,
            decoder_dem=dem,
            assumed_noise_provenance=provenance_json,
        )
        provenance_parity = (
            model_identity.decoder_dem_sha256 == artifact.record.dem_sha256
            and model_identity.assumed_noise_provenance == provenance_json
            and artifact.record.detector_order_sha256 == sampling.detector_order_sha256
            and artifact.record.observable_semantics_sha256 == sampling.observable_semantics_sha256
        )

        circuits.append(circuit)
        sampling_ids.append(sampling)
        artifacts.append(artifact)
        structure_hashes.append(structure_hash)
        detector_order_hashes.append(sampling.detector_order_sha256)
        dem_order_hashes.append(artifact.record.detector_order_sha256)
        observable_hashes.append(sampling.observable_semantics_sha256)

        for correlation_mode in (False, True):
            candidate_id = f"{condition_id}::correlations_{str(correlation_mode).lower()}"
            pm_status = "PASS"
            pm_error = None
            pm_metadata: dict = {}
            graph: dict = {}
            pm_decoder = None
            try:
                pm_decoder = PyMatchingDecoder.from_detector_error_model(
                    dem,
                    correlation_mode=correlation_mode,
                    name=f"pm_{condition_id}_{'corr' if correlation_mode else 'ordinary'}",
                    noise_model_id=model_id,
                )
                if pm_decoder.metadata.correlation_mode is not correlation_mode:
                    raise RuntimeError("PyMatching metadata does not preserve the constructor mode.")
                prediction = pm_decoder.decode(SYNTHETIC)
                if prediction.bits.shape != (SYNTHETIC.shape[0], 1):
                    raise RuntimeError(f"unexpected fixture prediction shape: {prediction.bits.shape}")
                if np.any((prediction.bits != 0) & (prediction.bits != 1)):
                    raise RuntimeError("fixture prediction contains nonbinary values.")
                pm_metadata = {
                    "name": pm_decoder.metadata.name,
                    "version": pm_decoder.metadata.version,
                    "detector_count": pm_decoder.metadata.detector_count,
                    "observable_count": pm_decoder.metadata.observable_count,
                    "correlation_mode": pm_decoder.metadata.correlation_mode,
                }
                match_obj = pm_decoder._matching
                graph = {
                    "nodes": getattr(match_obj, "num_nodes", None),
                    "edges": getattr(match_obj, "num_edges", None),
                    "detectors": getattr(match_obj, "num_detectors", None),
                    "fault_ids": getattr(match_obj, "num_fault_ids", None),
                }
            except Exception as exc:
                pm_status = "FAIL"
                pm_error = f"{type(exc).__name__}: {exc}"

            # Build the actual NS-2D model identity and bank reference, then
            # exercise the unchanged opt-in and information-parity gates.
            registration_status = "BLOCKED_NOT_ATTEMPTED"
            registration_error = None
            registration_no_partial = None
            if pm_status == "PASS":
                try:
                    pm_identity = DecoderModelIdentity.create(
                        sampling,
                        pm_decoder.metadata,
                        dem_record=artifact.record,
                        decoder_assumed_noise_model_id=model_id,
                        decoder_assumed_noise_provenance=provenance,
                        correlation_semantics=(
                            "PyMatching enable_correlations=True at construction and decode"
                            if correlation_mode
                            else "PyMatching enable_correlations=False at construction and decode"
                        ),
                    )
                    assert_model_compatible(pm_identity, sampling)
                    checked_pm = CheckedDecoderAdapter(
                        pm_decoder,
                        model_identity=pm_identity,
                        sampling_identity=sampling,
                    )
                    bank = CompatibilityAwareDecoderBank(sampling)
                    bank.register(checked_pm)
                    reference_names = list(bank.names())

                    # Negative opt-in check once per matrix row; no BM construction should occur.
                    try:
                        register_beliefmatching(
                            bank,
                            sampling_circuit=circuit,
                            sampling_identity=sampling,
                            dem_artifact=artifact,
                            assumed_noise_model_id=model_id,
                            assumed_noise_provenance=provenance,
                            information_reference_decoder=pm_decoder.metadata.name,
                            experimental_opt_in=False,
                        )
                    except PermissionError:
                        if list(bank.names()) == reference_names:
                            failure_tests["experimental_opt_in_false_rejected_without_registration"] = True
                    except Exception:
                        pass

                    try:
                        registration = register_beliefmatching(
                            bank,
                            sampling_circuit=circuit,
                            sampling_identity=sampling,
                            dem_artifact=artifact,
                            assumed_noise_model_id=model_id,
                            assumed_noise_provenance=provenance,
                            information_reference_decoder=pm_decoder.metadata.name,
                            experimental_opt_in=True,
                        )
                        # If the pinned dependency is available, only deterministic
                        # detector fixtures are passed; no labels or sampled data.
                        bm_prediction = registration.adapter.decode_batch(
                            SYNTHETIC,
                            detector_ids=tuple(range(40)),
                            observable_ids=(0,),
                        )
                        if bm_prediction.shape != (SYNTHETIC.shape[0], 1):
                            raise RuntimeError(f"unexpected BM fixture shape: {bm_prediction.shape}")
                        registration_status = "PASS"
                        registration_no_partial = "registered_after_success"
                    except Exception as exc:
                        registration_error = f"{type(exc).__name__}: {exc}"
                        registration_no_partial = (
                            "PASS" if list(bank.names()) == reference_names else "FAIL"
                        )
                        if registration_no_partial != "PASS":
                            raise RuntimeError(
                                f"{candidate_id}: registration failure left a partial bank state: {bank.names()}"
                            )
                        failure_tests["missing_dependency_failure_leaves_bank_unchanged"] = (
                            failure_tests["missing_dependency_failure_leaves_bank_unchanged"]
                            or registration_no_partial == "PASS"
                        )
                        if "No module named 'beliefmatching'" in registration_error:
                            registration_status = "BLOCKED_MISSING_DEPENDENCY"
                        else:
                            registration_status = "FAIL"
                except Exception as exc:
                    registration_status = "FAIL_PRECHECK"
                    registration_error = f"{type(exc).__name__}: {exc}"

            # Exercise the adapter's detector-ID and shape contract using a
            # deterministic fake upstream implementation, never real samples.
            fake_adapter = BeliefMatchingAdapter(
                FakeUpstreamDecoder(), model_identity, enabled=True
            )
            fake_shape = fake_adapter.decode_batch(
                SYNTHETIC,
                detector_ids=tuple(range(40)),
                observable_ids=(0,),
            ).shape
            if fake_shape != (SYNTHETIC.shape[0], 1):
                raise RuntimeError(f"{candidate_id}: fake adapter shape contract failed.")
            try:
                fake_adapter.decode_batch(
                    SYNTHETIC,
                    detector_ids=tuple(reversed(range(40))),
                    observable_ids=(0,),
                )
            except BeliefMatchingContractError:
                failure_tests["wrong_detector_order_rejected"] = True
            else:
                raise RuntimeError(f"{candidate_id}: detector-order mismatch was not rejected.")
            try:
                fake_adapter.decode_batch(
                    np.zeros((3, 39), dtype=np.uint8),
                    detector_ids=tuple(range(40)),
                    observable_ids=(0,),
                )
            except BeliefMatchingContractError:
                failure_tests["wrong_detector_shape_rejected"] = True
            else:
                raise RuntimeError(f"{candidate_id}: wrong detector shape was not rejected.")

            # A synthetic identity-bound detector batch verifies that NS-2C
            # receives only detector bytes. No observable labels are supplied.
            if condition_id == EXP["evaluation_conditions"][0]["id"] and correlation_mode is False:
                batch = TrustedDetectorBatchAdapter(sampling).from_stim_detector_samples(
                    circuit,
                    SYNTHETIC,
                    column_detector_ids=tuple(range(40)),
                )
                try:
                    TrustedDetectorBatchAdapter(sampling).from_stim_detector_samples(
                        circuit,
                        SYNTHETIC,
                        column_detector_ids=tuple(reversed(range(40))),
                    )
                except ValueError:
                    failure_tests["wrong_detector_order_rejected"] = True
                else:
                    raise RuntimeError("Trusted detector batch adapter accepted a reversed order.")
                spy_md = DecoderMetadata(
                    name="preflight_input_spy",
                    implementation="deterministic NS-2C fixture",
                    version="1",
                    detector_count=40,
                    observable_count=1,
                    noise_model_id=model_id,
                    correlation_mode=None,
                    experimental=True,
                    construction_provenance="synthetic detector-only information-isolation fixture",
                )
                spy = InputSpy(spy_md)
                spy_identity = DecoderModelIdentity.create(
                    sampling,
                    spy_md,
                    dem_record=artifact.record,
                    decoder_assumed_noise_model_id=model_id,
                    decoder_assumed_noise_provenance=provenance,
                    correlation_semantics=None,
                )
                spy_checked = CheckedDecoderAdapter(
                    spy, model_identity=spy_identity, sampling_identity=sampling
                )
                fixture_bank = CompatibilityAwareDecoderBank(sampling)
                fixture_bank.register(checked_pm)
                fixture_bank.register(spy_checked, experimental_opt_in=True)
                evaluate_paired_batch(
                    fixture_bank,
                    batch,
                    decoder_names=(pm_decoder.metadata.name, "preflight_input_spy"),
                    baseline_name=pm_decoder.metadata.name,
                    scope="development",
                    sample_id="deterministic-synthetic-fixture",
                    observables=None,
                )
                failure_tests["input_spy_receives_detector_only"] = (
                    spy.seen == [SYNTHETIC.tobytes(order="C")]
                    and spy.seen_shapes == [tuple(SYNTHETIC.shape)]
                )

            rows.append({
                "candidate_id": candidate_id,
                "condition_id": condition_id,
                "assumed_model_family": condition_id,
                "pymatching_correlation_mode": correlation_mode,
                "circuit_construction": "PASS",
                "circuit_sha256": sampling.circuit_sha256,
                "circuit_structure_sha256_excluding_burst_and_probability_values": structure_hash,
                "circuit_dimensions": {
                    "qubits": int(circuit.num_qubits),
                    "detectors": int(circuit.num_detectors),
                    "observables": int(circuit.num_observables),
                    "mr_boundaries": mr_count,
                    "spatial_burst_instructions": burst_count,
                },
                "sampling_detector_order_sha256": sampling.detector_order_sha256,
                "observable_semantics_sha256": sampling.observable_semantics_sha256,
                "dem_construction": "PASS",
                "dem_sha256": artifact.record.dem_sha256,
                "dem_bytes_sha256": dem_bytes_sha,
                "dem_settings": SETTINGS.stim_kwargs(),
                "dem_dimensions": {
                    "detectors": artifact.record.detector_count,
                    "observables": artifact.record.observable_count,
                },
                "dem_detector_order_sha256": artifact.record.detector_order_sha256,
                "alias_guard": guard_status,
                "alias_guard_error": guard_error,
                "pymatching_construction_and_fixture_decode": pm_status,
                "pymatching_error": pm_error,
                "pymatching_metadata": pm_metadata,
                "pymatching_graph": graph,
                "correlation_mode_consistent_at_constructor_and_decode": (
                    pm_status == "PASS" and pm_metadata.get("correlation_mode") is correlation_mode
                ),
                "bm_registration_and_construction": registration_status,
                "bm_error": registration_error,
                "bm_failure_no_partial_registration": registration_no_partial,
                "dem_and_assumed_noise_provenance_parity": (
                    "PASS_CONTRACT_CHECKS; BM runtime blocked"
                    if provenance_parity
                    else "FAIL"
                ),
                "same_concrete_dem_digest_for_pm_and_bm_identity": (
                    pm_status == "PASS"
                    and pm_identity.dem_record.dem_sha256 == model_identity.decoder_dem_sha256
                ) if pm_status == "PASS" else False,
                "labels_supplied": False,
                "sampled_detector_events": False,
            })

    common_detector_order = len(set(detector_order_hashes)) == 1
    common_dem_order = len(set(dem_order_hashes)) == 1
    common_observable_semantics = len(set(observable_hashes)) == 1
    common_topology = len(set(structure_hashes)) == 1
    expected_count = len(EXP["evaluation_conditions"]) * len(EXP["decoder_models"]["selection_modes"])
    if len(rows) != expected_count or expected_count != 12:
        raise RuntimeError(f"Expected a complete 12-candidate matrix, got {len(rows)}.")
    failure_tests["experimental_opt_in_false_rejected_without_registration"] = (
        failure_tests["experimental_opt_in_false_rejected_without_registration"]
        and len(rows) == 12
    )

    summary = {
        "schema": "qshift-ns4a-v2-deterministic-preflight-summary-v1",
        "base_commit": "612c5e1381d75ca069bc6952d057c798ab10e9ab",
        "branch": "codex/ns4a-v2-deterministic-preflight",
        "environment": env,
        "counts": {
            "circuits_constructed": len(circuits),
            "dems_constructed": len(artifacts),
            "candidate_matrix_rows": len(rows),
            "sampler_calls": 0,
            "sampled_shots": 0,
            "labels_read": 0,
            "model_selections": 0,
        },
        "common_identity_checks": {
            "all_detector_order_fingerprints_equal": common_detector_order,
            "all_dem_order_fingerprints_equal": common_dem_order,
            "all_observable_semantics_equal": common_observable_semantics,
            "all_normalized_circuit_topology_signatures_equal": common_topology,
        },
        "deterministic_fixture_checks": failure_tests,
        "bm_runtime_dependency_status": (
            "MISSING" if env["beliefmatching_distribution"] is None else "PRESENT"
        ),
        "overall_preflight": (
            "BLOCKED_BELIEFMATCHING_DEPENDENCY"
            if env["beliefmatching_distribution"] is None
            else "REVIEW_MATRIX_FOR_OTHER_BLOCKERS"
        ),
        "no_sampling_assertion": True,
    }
    (OUT / "COMPATIBILITY_MATRIX.json").write_text(
        json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (OUT / "VALIDATION_SUMMARY.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if all(failure_tests.values()) and len(rows) == 12 else 2


if __name__ == "__main__":
    raise SystemExit(main())
