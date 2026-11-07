"""Independent read-only verification and scoring of the Stage 4 saved evidence."""
from __future__ import annotations

import csv
import hashlib
import itertools
import json
import math
import os
import statistics
import time
from pathlib import Path

import numpy as np
import psutil
import stim
import pymatching

from outputs.phase3a_correlated_noise_preflight.simulator import (
    DEFAULT_BURST_PAIR, build_matching, build_spatial_burst_circuit,
)
from outputs.stage4_noise_adaptive_feasibility_v1.prototype import DetectorProfileEstimator
from outputs.stage4_noise_adaptive_development_v1.run_stage4 import (
    HERE, REPO, PROFILE_DIR, ROOT_DIR, RUN_DIR, STATUS_PATH, sha256_bytes, sha256_file,
)
from outputs.stage4_noise_adaptive_development_v1.freeze_stage4_dev_v2 import build as build_freeze

CONFIG = json.loads((HERE / "stage4_development_config.json").read_text(encoding="utf-8"))
INVENTORY = json.loads((HERE / "seed_inventory.json").read_text(encoding="utf-8"))
PROBABILITIES = (0.0, 0.004, 0.008, 0.012, 0.016)
NONZERO = PROBABILITIES[1:]
DECODERS = ("fixed_nominal", "detector_estimated", "privileged_true_probability")
OUT = HERE


