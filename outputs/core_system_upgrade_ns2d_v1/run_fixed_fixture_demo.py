"""Run the deterministic NS-2D integration demo; no sampler is called."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import platform
from pathlib import Path
import sys
import time

import numpy as np
import pymatching
import stim

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
_SIMULATOR_PATH = ROOT / "outputs" / "phase3a_correlated_noise_preflight" / "simulator.py"
_SIMULATOR_SPEC = importlib.util.spec_from_file_location(
    "qshift_ns2d_correlated_simulator_fixture", _SIMULATOR_PATH,
)
if _SIMULATOR_SPEC is None or _SIMULATOR_SPEC.loader is None:
    raise RuntimeError(f"Cannot load deterministic circuit builder at {_SIMULATOR_PATH}")
simulator = importlib.util.module_from_spec(_SIMULATOR_SPEC)
_SIMULATOR_SPEC.loader.exec_module(simulator)

from qshift_core_v1.contracts import DecoderMetadata  # noqa: E402
from qshift_core_v1.decoder_runtime_v2 import (  # noqa: E402
    CheckedDecoderAdapter,
    CompatibilityAwareDecoderBank,
    evaluate_paired_batch,
)
from qshift_core_v1.pymatching_adapter import PyMatchingDecoder  # noqa: E402
from qshift_core_v1.research_adapters.beliefmatching_integration_ns2d import (  # noqa: E402
    register_beliefmatching,
)
from qshift_core_v1.sampling_model_identity import (  # noqa: E402
    DEMConstructionSettingsV2,
    DecoderModelIdentity,
    SamplingIdentity,
    StimDEMArtifact,
    TrustedDetectorBatchAdapter,
)


def main() -> int:
    generator = {
        "memory_basis": "z", "regime": "balanced", "distance": 3, "rounds": 5,
        "gate_p": 0.003, "measurement_p": 0.003, "bias_ratio": 10.0,
        "burst_probability": 0.01, "burst_pair": [8, 10],
    }
    noise_model_id = "shared-qshift-decomposed-dem-static-model-v1"
    observable_meaning = "Stim OBSERVABLE_INCLUDE(0) parity; 1 predicts logical observable flip"
    provenance = {
        "source": "shared explicit deterministic development fixture model",
        "gate_p": 0.003, "measurement_p": 0.003, "bias_ratio": 10.0,
        "burst_probability": 0.01, "burst_pair": [8, 10],
        "dem_decompose_errors": True, "dem_approximate_disjoint_errors": True,
    }
    circuit = simulator.build_spatial_burst_circuit(**generator)
    sampling = SamplingIdentity.from_stim(
        circuit, generating_noise_model_id="qshift-ns3b-balanced-z-d3-r5-static-burst-v1",
        generating_noise_provenance={**provenance, "role": "data-generating circuit"},
        code_family="rotated_surface_code", distance=3, rounds=5, memory_basis="z",
        observable_interpretations=(observable_meaning,), observable_polarities=(1,),
    )
    artifact = StimDEMArtifact.build(
        circuit,
        DEMConstructionSettingsV2(
            decompose_errors=True, approximate_disjoint_errors=True,
            construction_note="NS-3B handoff DEM conversion; deterministic integration only",
        ),
        observable_interpretations=(observable_meaning,), observable_polarities=(1,),
    )
    bank = CompatibilityAwareDecoderBank(sampling)
    construction_ms = {}
    for mode, name in ((False, "pymatching_ordinary"), (True, "pymatching_correlated")):
        started = time.perf_counter()
        decoder = PyMatchingDecoder.from_detector_error_model(
            artifact.dem, correlation_mode=mode, name=name,
            noise_model_id=noise_model_id, experimental=False,
        )
        metadata = decoder.metadata
        model = DecoderModelIdentity.create(
            sampling, metadata, dem_record=artifact.record,
            decoder_assumed_noise_model_id=noise_model_id,
            decoder_assumed_noise_provenance=provenance,
            correlation_semantics=(
                "correlation enabled at graph construction and decode"
                if mode else "correlation disabled at graph construction and decode"
            ),
        )
        bank.register(CheckedDecoderAdapter(
            decoder, model_identity=model, sampling_identity=sampling,
        ))
        construction_ms[name] = (time.perf_counter() - started) * 1000.0

    bm = register_beliefmatching(
        bank, sampling_circuit=circuit, sampling_identity=sampling,
        dem_artifact=artifact, assumed_noise_model_id=noise_model_id,
        assumed_noise_provenance=provenance,
        information_reference_decoder="pymatching_ordinary",
        experimental_opt_in=True, max_bp_iters=20,
    )
    construction_ms["beliefmatching"] = bm.construction_seconds * 1000.0

    detector_rows = np.zeros((5, len(sampling.detector_ids)), dtype=np.uint8)
    detector_rows[1, 0] = 1
    detector_rows[2, 1] = 1
    detector_rows[3, [8, 10]] = 1
    detector_rows[4, -1] = 1
    batch = TrustedDetectorBatchAdapter(sampling).from_stim_detector_samples(
        circuit, detector_rows, column_detector_ids=sampling.detector_ids,
    )
    names = ("pymatching_ordinary", "pymatching_correlated", "beliefmatching")
    paired = evaluate_paired_batch(
        bank, batch, decoder_names=names, baseline_name="pymatching_ordinary",
        scope="development", sample_id="ns2d-fixed-detector-fixture-v1", observables=None,
    )
    predictions = {}
    prediction_timings = {}
    identities = {}
    for name in names:
        execution = bank.adapter(name).predict(batch)
        if execution.status != "ok" or execution.prediction is None:
            raise RuntimeError(f"{name} failed in deterministic fixture: {execution.failure_message}")
        digest = hashlib.sha256(execution.prediction.bits.tobytes(order="C")).hexdigest()
        if digest != paired["records"][name]["prediction_sha256"]:
            raise RuntimeError(f"{name} changed predictions across deterministic repeat.")
        predictions[name] = execution.prediction.bits.tolist()
        prediction_timings[name] = {
            "wall_seconds": execution.wall_seconds,
            "decoder_reported_seconds": execution.decoder_reported_seconds,
        }
        model = bank.adapter(name).model_identity
        identities[name] = {
            "model_identity_sha256": model.identity_sha256,
            "sampling_identity_sha256": model.sampling_identity_sha256,
            "dem_sha256": model.dem_record.dem_sha256,
            "assumed_noise_model_id": model.decoder_assumed_noise_model_id,
            "assumed_noise_provenance": json.loads(model.decoder_assumed_noise_provenance_json),
            "experimental": model.metadata.experimental,
            "correlation_mode": model.metadata.correlation_mode,
            "implementation_version": model.metadata.version,
        }

    output = {
        "schema": "qshift-ns2d-fixed-fixture-demo-v1",
        "classification": "deterministic engineering fixture; not sampled data and not a performance study",
        "sampling_performed": False,
        "training_performed": False,
        "protected_outcomes_accessed": False,
        "stim_version": str(stim.__version__),
        "pymatching_version": str(pymatching.__version__),
        "python": platform.python_version(),
        "generator_configuration": generator,
        "dem": {
            "sha256": artifact.record.dem_sha256,
            "decompose_errors": artifact.record.settings.decompose_errors,
            "approximate_disjoint_errors": artifact.record.settings.approximate_disjoint_errors,
            "detectors": artifact.record.detector_count,
            "observables": artifact.record.observable_count,
        },
        "detector_fixture": detector_rows.tolist(),
        "detector_fixture_sha256": batch.content_sha256,
        "predictions": predictions,
        "model_identities": identities,
        "construction_milliseconds": construction_ms,
        "inference": {
            "paired_harness_records": paired["records"],
            "repeat_call_timings_seconds": prediction_timings,
        },
        "paired_vs_ordinary_pymatching": paired["paired_vs_baseline"],
        "logical_error_rate": None,
        "logical_error_rate_note": "No scoring labels were supplied; deterministic fixture predictions only.",
        "validation": {
            "all_prediction_shapes_valid": all(len(value) == 5 and all(len(row) == 1 for row in value)
                                                for value in predictions.values()),
            "all_arms_share_dem_sha256": len({value["dem_sha256"] for value in identities.values()}) == 1,
            "all_arms_share_noise_model_id": len({value["assumed_noise_model_id"] for value in identities.values()}) == 1,
            "candidate_is_experimental": identities["beliefmatching"]["experimental"],
        },
    }
    out = ROOT / "outputs" / "core_system_upgrade_ns2d_v1" / "FIXED_FIXTURE_COMPARISON.json"
    out.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(out)
    print(json.dumps({
        "dem_sha256": artifact.record.dem_sha256,
        "predictions": predictions,
        "construction_milliseconds": construction_ms,
        "paired_vs_ordinary": paired["paired_vs_baseline"],
        "inference_wall_seconds": {name: paired["records"][name]["wall_seconds"] for name in names},
        "ler": None,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
