"""CUSUM vs periodic LDA profile switching under stable and alternating noise."""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from adaptive_basis_sprt import PROFILES
from adaptive_basis_sprt_common_variance import llr_stream
from bias_identification import feature_masks, make_features
from basis_alignment_distance7 import build

HERE = Path(__file__).resolve().parent
FROZEN = json.loads((HERE / "adaptive_basis_sprt_results.json").read_text())
MAX_WINDOWS_STABLE = 100
PRE_WINDOWS_STABLE = 10
DWELLS = (1_000, 10_000)
PRE_SEGMENTS, MAIN_SEGMENTS = 20, 101
PRE_SEEDS = tuple(range(2026116001, 2026116017))
MAIN_SEEDS = tuple(range(2026116021, 2026116037))
THRESHOLD = float(np.log(200))


def sample_scores(profile: str, measurement_p: float, shots: int, seed: int) -> tuple[np.ndarray, float]:
    from noise_model import build_circuit as source_build

    circuit = build("z", profile, 3, 5, bias_ratio=10.0, gate_p=0.003, measurement_p=measurement_p)
    source = source_build("z", profile, distance=3, rounds=5, bias_ratio=10.0, gate_p=0.003, measurement_p=measurement_p)
    if str(circuit) != str(source):
        raise RuntimeError(f"source builder mismatch: {profile}, measurement_p={measurement_p}")
    masks = feature_masks(circuit, 3, 5)
    started = time.perf_counter()
    det = circuit.compile_detector_sampler(seed=seed).sample(shots=shots)
    elapsed = time.perf_counter() - started
    w = np.asarray(json.loads((HERE / "bias_identification_results.json").read_text())["training"]["weights"], dtype=float)
    b = float(json.loads((HERE / "bias_identification_results.json").read_text())["training"]["intercept"])
    score = make_features(det, masks) @ w + b
    if not np.isfinite(score).all():
        raise RuntimeError("non-finite score stream")
    return score, elapsed


def initial_state(scores: np.ndarray) -> bool:
    """True means choose X memory; initialize with a frozen 100-shot LDA block."""
    return bool(np.mean(scores[:100]) < 0)


def run_cusum(scores: np.ndarray, model: str) -> tuple[bool, list[tuple[int, bool]]]:
    llrs = llr_stream(scores, model)
    state_x = initial_state(scores)
    gz = gx = 0.0
    events = []
    for i in range(100, len(scores)):
        llr = float(llrs[i])
        if state_x:
            gz = max(0.0, gz + llr)
            if gz >= THRESHOLD:
                state_x = False
                gz = gx = 0.0
                events.append((i, state_x))
        else:
            gx = max(0.0, gx - llr)
            if gx >= THRESHOLD:
                state_x = True
                gz = gx = 0.0
                events.append((i, state_x))
    return state_x, events


def run_periodic_lda(scores: np.ndarray) -> tuple[bool, list[tuple[int, bool]]]:
    state_x = initial_state(scores)
    events = []
    for end in range(200, len(scores) + 1, 100):
        choice_x = bool(np.mean(scores[end - 100 : end]) < 0)
        if choice_x != state_x:
            state_x = choice_x
            events.append((end - 1, state_x))
    return state_x, events


def stable_metrics(scores: np.ndarray, truth_x: bool) -> dict:
    variants = {
        "class_specific_cusum": run_cusum(scores, "heteroscedastic"),
        "common_variance_cusum": run_cusum(scores, "common_variance"),
        "periodic_100_shot_lda": run_periodic_lda(scores),
    }
    initial_error = int(initial_state(scores) != truth_x)
    row = {"episodes": 0, "total_shots": len(scores), "initial_errors": initial_error, "variants": {}}
    for name, (_, events) in variants.items():
        false_switches = sum(int(new_x != truth_x) for _, new_x in events)
        row["variants"][name] = {
            "total_switches": len(events),
            "false_switches": false_switches,
            "episodes_with_false_switch": int(false_switches > 0),
            "false_switches_per_100k_shots": false_switches * 100_000 / max(1, len(scores) - 100),
        }
    return row


def alternating_metrics(scores: np.ndarray, dwell: int, segments: int) -> dict:
    true_states = [i % 2 == 0 for i in range(segments)]
    boundaries = [(i * dwell, true_states[i]) for i in range(1, segments)]
    methods = {
        "class_specific_cusum": run_cusum(scores, "heteroscedastic")[1],
        "common_variance_cusum": run_cusum(scores, "common_variance")[1],
        "periodic_100_shot_lda": run_periodic_lda(scores)[1],
    }
    output = {"segments": segments, "dwell_shots": dwell, "transitions": len(boundaries), "methods": {}}
    for name, events in methods.items():
        delays, missed, already_correct = [], 0, 0
        for boundary, new_truth_x in boundaries:
            prior_events = [event for event in events if event[0] < boundary]
            current_state = initial_state(scores) if not prior_events else prior_events[-1][1]
            if current_state == new_truth_x:
                already_correct += 1
                delays.append(0)
                continue
            next_boundary = boundary + dwell
            detection = next((event for event in events if boundary <= event[0] < next_boundary and event[1] == new_truth_x), None)
            if detection is None:
                missed += 1
            else:
                delays.append(int(detection[0] - boundary + 1))
        output["methods"][name] = {
            "detected_or_already_correct": len(delays),
            "missed_transitions": missed,
            "already_correct_at_change": already_correct,
            "median_delay_shots": float(np.median(delays)) if delays else None,
            "p90_delay_shots": float(np.quantile(delays, 0.9)) if delays else None,
            "switch_events": len(events),
        }
    return output