def atomic_json(path: Path, obj: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def build_circuit(p: float):
    return build_spatial_burst_circuit(
        memory_basis="z", regime="balanced", distance=3, rounds=5,
        gate_p=0.003, measurement_p=0.003, bias_ratio=10.0,
        burst_probability=float(p), burst_pair=DEFAULT_BURST_PAIR,
    )


def build_auditor_matcher(p: float):
    c = build_circuit(p)
    dem = c.detector_error_model(decompose_errors=True, approximate_disjoint_errors=True)
    m = pymatching.Matching.from_detector_error_model(dem, enable_correlations=True)
    if ((c.num_detectors, c.num_observables, dem.num_detectors, dem.num_observables)
            != (40, 1, 40, 1) or (m.num_detectors, m.num_fault_ids) != (40, 1)):
        raise ValueError("independent reconstructed model has unexpected detector/observable dimensions")
    return c, dem, m


def independently_decode(matcher, detector_array: np.ndarray) -> np.ndarray:
    d = np.asarray(detector_array)
    if d.dtype != np.uint8 or d.ndim != 2 or d.shape[1] != 40 or not np.isin(d, (0, 1)).all():
        raise ValueError(f"invalid stored detector array: {d.shape} {d.dtype}")
    pred = np.asarray(matcher.decode_batch(d), dtype=np.uint8)
    if pred.shape == (len(d), 1):
        pred = pred[:, 0]
    if pred.shape != (len(d),) or not np.isin(pred, (0, 1)).all():
        raise ValueError("independent decoder returned invalid prediction shape/content")
    return pred


def cluster_boot(diffs: dict[float, np.ndarray], rng: np.random.Generator, n: int = 20000) -> np.ndarray:
    # Independently coded to audit the frozen analysis helper.
    pieces = []
    for p in NONZERO:
        v = np.asarray(diffs[p], dtype=np.float64)
        if v.shape != (7,):
            raise ValueError("expected seven independent roots in each nonzero stratum")
        idx = rng.integers(0, 7, size=(n, 7))
        pieces.append(v[idx].mean(axis=1))
    return np.mean(np.stack(pieces), axis=0)


def single_stratum_boot(values: np.ndarray, rng: np.random.Generator, n: int = 20000) -> np.ndarray:
    v = np.asarray(values, dtype=np.float64)
    if v.shape != (7,):
        raise ValueError("single-stratum root bootstrap requires seven roots")
    return v[rng.integers(0, 7, size=(n, 7))].mean(axis=1)


def root_signflip(diffs: dict[float, np.ndarray], rng: np.random.Generator,
                  assignments: int = 100000) -> tuple[float, float]:
    cells = [np.asarray(diffs[p], dtype=np.float64) for p in NONZERO]
    obs = float(np.mean([x.mean() for x in cells]))
    vals = np.concatenate(cells)
    extreme = 0
    remaining = assignments
    while remaining:
        n = min(10000, remaining)
        signs = rng.integers(0, 2, size=(n, len(vals)), dtype=np.int8) * 2 - 1
        signs = signs.astype(np.float64)
        simulated = (signs * vals).mean(axis=1)
        extreme += int(np.count_nonzero(np.abs(simulated) >= abs(obs) - 1e-15))
        remaining -= n
    return obs, (extreme + 1) / (assignments + 1)


def exact_flip(values: np.ndarray) -> float:
    v = np.asarray(values, dtype=np.float64)
    obs = abs(float(v.mean()))
    signs = np.asarray(list(itertools.product((-1.0, 1.0), repeat=7)))
    t = np.abs((signs * v[None, :]).mean(axis=1))
    return float(np.count_nonzero(t >= obs - 1e-15) / len(t))


def holm(raw: dict[str, float]) -> dict[str, float]:
    order = sorted(raw, key=raw.get)
    m = len(order)
    adjusted: dict[str, float] = {}
    last = 0.0
    for i, name in enumerate(order):
        last = max(last, min(1.0, (m - i) * raw[name]))
        adjusted[name] = last
    return adjusted


def q(values, qv):
    return float(np.quantile(np.asarray(values, dtype=np.float64), qv))


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    fields = fields or (list(rows[0]) if rows else [])
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def write_reports(results: dict, status: dict) -> None:
    agg = results["aggregate"]
    stats = results["statistics"]
    d = agg["evaluation_totals"]
    relative_text = ("not defined (zero fixed LER)" if stats["nonzero_relative_error_reduction"] is None
                     else f"{stats['nonzero_relative_error_reduction']:.3%}")
    table = [
        ("Fixed nominal PyMatching", d["fixed_nominal"]["errors"], d["fixed_nominal"]["ler"]),
        ("Detector-estimated PyMatching", d["detector_estimated"]["errors"], d["detector_estimated"]["ler"]),
        ("Privileged true-probability reference", d["privileged_true_probability"]["errors"], d["privileged_true_probability"]["ler"]),
    ]
    condition_table = "\n".join(
        f"| {r['probability']:.3f} | {r['shots']:,} | {r['raw_observable_errors']} ({r['raw_observable_ler']:.6%}) | "
        f"{r['fixed_nominal_errors']} ({r['fixed_nominal_ler']:.6%}) | "
        f"{r['detector_estimated_errors']} ({r['detector_estimated_ler']:.6%}) | "
        f"{r['privileged_true_probability_errors']} ({r['privileged_true_probability_ler']:.6%}) | "
        f"{r['estimated_minus_fixed']:+.6%} [{r['estimated_minus_fixed_bootstrap_95ci'][0]:+.6%}, {r['estimated_minus_fixed_bootstrap_95ci'][1]:+.6%}] | "
        f"{r['estimated_candidate_only']} / {r['estimated_fixed_only']} |"
        for r in results["per_condition"])
    decoder_table = "\n".join(f"| {name} | {errors:,} / 87,500 | {ler:.6%} |"
                                for name, errors, ler in table)
    gate_lines = "\n".join(f"- {'PASS' if value else 'FAIL'} — {key.replace('_', ' ')}"
                           for key, value in stats["gate_checks"].items())
    report = f"""# Stage 4 Development Execution Report

Status: **{status.get('status')}**; independent evidence audit: **{status.get('audit_status')}**; development gate: **{stats['gate_status']}**.

The frozen development allocation completed {agg['total_unique_shots']:,} unique shots: {agg['profile_shots']:,} detector-only profile shots, {agg['calibration_shots']:,} calibration shots, and {agg['paired_evaluation_shots']:,} paired evaluation shots across 35 root-condition checkpoints. The three decoders used the same 87,500 evaluation detector/observable pairs. No independent-test samples were allocated, accessed, or evaluated.

The complete execution took {status.get('active_runtime_seconds', float('nan')):.2f} seconds; observed peak RSS was {status.get('peak_rss_bytes', 0):,} bytes. Limits were 1,800 seconds and 2 GiB. Environment: Stim {results['software']['stim']}, PyMatching {results['software']['pymatching']}, NumPy {results['software']['numpy']}.

## Reproduction and audit

Run the commands in [REPRODUCE.md](REPRODUCE.md). `audit_stage4.py` independently rebuilt the profile estimator and all decoder models, and exact-redecoded every saved prediction array. The raw per-shot detector, observable, calibration, and prediction arrays are preserved in `run_v1/` locally and listed in `EVIDENCE_MANIFEST.json`.

See [STAGE4_RESULTS.md](STAGE4_RESULTS.md), [STAGE4_INDEPENDENT_AUDIT.md](STAGE4_INDEPENDENT_AUDIT.md), and [STAGE4_COMPETITION_EVIDENCE.md](STAGE4_COMPETITION_EVIDENCE.md). Stage 4 is synthetic development evidence only; it is not hardware validation or independent confirmation.
"""
    (HERE / "STAGE4_EXECUTION_REPORT.md").write_text(report, encoding="utf-8")

    result_report = f"""# Stage 4 Development Results

## Aggregate paired evaluation

| Decoder | Logical errors / shots | LER |
|---|---:|---:|
{decoder_table}

| Paired measure: estimated vs fixed | Count / estimate |
|---|---:|
| Candidate-only failures | {d['estimated_candidate_only_vs_fixed']:,} |
| Fixed-only failures | {d['estimated_fixed_only_vs_fixed']:,} |
| Prediction disagreements | {d['estimated_prediction_disagreements']:,} |
| Equal-weight mean nonzero-condition LER difference | {stats['primary_difference']:+.6%} |
| Relative reduction vs equal-weight nonzero fixed LER | {relative_text} |
| Root-cluster 95% bootstrap CI | [{stats['primary_bootstrap_95ci'][0]:+.6%}, {stats['primary_bootstrap_95ci'][1]:+.6%}] |
| Two-sided root sign-flip p | {stats['primary_two_sided_signflip_p']:.6g} |
| Zero-burst mean difference | {stats['zero_burst_difference']:+.6%} |
| Zero-burst one-sided 95% upper bound | {stats['zero_burst_one_sided_95_bootstrap_upper']:+.6%} |

## Condition results

| Burst p | Shots | Raw observable errors (LER) | Fixed errors (LER) | Estimated errors (LER) | Privileged reference errors (LER) | Est. − fixed [95% root CI] | Estimated-only / fixed-only errors |
|---:|---:|---:|---:|---:|---:|---:|---:|
{condition_table}

## Estimation and selection diagnostics

Across nonzero conditions, probability-estimation MAE was {stats['estimation_nonzero_mae']:.6f}, signed bias {stats['estimation_nonzero_bias']:+.6f}. Counts within absolute error 0.005 were {json.dumps(stats['estimation_within_0.005_count'], sort_keys=True)}. The profile-conditional percentile intervals covered the true nonzero p in {stats['profile_conditional_interval_coverage']}/{stats['profile_conditional_interval_count']} roots; they condition on the fixed profile batches and omit template uncertainty.

Per-root results and paired differences are in `PER_ROOT_RESULTS.csv`; per-condition summaries are in `PER_CONDITION_RESULTS.csv`; calibration estimates/intervals are in `ESTIMATION_DIAGNOSTICS.csv`; root-level paired decoder evidence is in `PAIRED_COMPARISONS.csv`.

## Frozen development gate: {stats['gate_status']}

{gate_lines}

This is not a confirmatory test. The privileged true-probability decoder is a nondeployable reference, not an adaptive arm.
"""
    (HERE / "STAGE4_RESULTS.md").write_text(result_report, encoding="utf-8")

    audit_report = f"""# Stage 4 Independent Evidence Audit

**Audit result: PASS.** Independent-test access: **none**.

## Evidence coverage

- Profile data: 9 detector-only batches, 18,000 shots, exact seeds validated.
- Calibration data: 35 detector-only batches, 70,000 shots, saved for independent estimator reconstruction.
- Paired evaluation: 35 root files, 87,500 shots; each contains 40 detector bits, one observable, and three decoder predictions.
- Total: 175,500 unique allocated shots; 79 sampling seeds plus 3 analysis seeds, all unique.
- Partition payloads independently hashed: {results['integrity']['unique_partition_count_hash_checked']}; duplicate complete partition payloads: zero.

## Scientific checks

- Every filename, probability, root ID, and calibration/evaluation seed matches the frozen inventory.
- Calibration p-hat and its conditional bootstrap interval reproduce from saved calibration detectors only.
- The auditor rebuilt Stim circuits/DEMs and PyMatching instances separately from runner predictions and re-decoded all held-out detector arrays; every stored prediction matched exactly.
- Observable labels were used only for residual scoring after model predictions were reconstructed.
- All three decoder arms were paired on each root's same evaluation detector and observable arrays.
- Seed collision screening: PASS against {json.loads((HERE / 'additional_development_seed_audit.json').read_text(encoding='utf-8'))['recoverable_historical_development_seed_values_union']:,} recoverable historical development seed values. Unrecorded historical RNG use is not ruled out.
- No independent-test sample arrays or labels were opened, read, hashed, summarized, or used. An initial broad filename-only search unintentionally displayed names under a historical independent-replication raw-data directory; none of those files was opened or used. This is documented in `ADDITIONAL_SEED_COVERAGE.md`.

## Statistics and scope

Primary equal-weight nonzero-condition effect: {stats['primary_difference']:+.6%}; 95% stratified root-cluster bootstrap CI [{stats['primary_bootstrap_95ci'][0]:+.6%}, {stats['primary_bootstrap_95ci'][1]:+.6%}], two-sided sign-flip p={stats['primary_two_sided_signflip_p']:.6g}. The inference unit is the independent root, not the shot. Seven roots per condition give limited resolution and rely on sign symmetry for the randomization test.

The audit confirms saved-data integrity and numerical reproducibility. It cannot establish external reproducibility or a hardware noise model. See `AUDIT_RESULTS.json`, `RESULTS.json`, and `EVIDENCE_MANIFEST.json` for structured values and SHA-256 digests.
"""
    (HERE / "STAGE4_INDEPENDENT_AUDIT.md").write_text(audit_report, encoding="utf-8")

    competition = f"""# Q-SHIFT Stage 4 — Competition Evidence Summary

Q-SHIFT tested whether it could estimate the strength of a synthetic correlated error from detector measurements and rebuild a conventional PyMatching decoder. It ran a distance-3, five-round simulated surface-code memory experiment. Each test batch was decoded by the same fixed decoder, the detector-estimated decoder, and a reference decoder given the true simulated probability.

The study used 175,500 new simulated shots across five burst probabilities and seven independent roots per probability. The adaptive estimate used detector-only calibration data; test outcomes were used only to score predictions. An independent audit rebuilt the decoders and reproduced every saved prediction. No quantum hardware was used and the independent test set remained sealed.

Across the four nonzero burst conditions, the detector-estimated decoder changed logical error by {stats['primary_difference']:+.6%} on average versus fixed nominal PyMatching (95% root-cluster interval [{stats['primary_bootstrap_95ci'][0]:+.6%}, {stats['primary_bootstrap_95ci'][1]:+.6%}]). The prespecified development gate was **{stats['gate_status']}**. This result is limited to the chosen synthetic burst model and should not be described as a hardware improvement or general adaptive-decoding advantage.

Full counts, uncertainty, methods, and limitations are in `STAGE4_RESULTS.md` and `STAGE4_INDEPENDENT_AUDIT.md`.
"""
    (HERE / "STAGE4_COMPETITION_EVIDENCE.md").write_text(competition, encoding="utf-8")


def write_manifest() -> None:
    included = []
    for path in sorted(HERE.rglob("*")):
        if (not path.is_file() or path.name == "EVIDENCE_MANIFEST.json"
                or "__pycache__" in path.parts or path.suffix in {".pyc", ".tmp"}):
            continue
        included.append({"path": str(path.relative_to(REPO)), "bytes": path.stat().st_size,
                         "sha256": sha256_file(path)})
    upstream = [
        REPO / "outputs/phase3a_correlated_noise_preflight/simulator.py",
        REPO / "outputs/stage4_noise_adaptive_feasibility_v1/prototype.py",
    ]
    payload = {"manifest_status": "FINALIZED_AFTER_INDEPENDENT_AUDIT",
               "study_status": "development_only",
               "independent_test_accessed": False,
               "files": included,
               "upstream_source_hashes": [{"path": str(p.relative_to(REPO)), "sha256": sha256_file(p)}
                                          for p in upstream]}
    atomic_json(HERE / "EVIDENCE_MANIFEST.json", payload)


def main() -> None:
    started = time.perf_counter()
    recorded_freeze = json.loads((HERE / "STAGE4_DEVELOPMENT_FREEZE.json").read_text(encoding="utf-8"))
    recomputed_freeze = build_freeze()
    if recorded_freeze.get("files_sha256") != recomputed_freeze.get("files_sha256"):
        raise RuntimeError("pre-sampling frozen source/configuration hashes no longer match")
    status = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    if status.get("completed_shot_count") != 175500 or status.get("completed_root_condition_count") != 35:
        raise RuntimeError("runner did not persist the complete frozen allocation; audit cannot pass")
    streams = INVENTORY["streams"]
    seeds = [int(s["seed"]) for s in streams]
    if len(seeds) != 79 or len(seeds) != len(set(seeds)):
        raise RuntimeError("sampling seed inventory missing/duplicated streams")
    seed_audit = json.loads((HERE / "seed_audit.json").read_text(encoding="utf-8"))
    supplemental_seed_audit = json.loads((HERE / "additional_development_seed_audit.json").read_text(encoding="utf-8"))
    all_allocated = [int(s["seed"]) for s in INVENTORY["streams"]]
    if (len(all_allocated) != 82 or len(set(all_allocated)) != 82
            or seed_audit.get("historical_collisions") != []
            or seed_audit.get("candidate_seed_count") != 82
            or supplemental_seed_audit.get("collisions") != []
            or supplemental_seed_audit.get("status") != "PASS_RECOVERABLE_DEVELOPMENT_METADATA"):
        raise RuntimeError("prospective RNG collision audit no longer validates")
    if INVENTORY.get("independent_test_allocated") is not False:
        raise RuntimeError("independent test allocation flag violates protocol")

    # Refit profiles from actual archived detector-only batches.
    profile_batches = []
    profile_hashes = {}
    all_partition_hashes: dict[str, str] = {}
    for s in streams:
        if s["kind"] != "profile_development_detectors":
            continue
        p, rep = float(s["probability"]), int(s["root"])
        path = PROFILE_DIR / f"profile_p{int(round(p*1000)):03d}_r{rep}.npz"
        with np.load(path, allow_pickle=False) as z:
            det = z["detectors"]
            saved_seed = int(z["seed"].item())
            saved_p = float(z["probability"].item())
            saved_rep = int(z["root"].item())
        if det.shape != (2000, 40) or det.dtype != np.uint8 or not np.isin(det, (0, 1)).all():
            raise RuntimeError(f"invalid detector-only profile batch {path}")
        if (saved_seed, saved_p, saved_rep) != (int(s["seed"]), p, rep):
            raise RuntimeError(f"profile seed/probability/root mismatch in {path}")
        digest = sha256_bytes(det.tobytes())
        if digest in all_partition_hashes.values():
            raise RuntimeError(f"duplicate detector-only profile partition: {path}")
        all_partition_hashes[f"profile:{p}:{rep}"] = digest
        profile_batches.append((p, det))
        profile_hashes[path.name] = sha256_file(path)
    if len(profile_batches) != 9:
        raise RuntimeError(f"expected nine profile batches, found {len(profile_batches)}")
    estimator = DetectorProfileEstimator.fit(profile_batches)

    stream_lookup = {}
    for s in streams:
        if s["kind"] == "stage4_calibration_detectors":
            stream_lookup[("cal", float(s["probability"]), int(s["root"]))] = s
        elif s["kind"] == "stage4_paired_evaluation":
            stream_lookup[("eval", float(s["probability"]), int(s["root"]))] = s
    if len(stream_lookup) != 70:
        raise RuntimeError(f"expected 70 root streams, found {len(stream_lookup)}")

    cal_rng = np.random.default_rng(int(CONFIG["statistical_plan"]["calibration_interval"]["seed"]))
    root_rows = []
    model_cache: dict[float, tuple] = {}
    model_times = []
    recomputed_root_records = []
    for p in PROBABILITIES:
        for root in range(7):
            path = ROOT_DIR / f"p{int(round(p*1000)):03d}_root{root:02d}.npz"
            if not path.is_file():
                raise FileNotFoundError(f"missing root checkpoint: {path}")
            file_hash = sha256_file(path)
            with np.load(path, allow_pickle=False) as z:
                required = {"calibration_detectors", "evaluation_detectors", "observables",
                            "pred_fixed", "pred_estimated", "pred_oracle", "metadata_json"}
                if not required.issubset(z.files):
                    raise RuntimeError(f"missing fields in checkpoint {path}")
                cal = z["calibration_detectors"].copy()
                det = z["evaluation_detectors"].copy()
                obs = z["observables"].copy()
                predictions = {"fixed_nominal": z["pred_fixed"].copy(),
                               "detector_estimated": z["pred_estimated"].copy(),
                               "privileged_true_probability": z["pred_oracle"].copy()}
                meta = json.loads(str(z["metadata_json"].item()))
            cal_s, eval_s = stream_lookup[("cal", p, root)], stream_lookup[("eval", p, root)]
            expected_seeds = [int(cal_s["seed"]), int(eval_s["seed"])]
            if (cal.shape, cal.dtype) != ((2000, 40), np.dtype("uint8")):
                raise RuntimeError(f"calibration dimensions/dtype failed {path}")
            if (det.shape, det.dtype) != ((2500, 40), np.dtype("uint8")):
                raise RuntimeError(f"evaluation detector dimensions/dtype failed {path}")
            if (obs.shape, obs.dtype) != ((2500, 1), np.dtype("uint8")):
                raise RuntimeError(f"observable dimensions/dtype failed {path}")
            for name, a in [("calibration", cal), ("detectors", det), ("observables", obs)]:
                if not np.isin(a, (0, 1)).all():
                    raise RuntimeError(f"nonbinary {name} values in {path}")
            if meta.get("seeds") != expected_seeds or meta.get("probability") != p or meta.get("root") != root:
                raise RuntimeError(f"filename-to-root/seed provenance mismatch {path}")
            cal_sha, det_sha, obs_sha = sha256_bytes(cal.tobytes()), sha256_bytes(det.tobytes()), sha256_bytes(obs.tobytes())
            if (meta.get("calibration_detector_sha256") != cal_sha or meta.get("detector_sha256") != det_sha
                    or meta.get("observable_sha256") != obs_sha):
                raise RuntimeError(f"stored partition digest mismatch {path}")
            for label, digest in ((f"profile:{p}:{root}", None),
                                  (f"cal:{p}:{root}", cal_sha),
                                  (f"eval_det:{p}:{root}", det_sha),
                                  (f"eval_obs:{p}:{root}", obs_sha)):
                if digest is not None:
                    if digest in all_partition_hashes.values():
                        raise RuntimeError(f"duplicate complete partition payload detected: {label}")
                    all_partition_hashes[label] = digest

            # Refit inference estimate from the saved detector calibration only.
            p_hat = estimator.estimate(cal)
            if not math.isclose(p_hat, float(meta["p_hat"]), rel_tol=0, abs_tol=1e-12):
                raise RuntimeError(f"saved p-hat not reproducible from calibration detectors: {path}")
            ci = estimator.bootstrap_interval(cal, rng=cal_rng, replicates=500)
            if not np.allclose(ci, meta["p_hat_ci_95"], rtol=0, atol=1e-12):
                raise RuntimeError(f"saved calibration interval not reproducible: {path}")

            for decoder_p in (0.0, p_hat, p):
                if decoder_p not in model_cache:
                    t0 = time.perf_counter()
                    model_cache[decoder_p] = build_auditor_matcher(decoder_p)
                    model_times.append(time.perf_counter() - t0)
            reconstructed = {
                "fixed_nominal": independently_decode(model_cache[0.0][2], det),
                "detector_estimated": independently_decode(model_cache[p_hat][2], det),
                "privileged_true_probability": independently_decode(model_cache[p][2], det),
            }
            for name in DECODERS:
                if not np.array_equal(predictions[name], reconstructed[name]):
                    raise RuntimeError(f"independent prediction re-decode mismatch: {path} decoder={name}")
            e_raw = obs[:, 0].astype(np.uint8)
            row = {"probability": p, "root": root, "calibration_seed": expected_seeds[0],
                   "evaluation_seed": expected_seeds[1], "shots": 2500, "p_hat": p_hat,
                   "p_hat_error": p_hat - p, "p_hat_abs_error": abs(p_hat - p),
                   "p_hat_ci_low": ci[0], "p_hat_ci_high": ci[1],
                   "p_hat_interval_covers_truth": int(ci[0] <= p <= ci[1]),
                   "checkpoint_sha256": file_hash,
                   "rebuild_seconds_all_3_reported": float(meta["rebuild_seconds_all_3"]),
                   "decode_seconds_fixed": float(meta["decode_seconds"][0]),
                   "decode_seconds_estimated": float(meta["decode_seconds"][1]),
                   "decode_seconds_oracle": float(meta["decode_seconds"][2])}
            errors = {}
            for name in DECODERS:
                pred = predictions[name]
                residual = np.bitwise_xor(pred, e_raw)
                errors[name] = residual
                row[f"raw_errors"] = int(e_raw.sum())
                row[f"{name}_errors"] = int(residual.sum())
                row[f"{name}_ler"] = float(residual.mean())
                row[f"{name}_prediction_disagreements_vs_fixed"] = int(np.count_nonzero(pred != predictions["fixed_nominal"]))
            row["estimated_candidate_only_vs_fixed"] = int(np.count_nonzero((errors["detector_estimated"] == 1) & (errors["fixed_nominal"] == 0)))
            row["estimated_fixed_only_vs_fixed"] = int(np.count_nonzero((errors["detector_estimated"] == 0) & (errors["fixed_nominal"] == 1)))
            row["estimated_decoder_disagreements_vs_fixed"] = int(np.count_nonzero(predictions["detector_estimated"] != predictions["fixed_nominal"]))
            row["estimated_oracle_errors"] = int(np.count_nonzero((errors["detector_estimated"] == 1) & (errors["privileged_true_probability"] == 0)))
            row["fixed_oracle_errors"] = int(np.count_nonzero((errors["detector_estimated"] == 0) & (errors["privileged_true_probability"] == 1)))
            row["estimated_minus_fixed"] = row["detector_estimated_ler"] - row["fixed_nominal_ler"]
            row["oracle_minus_fixed"] = row["privileged_true_probability_ler"] - row["fixed_nominal_ler"]
            root_rows.append(row)
            recomputed_root_records.append({"path": str(path.relative_to(REPO)), "sha256": file_hash,
                                           "probability": p, "root": root, "status": "independent_predictions_match"})

    if len(root_rows) != 35 or sum(r["shots"] for r in root_rows) != 87500:
        raise RuntimeError("paired evaluation coverage mismatch")
    status_root_hashes = {r["path"]: r["sha256"] for r in status.get("root_files", [])}
    actual_root_hashes = {r["path"]: r["sha256"] for r in recomputed_root_records}
    if status_root_hashes != actual_root_hashes:
        raise RuntimeError("controller status root-file inventory does not match independently hashed files")
    actual_profile_hashes = {f"{name}": digest for name, digest in profile_hashes.items()}
    status_profile_hashes = {Path(r["path"]).name: r["sha256"] for r in status.get("profile_files", [])}
    if status_profile_hashes != actual_profile_hashes:
        raise RuntimeError("controller status profile inventory does not match independently hashed files")
    if len(all_partition_hashes) != 114:
        raise RuntimeError("expected nonduplicated profile/calibration/evaluation detector and label partitions")

    per_condition = []
    diffs = {}
    raw_tests = {}
    zero_diffs = None
    for p in PROBABILITIES:
        rows = [r for r in root_rows if r["probability"] == p]
        rec = {"probability": p, "roots": len(rows), "shots": sum(r["shots"] for r in rows)}
        rec["raw_observable_errors"] = sum(r["raw_errors"] for r in rows)
        rec["raw_observable_ler"] = rec["raw_observable_errors"] / rec["shots"]
        for name in DECODERS:
            errs = sum(r[f"{name}_errors"] for r in rows)
            rec[f"{name}_errors"] = errs
            rec[f"{name}_ler"] = errs / rec["shots"]
        rec["estimated_minus_fixed"] = rec["detector_estimated_ler"] - rec["fixed_nominal_ler"]
        rec["oracle_minus_fixed"] = rec["privileged_true_probability_ler"] - rec["fixed_nominal_ler"]
        rec["estimated_candidate_only"] = sum(r["estimated_candidate_only_vs_fixed"] for r in rows)
        rec["estimated_fixed_only"] = sum(r["estimated_fixed_only_vs_fixed"] for r in rows)
        rec["estimated_disagreements"] = sum(r["estimated_decoder_disagreements_vs_fixed"] for r in rows)
        rec["root_effect_sd"] = float(np.std([r["estimated_minus_fixed"] for r in rows], ddof=1))
        rec["root_effect_min"] = min(r["estimated_minus_fixed"] for r in rows)
        rec["root_effect_max"] = max(r["estimated_minus_fixed"] for r in rows)
        per_condition.append(rec)
        arr = np.asarray([r["estimated_minus_fixed"] for r in rows], dtype=np.float64)
        if p == 0:
            zero_diffs = arr
        else:
            diffs[p] = arr
            raw_tests[f"p={p:.3f}"] = exact_flip(arr)

    primary = float(np.mean([diffs[p].mean() for p in NONZERO]))
    bootstrap_rng = np.random.default_rng(int(CONFIG["statistical_plan"]["bootstrap"]["seed"]))
    boot = cluster_boot(diffs, bootstrap_rng, 20000)
    primary_ci = [q(boot, 0.025), q(boot, 0.975)]
    primary_p, primary_signflip = root_signflip(
        diffs, np.random.default_rng(int(CONFIG["statistical_plan"]["primary_signflip"]["seed"])), 100000)
    zero_samples = single_stratum_boot(zero_diffs, bootstrap_rng, 20000)
    zero_harm_upper = q(zero_samples, 0.95)
    condition_intervals = {}
    for p in NONZERO:
        draws = single_stratum_boot(diffs[p], bootstrap_rng, 20000)
        condition_intervals[p] = [q(draws, 0.025), q(draws, 0.975)]
    for row in per_condition:
        if row["probability"] in condition_intervals:
            row["estimated_minus_fixed_bootstrap_95ci"] = condition_intervals[row["probability"]]
        else:
            row["estimated_minus_fixed_bootstrap_95ci"] = [q(zero_samples, 0.025), q(zero_samples, 0.975)]
    adjusted = holm(raw_tests)

    nonzero_rows = [r for r in root_rows if r["probability"] > 0]
    mae = float(np.mean([r["p_hat_abs_error"] for r in nonzero_rows]))
    bias = float(np.mean([r["p_hat_error"] for r in nonzero_rows]))
    within = {p: sum(r["p_hat_abs_error"] <= .005 for r in nonzero_rows if r["probability"] == p)
              for p in NONZERO}
    stratum_means = {p: float(diffs[p].mean()) for p in NONZERO}
    nonzero_fixed_ler = float(np.mean([next(r["fixed_nominal_ler"] for r in per_condition if r["probability"] == p) for p in NONZERO]))
    nonzero_estimated_ler = float(np.mean([next(r["detector_estimated_ler"] for r in per_condition if r["probability"] == p) for p in NONZERO]))
    rebuilds = [float(x) for r in root_rows for x in []]
    rebuilds = []
    for r in root_rows:
        # The per-root metadata carries all three build latencies; read it from raw checkpoint.
        p, root = r["probability"], r["root"]
        with np.load(ROOT_DIR / f"p{int(round(p*1000)):03d}_root{root:02d}.npz", allow_pickle=False) as z:
            meta = json.loads(str(z["metadata_json"].item()))
        rebuilds.extend(meta["decoder_rebuild_seconds"])
    med_rebuild = float(np.median(rebuilds))
    peak_rss = int(max(status.get("peak_rss_bytes", 0), psutil.Process().memory_info().rss))
    checks = {
        "nonzero_estimation_mae": mae <= .0025,
        "nonzero_estimation_absolute_bias": abs(bias) <= .0015,
        "at_least_5_of_7_estimates_within_0.005_per_nonzero_condition": all(within[p] >= 5 for p in NONZERO),
        "primary_equal_condition_mean_at_least_0.0002_improvement": primary <= -.0002,
        "primary_stratified_root_bootstrap_95ci_upper_below_zero": primary_ci[1] < 0,
        "all_4_nonzero_condition_means_favorable": sum(stratum_means[p] < 0 for p in NONZERO) == 4,
        "no_nonzero_condition_mean_harm_above_0.0002": max(stratum_means.values()) <= .0002,
        "zero_burst_one_sided_root_bootstrap_95ci_upper_within_0.0002": zero_harm_upper <= .0002,
        "median_decoder_rebuild_below_1s": med_rebuild < 1.0,
        "peak_rss_below_2gib": peak_rss < 2 * 1024**3,
    }
    gate = "PASS" if all(checks.values()) else "FAIL"
    stats = {"primary_estimand": "equal-weight mean over p=.004,.008,.012,.016 of each condition's 7-root mean paired estimated-minus-fixed LER",
             "primary_difference": primary, "primary_bootstrap_95ci": primary_ci,
             "primary_two_sided_signflip_p": primary_signflip,
             "signflip_assignments": 100000, "bootstrap_resamples": 20000,
             "per_nonzero_condition_difference": stratum_means,
             "per_nonzero_condition_bootstrap_95ci": {str(p): condition_intervals[p] for p in NONZERO},
             "per_nonzero_condition_exact_signflip_p": raw_tests,
             "per_nonzero_condition_holm_adjusted_p": adjusted,
             "zero_burst_difference": float(zero_diffs.mean()),
             "zero_burst_one_sided_95_bootstrap_upper": zero_harm_upper,
             "zero_burst_bootstrap_resamples": 20000,
             "estimation_nonzero_mae": mae, "estimation_nonzero_bias": bias,
             "nonzero_fixed_mean_ler": nonzero_fixed_ler,
             "nonzero_estimated_mean_ler": nonzero_estimated_ler,
             "nonzero_relative_error_reduction": ((nonzero_fixed_ler - nonzero_estimated_ler) / nonzero_fixed_ler
                                                  if nonzero_fixed_ler else None),
             "estimation_within_0.005_count": {str(k): int(v) for k, v in within.items()},
             "profile_conditional_interval_coverage": int(sum(r["p_hat_interval_covers_truth"] for r in nonzero_rows)),
             "profile_conditional_interval_count": len(nonzero_rows),
             "median_single_decoder_rebuild_seconds": med_rebuild,
             "peak_process_rss_bytes_observed_at_audit": peak_rss,
             "gate_status": gate, "gate_checks": checks,
             "primary_signflip_null_assumption": "Independent root effects are sign-symmetric under the null within the prespecified equal-stratum estimand; with only seven roots per stratum, the p-value is coarse and sensitivity to this assumption must be reported."}

    # Paired aggregate totals and explicit fidelity coverage.
    aggregate = {"total_unique_shots": 175500, "profile_shots": 18000,
                 "calibration_shots": 70000, "paired_evaluation_shots": 87500,
                 "root_condition_checkpoints": 35, "roots_per_condition": 7,
                 "raw_observable_errors": sum(r["raw_errors"] for r in root_rows),
                 "raw_observable_ler": sum(r["raw_errors"] for r in root_rows) / 87500,
                 "evaluation_totals": {}}
    for name in DECODERS:
        total_err = sum(r[f"{name}_errors"] for r in root_rows)
        aggregate["evaluation_totals"][name] = {"errors": total_err, "shots": 87500, "ler": total_err / 87500}
    aggregate["evaluation_totals"]["estimated_candidate_only_vs_fixed"] = sum(r["estimated_candidate_only_vs_fixed"] for r in root_rows)
    aggregate["evaluation_totals"]["estimated_fixed_only_vs_fixed"] = sum(r["estimated_fixed_only_vs_fixed"] for r in root_rows)
    aggregate["evaluation_totals"]["estimated_prediction_disagreements"] = sum(r["estimated_decoder_disagreements_vs_fixed"] for r in root_rows)
    results = {"study": "Q-SHIFT Stage 4 full development evaluation", "status": "independently_recomputed",
               "gate_status": gate, "software": {"stim": stim.__version__, "pymatching": pymatching.__version__,
                                                   "numpy": np.__version__},
               "aggregate": aggregate, "statistics": stats,
               "per_condition": per_condition,
               "estimation_diagnostics": {"nonzero_mae": mae, "nonzero_bias": bias,
                                          "within_0.005_by_condition": {str(k): int(v) for k, v in within.items()},
                                          "conditional_interval_covered_roots": stats["profile_conditional_interval_coverage"],
                                          "conditional_interval_roots": len(nonzero_rows)},
               "integrity": {"all_35_root_files_present": True, "all_profile_batches_present": True,
                             "all_stored_predictions_redecoded_exactly": True,
                             "seed_uniqueness": True, "sample_partition_payload_hashes_unique": True,
                             "sealed_independent_test_accessed": False, "recomputed_roots": recomputed_root_records,
                             "profile_files_sha256": profile_hashes,
                             "unique_partition_count_hash_checked": len(all_partition_hashes)},
               "runtime": {"independent_audit_seconds": time.perf_counter() - started,
                           "auditor_decoder_constructions": len(model_cache),
                           "auditor_decoder_construction_time_seconds_sum": float(sum(model_times)),
                           "max_decoder_construction_seconds": float(max(model_times) if model_times else 0)}}

    atomic_json(OUT / "RESULTS.json", results)
    atomic_json(OUT / "AUDIT_RESULTS.json", {"status": "PASS" if results["integrity"]["all_stored_predictions_redecoded_exactly"] else "FAIL",
                                             "independent_test_accessed": False,
                                             "verified_root_count": len(root_rows),
                                             "verified_evaluation_shots": aggregate["paired_evaluation_shots"],
                                             "prediction_redecode": "exact_match_all_three_decoder_arms",
                                             "results_sha256": sha256_file(OUT / "RESULTS.json"),
                                             "per_root_source_files": recomputed_root_records})
    write_csv(OUT / "PER_ROOT_RESULTS.csv", root_rows)
    write_csv(OUT / "PER_CONDITION_RESULTS.csv", per_condition)
    estimation_rows = [{k: r[k] for k in ("probability", "root", "p_hat", "p_hat_error", "p_hat_abs_error",
                                          "p_hat_ci_low", "p_hat_ci_high", "p_hat_interval_covers_truth")}
                       for r in root_rows]
    write_csv(OUT / "ESTIMATION_DIAGNOSTICS.csv", estimation_rows)
    pair_rows = []
    for r in root_rows:
        pair_rows.append({k: r[k] for k in ("probability", "root", "shots", "fixed_nominal_errors",
                                            "detector_estimated_errors", "privileged_true_probability_errors",
                                            "estimated_candidate_only_vs_fixed", "estimated_fixed_only_vs_fixed",
                                            "estimated_decoder_disagreements_vs_fixed", "estimated_minus_fixed",
                                            "oracle_minus_fixed")})
    write_csv(OUT / "PAIRED_COMPARISONS.csv", pair_rows)

    # Terminal success is written only after independent array/model/statistical audit completed.
    status["audit_status"] = "PASS" if results["integrity"]["all_stored_predictions_redecoded_exactly"] else "FAIL"
    status["status"] = "completed" if status["audit_status"] == "PASS" else "audit_failed"
    status["independent_audit_completed_unix"] = time.time()
    status["gate_status"] = gate
    atomic_json(STATUS_PATH, status)
    write_reports(results, status)
    write_manifest()
    print(json.dumps({"audit": status["audit_status"], "gate": gate,
                      "primary_difference": primary, "primary_95ci": primary_ci,
                      "primary_signflip_p": primary_signflip,
                      "evaluation_shots": 87500}, indent=2))


if __name__ == "__main__":
    main()
