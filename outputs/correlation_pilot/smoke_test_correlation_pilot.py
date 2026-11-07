"""Small deterministic smoke test of the actual pilot decoder-call pattern."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("qshift_pilot_runner", HERE / "run_correlation_pilot.py")
runner = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runner
spec.loader.exec_module(runner)


def main() -> dict:
    cfg = runner.CFG
    models, build_seconds = runner.make_models()
    records = []
    for si, label in enumerate(cfg["stratum_order"]):
        basis, regime = label.split("_", 1)
        circuit = runner.noise_model.build_circuit(
            basis, regime, distance=3, rounds=5, gate_p=0.003,
            measurement_p=0.003, bias_ratio=10.0)
        d1, y1 = circuit.compile_detector_sampler(seed=cfg["seed_allocation"]["diagnostic"]).sample(
            256, separate_observables=True)
        d2, y2 = circuit.compile_detector_sampler(seed=cfg["seed_allocation"]["diagnostic"]).sample(
            256, separate_observables=True)
        if not np.array_equal(d1, d2) or not np.array_equal(y1, y2):
            raise AssertionError(f"Diagnostic seed is not reproducible for {label}")
        fixed_index = cfg["pooled_fixed_model_index_by_basis"][basis]
        regime_index = cfg["regimes"].index(regime)
        fixed, specialized = models[(basis, fixed_index)], models[(basis, regime_index)]
        arms = [
            np.asarray(fixed["correlation_off"].decode_batch(d1, enable_correlations=False)).reshape(-1),
            np.asarray(fixed["correlation_on"].decode_batch(d1, enable_correlations=True)).reshape(-1),
            np.asarray(specialized["correlation_off"].decode_batch(d1, enable_correlations=False)).reshape(-1),
            np.asarray(specialized["correlation_on"].decode_batch(d1, enable_correlations=True)).reshape(-1),
        ]
        pred = np.stack(arms).astype(np.uint8)
        obs = np.asarray(y1, dtype=np.uint8).reshape(-1)
        if d1.shape != (256, 40) or obs.shape != (256,) or pred.shape != (4, 256):
            raise AssertionError(f"Smoke output shape mismatch for {label}")
        if not np.isin(pred, [0, 1]).all() or not np.isin(obs, [0, 1]).all():
            raise AssertionError(f"Smoke outputs are not binary for {label}")
        packed = np.packbits(d1, axis=1, bitorder="little")
        unpacked = np.unpackbits(packed, axis=1, bitorder="little")[:, :40]
        if packed.shape != (256, 5) or not np.array_equal(unpacked, d1):
            raise AssertionError(f"Packed detector round-trip failed for {label}")
        records.append({"stratum": label, "shots": 256,
                        "detectors_shape": list(d1.shape), "packed_shape": list(packed.shape),
                        "observable_shape": list(obs.shape), "predictions_shape": list(pred.shape),
                        "binary": True,
                        "pooled_prediction_disagreements_on_off": int(np.count_nonzero(pred[0] != pred[1])),
                        "pooled_standard_only": int(np.count_nonzero((obs ^ pred[0]) & (1 - (obs ^ pred[1])))),
                        "pooled_correlation_only": int(np.count_nonzero((obs ^ pred[1]) & (1 - (obs ^ pred[0]))))})
    result = {"status": "PASS", "deterministic_test_shots": 6 * 256,
              "no_full_pilot_shots_generated": True,
              "matcher_construction_seconds": build_seconds,
              "records": records}
    (HERE / "SMOKE_TEST.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "smoke_shots": result["deterministic_test_shots"],
                      "all_six_strata": len(records) == 6,
                      "pooled_disagreements": [r["pooled_prediction_disagreements_on_off"] for r in records]}, indent=2))
    return result


if __name__ == "__main__":
    main()
