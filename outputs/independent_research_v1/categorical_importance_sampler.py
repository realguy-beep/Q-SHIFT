"""Exact categorical-channel instrumentation for circuit-level likelihood weighting."""
from __future__ import annotations

import argparse
import json
import resource
import sys
import time
from pathlib import Path

import numpy as np
import pymatching
import stim

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PHASE2B = REPO / "outputs" / "phase2b_pauli_bias"
sys.path.insert(0, str(PHASE2B))
from noise_model import MEMORY_BASES, PAULI_PAIRS, REGIMES, build_circuit  # noqa: E402

ALPHA = 5.0
PREFLIGHT_DIRECT = (202611501, 202611502, 202611503, 202611504, 202611505, 202611506)
PREFLIGHT_TILTED = (202611507, 202611508, 202611509, 202611510, 202611511, 202611512)
MAIN_DIRECT = (202611521, 202611522, 202611523, 202611524, 202611525, 202611526)
MAIN_TILTED = (202611531, 202611532, 202611533, 202611534, 202611535, 202611536)
CONDITIONS = tuple((basis, regime) for basis in MEMORY_BASES for regime in REGIMES)
SYMBOL_TO_TARGET = {"X": stim.target_x, "Y": stim.target_y, "Z": stim.target_z}


def tilted_channel(probabilities: list[float], alpha: float) -> list[float]:
    p = np.asarray(probabilities, dtype=np.float64)
    identity = 1.0 - float(p.sum())
    if identity < -1e-12 or alpha <= 0:
        raise ValueError("invalid categorical probabilities or tilt factor")
    denom = identity + alpha * float(p.sum())
    return [float(alpha * x / denom) for x in p]


def instrument_circuit(circuit: stim.Circuit, alpha: float,
                       channel_proposals: list[list[float]] | None = None) -> tuple[stim.Circuit, list[dict]]:
    """Replace each pair channel with an exact categorical branch and private flags."""
    source = circuit.flattened()
    out = stim.Circuit()
    events: list[dict] = []
    flag_qubits: list[int] = []
    next_flag_qubit = circuit.num_qubits
    event_index = 0

    for instruction in source:
        if instruction.name != "PAULI_CHANNEL_2":
            out.append(instruction.name, instruction.targets_copy(), instruction.gate_args_copy())
            continue

        probabilities = [float(x) for x in instruction.gate_args_copy()]
        if len(probabilities) != 15:
            raise RuntimeError("PAULI_CHANNEL_2 did not provide 15 nonidentity probabilities")
        targets = instruction.targets_copy()
        if len(targets) % 2:
            raise RuntimeError("PAULI_CHANNEL_2 has an odd number of qubit targets")
        # Each target pair in one PAULI_CHANNEL_2 instruction is an independent draw.
        for offset in range(0, len(targets), 2):
            if channel_proposals is None:
                q_probabilities = tilted_channel(probabilities, alpha)
            else:
                if event_index >= len(channel_proposals):
                    raise ValueError("channel proposal list is shorter than the circuit's channel-pair count")
                q_probabilities = [float(x) for x in channel_proposals[event_index]]
                if len(q_probabilities) != 15 or min(q_probabilities) <= 0 or sum(q_probabilities) >= 1:
                    raise ValueError(f"invalid categorical proposal at channel-pair index {event_index}")
            data_qubits = (int(targets[offset].value), int(targets[offset+1].value))
            flags = tuple(range(next_flag_qubit, next_flag_qubit+4))
            next_flag_qubit += 4
            previous_probability = 0.0
            for outcome, (pauli_pair, q) in enumerate(zip(PAULI_PAIRS, q_probabilities, strict=True), start=1):
                conditional_q = q / (1.0-previous_probability)
                error_targets = []
                for symbol, qubit in zip(pauli_pair, data_qubits, strict=True):
                    if symbol != "I":
                        error_targets.append(SYMBOL_TO_TARGET[symbol](qubit))
                for bit, flag_qubit in enumerate(flags):
                    if (outcome >> bit) & 1:
                        error_targets.append(stim.target_x(flag_qubit))
                gate = "E" if outcome == 1 else "ELSE_CORRELATED_ERROR"
                out.append(gate, error_targets, [conditional_q])
                previous_probability += q
            events.append({
                "p": probabilities,
                "q": q_probabilities,
                "p_identity": 1.0-float(sum(probabilities)),
                "q_identity": 1.0-float(sum(q_probabilities)),
                "flags": flags,
                "data_qubits": data_qubits,
            })
            flag_qubits.extend(flags)
            event_index += 1

    if channel_proposals is not None and event_index != len(channel_proposals):
        raise ValueError("channel proposal list is longer than the circuit's channel-pair count")

    if events:
        out.append("M", flag_qubits)
        n = len(flag_qubits)
        for i in range(n):
            out.append("OBSERVABLE_INCLUDE", [stim.target_rec(-n+i)], [circuit.num_observables+i])

    if out.num_detectors != circuit.num_detectors:
        raise RuntimeError(f"detector count changed: {circuit.num_detectors} -> {out.num_detectors}")
    if out.num_observables != circuit.num_observables + len(flag_qubits):
        raise RuntimeError("unexpected instrumented observable count")
    return out, events