def run(preflight: bool) -> dict:
    start = time.perf_counter()
    episodes = PRE_WINDOWS_STABLE if preflight else MAX_WINDOWS_STABLE
    segments = PRE_SEGMENTS if preflight else MAIN_SEGMENTS
    seeds = PRE_SEEDS if preflight else MAIN_SEEDS
    stable, alternating = [], []
    seed_i = 0
    total_samples = 0
    stable_elapsed = 0.0
    for regime, measurement_p in (("nominal", 0.003), ("measurement_shift", 0.006)):
        for profile in PROFILES:
            truth_x = profile == "x_biased"
            for dwell in DWELLS:
                n = episodes * dwell
                score, elapsed = sample_scores(profile, measurement_p, n, seeds[seed_i])
                seed_i += 1
                total_samples += n
                stable_elapsed += elapsed
                ep_metrics = [stable_metrics(score[i * dwell : (i + 1) * dwell], truth_x) for i in range(episodes)]
                stable.append({
                    "regime": regime,
                    "measurement_p": measurement_p,
                    "profile": profile,
                    "dwell_shots": dwell,
                    "episodes": episodes,
                    "seed": seeds[seed_i - 1],
                    "sampling_seconds": elapsed,
                    "initial_errors": sum(x["initial_errors"] for x in ep_metrics),
                    "variant_totals": {
                        name: {
                            "total_switches": sum(x["variants"][name]["total_switches"] for x in ep_metrics),
                            "false_switches": sum(x["variants"][name]["false_switches"] for x in ep_metrics),
                            "episodes_with_false_switch": sum(x["variants"][name]["episodes_with_false_switch"] for x in ep_metrics),
                            "false_switches_per_100k_shots": sum(x["variants"][name]["false_switches"] for x in ep_metrics) * 100_000 / max(1, episodes * (dwell - 100)),
                        }
                        for name in ("class_specific_cusum", "common_variance_cusum", "periodic_100_shot_lda")
                    },
                })
        for dwell in DWELLS:
            nseg = segments
            n_x = (nseg + 1) // 2
            n_z = nseg // 2
            x_scores, sx = sample_scores("x_biased", measurement_p, n_x * dwell, seeds[seed_i])
            seed_x = seeds[seed_i]
            seed_i += 1
            z_scores, sz = sample_scores("z_biased", measurement_p, n_z * dwell, seeds[seed_i])
            seed_z = seeds[seed_i]
            seed_i += 1
            total_samples += nseg * dwell
            stable_elapsed += sx + sz
            parts, xi, zi = [], 0, 0
            for seg in range(nseg):
                if seg % 2 == 0:
                    parts.append(x_scores[xi : xi + dwell]); xi += dwell
                else:
                    parts.append(z_scores[zi : zi + dwell]); zi += dwell
            stream = np.concatenate(parts)
            alternating.append({
                "regime": regime,
                "measurement_p": measurement_p,
                "dwell_shots": dwell,
                "segments": nseg,
                "seeds": [seed_x, seed_z],
                "sampling_seconds": sx + sz,
                **alternating_metrics(stream, dwell, nseg),
            })
    elapsed = time.perf_counter() - start
    output = {
        "status": "change_detection_preflight" if preflight else "change_detection_validation",
        "threshold": THRESHOLD,
        "initialization": "first 100 scores, frozen LDA mean-sign; no profile label",
        "profile_conditions": stable,
        "alternating_conditions": alternating,
        "stable_episodes_per_condition": episodes,
        "alternating_segments_per_condition": segments,
        "elapsed_seconds": elapsed,
        "new_source_equivalent_samples": total_samples,
        "scope": "detector-only simulator change detection and false switching; no logical output",
    }
    if preflight:
        full_samples = (
            MAX_WINDOWS_STABLE * sum(DWELLS) * 2 * 2
            + MAIN_SEGMENTS * sum(DWELLS) * 2
        )
        output["projected_main_seconds"] = elapsed * full_samples / max(1, total_samples)
        output["runtime_cap_seconds"] = 300
        output["runtime_gate_passed"] = output["projected_main_seconds"] <= 300
        path = HERE / "adaptive_basis_change_detection_preflight.json"
    else:
        path = HERE / "adaptive_basis_change_detection_results.json"
    path.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"status": output["status"], "projected_main_seconds": output.get("projected_main_seconds"), "new_samples": total_samples, "output": str(path)}, indent=2))
    return output


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    result = run(args.preflight)
    if args.preflight and not result["runtime_gate_passed"]:
        raise SystemExit(1)
