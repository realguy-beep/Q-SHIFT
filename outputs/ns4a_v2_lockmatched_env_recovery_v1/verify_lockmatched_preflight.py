from __future__ import annotations

import hashlib
import ast
import json
import math
import sys
from unittest.mock import patch
from pathlib import Path

import numpy as np
import pymatching
import stim

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
for p in (ROOT / "outputs/phase2b_pauli_bias", ROOT / "outputs/phase3a_correlated_noise_preflight"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from simulator import build_spatial_burst_circuit
from qshift_core_v1.pymatching_adapter import PyMatchingDecoder
from qshift_core_v1.research_adapters.beliefmatching_adapter_ns3b import (
    BeliefMatchingContractError,
    validate_upstream_signature_semantics,
)
from qshift_core_v1.research_adapters.beliefmatching_integration_ns2d import register_beliefmatching
import qshift_core_v1.research_adapters.beliefmatching_integration_ns2d as bm_integration
from qshift_core_v1.sampling_model_identity import (
    DEMConstructionSettingsV2,
    DecoderModelIdentity,
    SamplingIdentity,
    StimDEMArtifact,
)

CONFIG = json.loads((OUT.parent / "qshift_ns4a_pilot_protocol_v2/proposed_config_v2.json").read_text(encoding="utf-8"))
EXP = CONFIG["experiment"]
GEN = EXP["generator"]
SETTINGS = DEMConstructionSettingsV2(
    decompose_errors=True,
    approximate_disjoint_errors=True,
    construction_note="NS-4A V2 requested preflight: Stim detector_error_model",
)
OBSERVABLE_MEANING = "Stim OBSERVABLE_INCLUDE parity; bit 1 denotes predicted logical-observable flip"
FIXTURE = np.zeros((3, 40), dtype=np.uint8)
FIXTURE[1, [0, 3, 7]] = 1
FIXTURE[2, [12, 19, 34]] = 1


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def provenance_for(condition: dict) -> tuple[str, dict]:
    model_id = f"ns4a-v2-assumed:{condition['id']}"
    return model_id, {
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
        "dem_settings": {"decompose_errors": True, "approximate_disjoint_errors": True},
    }


def independently_check_registration_failures(*, bank, circuit, sampling, artifact, model_id, provenance, reference_name, target_identity, target_metadata) -> dict[str, bool]:
    before = list(bank.names())
    args = {
        "bank": bank,
        "sampling_circuit": circuit,
        "sampling_identity": sampling,
        "dem_artifact": artifact,
        "assumed_noise_model_id": model_id,
        "assumed_noise_provenance": provenance,
        "information_reference_decoder": reference_name,
        "experimental_opt_in": True,
    }
    result = {
        "construction_failure_leaves_bank_unchanged": False,
        "binding_failure_closes_adapter_and_leaves_bank_unchanged": False,
        "registration_failure_closes_adapter_and_leaves_bank_unchanged": False,
    }

    class ConstructionFailure:
        @classmethod
        def from_dem(cls, **kwargs):
            raise RuntimeError("independent injected construction failure")

    with patch.object(bm_integration, "BeliefMatchingAdapter", ConstructionFailure):
        try:
            register_beliefmatching(**args)
        except RuntimeError as exc:
            result["construction_failure_leaves_bank_unchanged"] = (
                "independent injected construction failure" in str(exc) and list(bank.names()) == before
            )

    bound = []

    class BindingFailure:
        def __init__(self):
            self.closed = False

        @classmethod
        def from_dem(cls, **kwargs):
            item = cls()
            bound.append(item)
            return item

        def bind_ns2c(self, **kwargs):
            raise RuntimeError("independent injected binding failure")

        def close(self):
            self.closed = True

    with patch.object(bm_integration, "BeliefMatchingAdapter", BindingFailure):
        try:
            register_beliefmatching(**args)
        except RuntimeError as exc:
            result["binding_failure_closes_adapter_and_leaves_bank_unchanged"] = (
                "independent injected binding failure" in str(exc)
                and len(bound) == 1 and bound[0].closed and list(bank.names()) == before
            )

    registered = []

    class RegistrationFailure:
        def __init__(self):
            self.closed = False
            self.metadata = target_metadata

        @classmethod
        def from_dem(cls, **kwargs):
            item = cls()
            registered.append(item)
            return item

        def bind_ns2c(self, **kwargs):
            return target_identity

        def decode(self, detectors):
            return None

        def close(self):
            self.closed = True

    with patch.object(bm_integration, "BeliefMatchingAdapter", RegistrationFailure):
        with patch.object(bank, "register", side_effect=RuntimeError("independent injected registration failure")):
            try:
                register_beliefmatching(**args)
            except RuntimeError as exc:
                result["registration_failure_closes_adapter_and_leaves_bank_unchanged"] = (
                    "independent injected registration failure" in str(exc)
                    and len(registered) == 1 and registered[0].closed and list(bank.names()) == before
                )
    return result


def main() -> int:
    matrix_path = OUT / "BELIEFMATCHING_COMPATIBILITY_MATRIX.json"
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    dependency = json.loads((OUT / "DEPENDENCY_VERIFICATION.json").read_text(encoding="utf-8"))
    summary = json.loads((OUT / "LOCKMATCHED_PREFLIGHT_SUMMARY.json").read_text(encoding="utf-8"))
    source_inventory = json.loads((OUT / "SOURCE_INPUT_INVENTORY.json").read_text(encoding="utf-8"))
    failures: list[dict] = []
    checked: list[dict] = []
    independently_injected: list[dict] = []

    if dependency.get("overall") != "PASS":
        failures.append({"check": "dependency_verification", "detail": dependency.get("overall")})
    if (
        source_inventory.get("base_commit") != "2ba57e83e262ca32afe4cb58063d2e3e63605e3b"
        or source_inventory.get("branch") != "codex/ns4a-v2-lockmatched-env"
        or len(source_inventory.get("local_allowlisted_inputs", [])) != 20
        or len(source_inventory.get("upstream_inputs_read_by_exact_git_object", [])) != 2
        or source_inventory.get("all_local_sources_match_base_commit") is not True
        or source_inventory.get("adapter_copy_matches_upstream_blob") is not True
        or source_inventory.get("locked_dependency_sha256") != dependency.get("lock", {}).get("sha256")
    ):
        failures.append({"check": "source_input_inventory", "detail": "source inventory mismatch or incomplete"})
    if CONFIG.get("sampling_authorized") is not False or CONFIG.get("sampling_performed") is not False:
        failures.append({"check": "sampling_boundary", "detail": "V2 config not closed"})
    for script_name in ("run_lockmatched_preflight.py", "verify_lockmatched_preflight.py"):
        tree = ast.parse((OUT / script_name).read_text(encoding="utf-8"), filename=script_name)
        forbidden_sampling_calls = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"compile_detector_sampler", "compile_sampler", "sample", "sample_batch"}
        }
        if forbidden_sampling_calls:
            failures.append({"check": f"{script_name}:no_sampling_api_calls", "detail": sorted(forbidden_sampling_calls)})
    if summary.get("counts") != {
        "circuits_constructed": 6,
        "dems_constructed": 6,
        "candidate_matrix_rows": 12,
        "sampler_calls": 0,
        "sampled_shots": 0,
        "labels_read": 0,
        "model_selections": 0,
        "failure_injection_candidate_rows": 12,
    }:
        failures.append({"check": "summary_zero_counts", "detail": summary.get("counts")})

    expected_modes = (False, True)
    expected_ids = {
        f"{condition['id']}::correlations_{str(mode).lower()}"
        for condition in EXP["evaluation_conditions"]
        for mode in expected_modes
    }
    if len(matrix) != 12 or {row.get("candidate_id") for row in matrix} != expected_ids:
        failures.append({"check": "matrix_completeness", "detail": f"rows={len(matrix)}"})

    row_by_id = {row.get("candidate_id"): row for row in matrix}
    for condition in EXP["evaluation_conditions"]:
        cid = condition["id"]
        model_id, provenance = provenance_for(condition)
        try:
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
            sampling = SamplingIdentity.from_stim(
                circuit,
                generating_noise_model_id=f"ns4a-v2-generating:{cid}",
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
            try:
                validate_upstream_signature_semantics(dem)
                alias_result = "PASS"
            except Exception as exc:
                alias_result = "FAIL"
                failures.append({"check": f"{cid}:alias_guard", "detail": f"{type(exc).__name__}: {exc}"})
            if circuit.num_detectors != 40 or circuit.num_observables != 1 or dem.num_detectors != 40 or dem.num_observables != 1:
                failures.append({"check": f"{cid}:dimensions", "detail": "expected circuit and DEM 40 detectors/1 observable"})

            for mode in expected_modes:
                candidate_id = f"{cid}::correlations_{str(mode).lower()}"
                row = row_by_id.get(candidate_id)
                row_failures: list[str] = []
                if row is None:
                    failures.append({"check": candidate_id, "detail": "missing row"})
                    continue
                expected_dem_sha = artifact.record.dem_sha256
                if row.get("circuit_sha256") != sampling.circuit_sha256:
                    row_failures.append("circuit digest mismatch")
                if row.get("dem_sha256") != expected_dem_sha or row.get("dem_bytes_sha256") != sha(str(dem).encode("utf-8")):
                    row_failures.append("DEM digest mismatch")
                if row.get("alias_guard") != alias_result or alias_result != "PASS":
                    row_failures.append("alias guard failed or disagrees")
                if row.get("labels_supplied") is not False or row.get("sampled_detector_events") is not False:
                    row_failures.append("nonzero information-boundary flag")
                for timing_key in (
                    "pymatching_construction_seconds_diagnostic_only",
                    "pymatching_inference_seconds_diagnostic_only",
                    "bm_construction_seconds_diagnostic_only",
                    "bm_inference_seconds_diagnostic_only",
                ):
                    timing_value = row.get(timing_key)
                    if not isinstance(timing_value, (int, float)) or not math.isfinite(timing_value) or timing_value < 0:
                        row_failures.append(f"missing/invalid nonnegative timing field: {timing_key}")

                pm = None
                registration = None
                injected = None
                try:
                    pm = PyMatchingDecoder.from_detector_error_model(
                        dem,
                        correlation_mode=mode,
                        name=f"verify_pm_{cid}_{'corr' if mode else 'ordinary'}",
                        noise_model_id=model_id,
                    )
                    pm_pred = pm.decode(FIXTURE)
                    if pm.metadata.correlation_mode is not mode:
                        row_failures.append("PyMatching correlation mode metadata mismatch")
                    if pm_pred.bits.shape != (3, 1) or pm_pred.bits.dtype != np.dtype(np.uint8) or np.any((pm_pred.bits != 0) & (pm_pred.bits != 1)):
                        row_failures.append("PyMatching fixture prediction contract failure")

                    pm_identity = DecoderModelIdentity.create(
                        sampling,
                        pm.metadata,
                        dem_record=artifact.record,
                        decoder_assumed_noise_model_id=model_id,
                        decoder_assumed_noise_provenance=provenance,
                        correlation_semantics=(
                            "PyMatching enable_correlations=True at construction and decode" if mode
                            else "PyMatching enable_correlations=False at construction and decode"
                        ),
                    )
                    from qshift_core_v1.decoder_runtime_v2 import CheckedDecoderAdapter, CompatibilityAwareDecoderBank
                    bank = CompatibilityAwareDecoderBank(sampling)
                    bank.register(CheckedDecoderAdapter(pm, model_identity=pm_identity, sampling_identity=sampling))
                    registration = register_beliefmatching(
                        bank,
                        sampling_circuit=circuit,
                        sampling_identity=sampling,
                        dem_artifact=artifact,
                        assumed_noise_model_id=model_id,
                        assumed_noise_provenance=provenance,
                        information_reference_decoder=pm.metadata.name,
                        experimental_opt_in=True,
                    )
                    bm_result = registration.adapter.decode(FIXTURE.copy())
                    bm_bits = np.asarray(bm_result.bits)
                    if (
                        bm_bits.shape != (3, 1)
                        or bm_bits.dtype != np.dtype(np.uint8)
                        or not np.isfinite(bm_bits).all()
                        or np.any((bm_bits != 0) & (bm_bits != 1))
                        or row.get("bm_prediction", {}).get("prediction_bits") != bm_bits.tolist()
                    ):
                        row_failures.append("BeliefMatching fixture prediction contract/value mismatch")
                    bm_identity = registration.model_identity
                    if (
                        bm_identity.dem_record.dem_sha256 != expected_dem_sha
                        or bm_identity.decoder_assumed_noise_model_id != pm_identity.decoder_assumed_noise_model_id
                        or bm_identity.decoder_assumed_noise_provenance_json != pm_identity.decoder_assumed_noise_provenance_json
                        or registration.adapter.identity.decoder_dem_sha256 != expected_dem_sha
                    ):
                        row_failures.append("BM/PM concrete DEM or assumed-noise provenance parity mismatch")
                    try:
                        registration.adapter.decode_batch(FIXTURE, detector_ids=tuple(reversed(range(40))), observable_ids=(0,))
                        row_failures.append("reversed detector order accepted")
                    except BeliefMatchingContractError:
                        pass
                    try:
                        registration.adapter.decode_batch(FIXTURE, detector_ids=tuple(range(40)), observable_ids=(1,))
                        row_failures.append("wrong observable id accepted")
                    except BeliefMatchingContractError:
                        pass
                    try:
                        registration.adapter.decode_batch(np.zeros((3, 39), dtype=np.uint8), detector_ids=tuple(range(40)), observable_ids=(0,))
                        row_failures.append("wrong detector shape accepted")
                    except BeliefMatchingContractError:
                        pass
                    failure_bank = CompatibilityAwareDecoderBank(sampling)
                    failure_bank.register(CheckedDecoderAdapter(pm, model_identity=pm_identity, sampling_identity=sampling))
                    injected = independently_check_registration_failures(
                        bank=failure_bank,
                        circuit=circuit,
                        sampling=sampling,
                        artifact=artifact,
                        model_id=model_id,
                        provenance=provenance,
                        reference_name=pm.metadata.name,
                        target_identity=registration.model_identity,
                        target_metadata=registration.adapter.metadata,
                    )
                    independently_injected.append({"candidate_id": candidate_id, **injected})
                    if not all(injected.values()):
                        row_failures.append(f"independent failure injection failed: {injected}")
                except Exception as exc:
                    row_failures.append(f"independent reconstruction exception: {type(exc).__name__}: {exc}")
                finally:
                    if registration is not None:
                        registration.adapter.close()
                        if registration.adapter._decoder is not None or registration.adapter.enabled:
                            row_failures.append("BM adapter did not close")

                if row.get("pymatching_construction_and_fixture_decode") != "PASS":
                    row_failures.append("saved PyMatching candidate did not PASS")
                if not str(row.get("pymatching_cleanup", "")).startswith("PASS_"):
                    row_failures.append("saved PyMatching cleanup did not PASS")
                if row.get("pymatching_correlation_mode") is not mode or row.get("correlation_mode_consistent_at_constructor_and_decode") is not True:
                    row_failures.append("saved PyMatching correlation-mode selection/consistency mismatch")
                if row.get("bm_registration_and_construction") != "PASS":
                    row_failures.append("saved BeliefMatching candidate did not PASS")
                if row.get("bm_cleanup") != "PASS":
                    row_failures.append("saved BeliefMatching cleanup did not PASS")
                if row.get("pymatching_error") is not None or row.get("bm_error") is not None:
                    row_failures.append("candidate contains a recorded decoder exception")
                if row.get("dem_and_assumed_noise_provenance_parity") != "PASS" or row.get("bm_runtime_provenance_parity") is not True:
                    row_failures.append("saved model/provenance parity did not PASS")
                if row_failures:
                    failures.append({"check": candidate_id, "detail": row_failures})
                checked.append({
                    "candidate_id": candidate_id,
                    "independent_reconstruction": "PASS" if not row_failures else "FAIL",
                    "failure_injection_checks": injected if registration is not None else None,
                })

        except Exception as exc:
            failures.append({"check": f"{cid}:construction", "detail": f"{type(exc).__name__}: {exc}"})
            for mode in expected_modes:
                candidate_id = f"{cid}::correlations_{str(mode).lower()}"
                checked.append({"candidate_id": candidate_id, "independent_reconstruction": "FAIL"})

    result = {
        "schema": "qshift-ns4a-v2-lockmatched-independent-verification-v1",
        "reconstructed_candidate_count": len(checked),
        "expected_candidate_count": 12,
        "all_candidates_reconstructed": len(checked) == 12 and all(c["independent_reconstruction"] == "PASS" for c in checked),
        "checks": checked,
        "independently_repeated_failure_injection_rows": len(independently_injected),
        "all_failure_injections_passed": len(independently_injected) == 12 and all(
            all(value for key, value in item.items() if key != "candidate_id")
            for item in independently_injected
        ),
        "independently_repeated_failure_injection": independently_injected,
        "failures": failures,
        "sampler_calls": 0,
        "sampled_shots": 0,
        "labels_read": 0,
        "overall": "PASS" if len(checked) == 12 and len(independently_injected) == 12 and not failures else "FAIL",
    }
    (OUT / "INDEPENDENT_PREFLIGHT_VERIFICATION.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"overall": result["overall"], "candidate_count": len(checked), "failures": failures}, indent=2))
    return 0 if result["overall"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