def categorical_log_weights(flag_bits: np.ndarray, events: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    if flag_bits.ndim != 3 or flag_bits.shape[1:] != (len(events), 4):
        raise ValueError("flag data shape does not match categorical event table")
    codes = (flag_bits.astype(np.uint8) @ np.asarray([1, 2, 4, 8], dtype=np.uint8)).astype(np.uint8)
    if np.any(codes > 15):
        raise RuntimeError("invalid four-bit categorical outcome code")
    logw = np.zeros(len(codes), dtype=np.float64)
    for j, event in enumerate(events):
        p = np.asarray([event["p_identity"], *event["p"]], dtype=np.float64)
        q = np.asarray([event["q_identity"], *event["q"]], dtype=np.float64)
        if np.any(p <= 0) or np.any(q <= 0):
            raise ValueError("categorical support must be strictly positive for likelihood weighting")
        lookup = np.log(p/q)
        logw += lookup[codes[:, j]]
    return logw, codes


def validate_instrumentation() -> dict:
    """Exercise all 16 outcomes and verify observed data Pauli actions and probabilities."""
    # Equal p_i gives a simple known distribution with nonzero identity probability.
    ps = [0.01]*15
    base = stim.Circuit("R 0 1\nPAULI_CHANNEL_2(" + ",".join(map(str, ps)) + ") 0 1\nM 0 1")
    shots = 50000
    outputs = {}
    for alpha, seed in ((1.0, 61101), (ALPHA, 61102)):
        inst, events = instrument_circuit(base, alpha)
        measurements = inst.compile_sampler(seed=seed).sample(shots=shots)
        data = measurements[:, :2]
        flags = measurements[:, 2:6]
        codes = flags.astype(np.uint8) @ np.asarray([1, 2, 4, 8], dtype=np.uint8)
        counts = np.bincount(codes, minlength=16)
        expected = np.asarray([1-sum(events[0]["q"]), *events[0]["q"]])
        for code in range(16):
            mean = shots*expected[code]
            sd = np.sqrt(shots*expected[code]*(1-expected[code]))
            if abs(counts[code]-mean) > 6*sd+2:
                raise RuntimeError(f"instrumented categorical frequency failed for alpha={alpha}, code={code}")
        pairs = ("II", *PAULI_PAIRS)
        mismatch = 0
        for code, pauli_pair in enumerate(pairs):
            x_pattern = np.asarray([symbol in "XY" for symbol in pauli_pair], dtype=np.bool_)
            mismatch += int(np.sum((codes == code) & np.any(data != x_pattern, axis=1)))
        if mismatch:
            raise RuntimeError(f"flag/data Pauli mapping had {mismatch} mismatches")
        outputs[str(alpha)] = {"counts": counts.astype(int).tolist(),
                               "expected_probabilities": expected.tolist(),
                               "data_pauli_mismatches": mismatch,
                               "instrumented_qubits": inst.num_qubits}

    # Confirm the assumed PAULI_CHANNEL_2 argument order against Stim itself. A
    # near-deterministic one-hot channel is observed in all four X/Z basis pairs.
    argument_order_checks = 0
    for index, pair in enumerate(PAULI_PAIRS):
        ps = [0.0]*15
        ps[index] = 0.99
        for axes in (("X", "X"), ("X", "Z"), ("Z", "X"), ("Z", "Z")):
            body = "R 0 1\n"
            if axes[0] == "X":
                body += "H 0\n"
            if axes[1] == "X":
                body += "H 1\n"
            body += "PAULI_CHANNEL_2(" + ",".join(map(str, ps)) + ") 0 1\n"
            if axes[0] == "X":
                body += "H 0\n"
            if axes[1] == "X":
                body += "H 1\n"
            body += "M 0 1"
            samples = stim.Circuit(body).compile_sampler(seed=62000+index*4+len(axes)).sample(shots=500)
            expected = np.asarray([symbol in ("Y", "Z") if axis == "X" else symbol in ("X", "Y")
                                   for symbol, axis in zip(pair, axes, strict=True)], dtype=np.bool_)
            # At p=0.99, permit rare identity outcomes but require the expected
            # measurement-flip pattern to win by a clear majority.
            means = np.mean(samples, axis=0)
            if np.any(np.where(expected, means <= 0.5, means >= 0.5)):
                raise RuntimeError(f"Stim PAULI_CHANNEL_2 argument order mismatch for {pair} in {axes} basis")
            argument_order_checks += 1

    # Stim permits several independent target pairs in one channel instruction;
    # verify consecutive E/ELSE chains reset independently between those pairs.
    multi_pair = stim.Circuit(
        "R 0 1 2 3\nPAULI_CHANNEL_2(" + ",".join(["0.01"]*15) + ") 0 1 2 3\nM 0 1 2 3")
    multi_instrumented, multi_events = instrument_circuit(multi_pair, 1.0)
    multi_samples = multi_instrumented.compile_sampler(seed=62100).sample(shots=shots)
    multi_flags = multi_samples[:, 4:].reshape(shots, 2, 4)
    multi_codes = (multi_flags.astype(np.uint8) @ np.asarray([1, 2, 4, 8], dtype=np.uint8)).astype(np.uint8)
    event_error_rates = []
    for event_index, event in enumerate(multi_events):
        counts = np.bincount(multi_codes[:, event_index], minlength=16)
        expected = np.asarray([event["q_identity"], *event["q"]])
        for code in range(16):
            mean = shots*expected[code]
            sd = np.sqrt(shots*expected[code]*(1-expected[code]))
            if abs(counts[code]-mean) > 6*sd+2:
                raise RuntimeError(f"multi-pair event {event_index} category {code} failed frequency gate")
        event_error_rates.append(float(np.mean(multi_codes[:, event_index] != 0)))
    joint_rate = float(np.mean((multi_codes[:, 0] != 0) & (multi_codes[:, 1] != 0)))
    independent_joint = event_error_rates[0]*event_error_rates[1]
    joint_se = np.sqrt(max(independent_joint*(1-independent_joint), 0)/shots)
    if abs(joint_rate-independent_joint) > 6*joint_se+0.0005:
        raise RuntimeError("multiple PAULI_CHANNEL_2 target pairs did not remain independent")

    # A noiseless Clifford with rec-based detectors/observables must be unchanged by adding flags.
    no_noise = stim.Circuit(
        "R 0 1\nPAULI_CHANNEL_2(" + ",".join(["0"]*15) + ") 0 1\n"
        "CX 0 1\nM 0 1\nDETECTOR rec[-2] rec[-1]\nOBSERVABLE_INCLUDE(0) rec[-1]")
    original = no_noise.compile_detector_sampler(seed=61103).sample(shots=10, separate_observables=True)
    flagged, _ = instrument_circuit(no_noise, ALPHA)
    instrumented = flagged.compile_detector_sampler(seed=61103).sample(shots=10, separate_observables=True)
    if not np.array_equal(original[0], instrumented[0]) or not np.array_equal(original[1], instrumented[1][:, :1]):
        raise RuntimeError("noiseless Clifford detector/observable behavior changed under instrumentation")

    return {"shots_per_channel": shots, "channel_probabilities": ps,
            "alpha": ALPHA, "direct_and_tilted": outputs,
            "stim_argument_order_checks": argument_order_checks,
            "multi_pair_event_error_rates": event_error_rates,
            "multi_pair_joint_error_rate": joint_rate,
            "multi_pair_independent_product": independent_joint,
            "noiseless_detector_observable_equality": True,
            "scope": "synthetic channel instrumentation only; no Phase 2B shots"}


def decode_failures(matching: pymatching.Matching, detectors: np.ndarray,
                    logicals: np.ndarray) -> np.ndarray:
    failures = np.empty(len(detectors), dtype=np.bool_)
    for i, syndrome in enumerate(detectors):
        predicted = np.asarray(matching.decode(syndrome), dtype=np.bool_).reshape(-1)
        failures[i] = not np.array_equal(predicted, logicals[i])
    return failures


def run_condition(basis: str, regime: str, shots: int,
                  direct_seed: int, tilted_seed: int) -> dict:
    circuit = build_circuit(basis, regime)
    dem = circuit.detector_error_model(decompose_errors=True, approximate_disjoint_errors=0.0018)
    matching = pymatching.Matching.from_detector_error_model(dem, enable_correlations=True)
    original_observables = circuit.num_observables
    started = time.perf_counter()
    direct_circuit, direct_events = instrument_circuit(circuit, 1.0)
    tilted_circuit, tilted_events = instrument_circuit(circuit, ALPHA)
    if len(direct_events) != len(tilted_events):
        raise RuntimeError("direct and tilted circuits expose different channel event counts")
    direct_sample = direct_circuit.compile_detector_sampler(seed=direct_seed).sample(
        shots=shots, separate_observables=True)
    direct_detectors, direct_outputs = direct_sample
    direct_logicals = direct_outputs[:, :original_observables]
    direct_failures = decode_failures(matching, direct_detectors, direct_logicals)
    direct_elapsed = time.perf_counter()-started

    started = time.perf_counter()
    tilted_sample = tilted_circuit.compile_detector_sampler(seed=tilted_seed).sample(
        shots=shots, separate_observables=True)
    tilted_detectors, tilted_outputs = tilted_sample
    tilted_logicals = tilted_outputs[:, :original_observables]
    flags = tilted_outputs[:, original_observables:].reshape(shots, len(tilted_events), 4)
    logw, codes = categorical_log_weights(flags, tilted_events)
    if not np.all(np.isfinite(logw)):
        raise RuntimeError("nonfinite categorical circuit likelihood ratio")
    tilted_failures = decode_failures(matching, tilted_detectors, tilted_logicals)
    weights = np.exp(logw)
    weighted_terms = weights*tilted_failures
    tilted_elapsed = time.perf_counter()-started
    estimate = float(weighted_terms.mean())
    se = float(weighted_terms.std(ddof=1)/np.sqrt(shots)) if shots > 1 else float("inf")
    failure_weights = weights[tilted_failures]
    ess = (float(failure_weights.sum()**2/np.square(failure_weights).sum())
           if len(failure_weights) and np.square(failure_weights).sum() else 0.0)
    return {
        "memory_basis": basis, "regime": regime,
        "direct_seed": direct_seed, "tilted_seed": tilted_seed, "shots_per_arm": shots,
        "base_detectors": int(circuit.num_detectors),
        "base_logical_observables": int(original_observables),
        "two_qubit_categorical_locations": len(direct_events),
        "augmented_flag_qubits": 4*len(direct_events),
        "direct_failures": int(direct_failures.sum()),
        "direct_ler": float(direct_failures.mean()),
        "tilted_failures_unweighted": int(tilted_failures.sum()),
        "importance_weighted_ler": estimate,
        "importance_standard_error": se,
        "direct_relative_se": (float(np.sqrt(direct_failures.mean()*(1-direct_failures.mean())/shots)/direct_failures.mean())
                               if direct_failures.mean() > 0 else float("inf")),
        "importance_relative_se": se/estimate if estimate > 0 else float("inf"),
        "failure_weight_effective_sample_size": ess,
        "max_abs_log_weight": float(np.max(np.abs(logw))),
        "max_weight": float(weights.max()),
        "flag_codes_observed": int(np.unique(codes).size),
        "direct_seconds": direct_elapsed,
        "tilted_seconds": tilted_elapsed,
        "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--shots", type=int, default=20000)
    parser.add_argument("--replicates", type=int, default=1,
                        help="independent replication count (use 8 for the predeclared stability check)")
    parser.add_argument("--replicate-start", type=int, default=0,
                        help="replication block offset; 8 selects the predeclared second block")
    args = parser.parse_args()
    if args.shots <= 0:
        parser.error("--shots must be positive")
    if args.replicates <= 0 or (args.preflight and args.replicates != 1):
        parser.error("replicates must be positive; preflight and replicate modes cannot be combined")
    if args.replicates > 1 and args.replicate_start not in (0, 8):
        parser.error("only the predeclared replicate starts 0 and 8 are valid")
    validation = validate_instrumentation()
    preflight = args.preflight
    shots = 200 if preflight else args.shots
    if args.replicates > 1:
        started = time.perf_counter()
        replicate_rows = []
        direct_seed_base = 202611601 if args.replicate_start == 0 else 202611801
        tilted_seed_base = 202611701 if args.replicate_start == 0 else 202611901
        for rep in range(args.replicates):
            direct_seeds = tuple(direct_seed_base+6*rep+i for i in range(6))
            tilted_seeds = tuple(tilted_seed_base+6*rep+i for i in range(6))
            replicate_rows.append([
                run_condition(b, r, shots, ds, ts)
                for (b, r), ds, ts in zip(CONDITIONS, direct_seeds, tilted_seeds, strict=True)
            ])
        summaries = []
        for i, (basis, regime) in enumerate(CONDITIONS):
            direct = np.asarray([block[i]["direct_ler"] for block in replicate_rows])
            tilted = np.asarray([block[i]["importance_weighted_ler"] for block in replicate_rows])
            direct_sd = float(direct.std(ddof=1))
            tilted_sd = float(tilted.std(ddof=1))
            differences = tilted-direct
            diff_se = float(differences.std(ddof=1)/np.sqrt(args.replicates))
            summaries.append({
                "memory_basis": basis, "regime": regime,
                "direct_mean": float(direct.mean()), "importance_mean": float(tilted.mean()),
                "direct_between_replicate_sd": direct_sd,
                "importance_between_replicate_sd": tilted_sd,
                "importance_to_direct_sd_ratio": tilted_sd/direct_sd if direct_sd else float("inf"),
                "mean_importance_minus_direct": float(differences.mean()),
                "difference_standard_error": diff_se,
            })
        output = {
            "status": "exact_categorical_independent_replication_check",
            "stim_version": stim.__version__, "pymatching_version": pymatching.__version__,
            "tilt_factor": ALPHA, "channel_instrumentation_validation": validation,
            "replicates": args.replicates,
            "replicate_start": args.replicate_start,
            "shots_per_arm_per_condition_per_replicate": shots,
            "condition_summaries": summaries, "replicate_results": replicate_rows,
            "conditions_with_at_least_25pct_between_replicate_sd_reduction": sum(
                row["importance_to_direct_sd_ratio"] <= 0.75 for row in summaries),
            "elapsed_seconds": time.perf_counter()-started,
            "stochastic_circuit_shots": shots*len(CONDITIONS)*2*args.replicates,
            "scope": "independent stability check under exact categorical Phase 2B channels, fixed approximate-DEM decoder",
        }
        target_name = ("categorical_importance_replication.json" if args.replicate_start == 0
                       else "categorical_importance_replication_2.json")
        target = HERE/target_name
        target.write_text(json.dumps(output, indent=2)+"\n", encoding="utf-8")
        print(f"Wrote {target}; elapsed={output['elapsed_seconds']:.3f}s")
        for row in summaries:
            print(row["memory_basis"], row["regime"],
                  f"SD={row['direct_between_replicate_sd']:.6g}->{row['importance_between_replicate_sd']:.6g}",
                  f"ratio={row['importance_to_direct_sd_ratio']:.3f}",
                  f"mean_diff={row['mean_importance_minus_direct']:.6g} +/- {row['difference_standard_error']:.3g}")
        return 0

    direct_seeds = PREFLIGHT_DIRECT if preflight else MAIN_DIRECT
    tilted_seeds = PREFLIGHT_TILTED if preflight else MAIN_TILTED
    started = time.perf_counter()
    rows = [run_condition(b, r, shots, ds, ts)
            for (b, r), ds, ts in zip(CONDITIONS, direct_seeds, tilted_seeds, strict=True)]
    elapsed = time.perf_counter()-started
    gain_count = sum(row["importance_relative_se"] <= 0.75*row["direct_relative_se"]
                     for row in rows)
    output = {
        "status": "preflight" if preflight else "exact_categorical_circuit_development_screen",
        "stim_version": stim.__version__, "pymatching_version": pymatching.__version__,
        "tilt_factor": ALPHA, "channel_instrumentation_validation": validation,
        "shots_per_arm_per_condition": shots, "conditions": rows,
        "conditions_with_at_least_25pct_relative_se_gain": int(gain_count),
        "elapsed_seconds": elapsed,
        "stochastic_circuit_shots": shots*len(rows)*2,
        "scope": "samples exact categorical Phase 2B circuit channels; decoder uses the same prebuilt approximate DEM as fixed baseline",
    }
    target = HERE / ("categorical_importance_preflight.json" if preflight
                     else "categorical_importance_results.json")
    target.write_text(json.dumps(output, indent=2)+"\n", encoding="utf-8")
    print(f"Wrote {target}; elapsed={elapsed:.3f}s; variance-gain conditions={gain_count}/6")
    for row in rows:
        print(row["memory_basis"], row["regime"],
              f"direct={row['direct_ler']:.6g}",
              f"weighted={row['importance_weighted_ler']:.6g}",
              f"relSE={row['direct_relative_se']:.4g}->{row['importance_relative_se']:.4g}",
              f"ESS={row['failure_weight_effective_sample_size']:.1f}")
    if preflight and elapsed > 300:
        print("Instrumented-channel preflight exceeded five minutes; stop before full run")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
