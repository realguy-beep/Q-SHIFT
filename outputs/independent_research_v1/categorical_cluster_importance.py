"""Development-only pair-cluster categorical importance sampler."""
from __future__ import annotations

import json
import math
import resource
import sys
import time
from pathlib import Path

import numpy as np
import pymatching
import stim

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "outputs/phase2b_pauli_bias"))
sys.path.insert(0, str(HERE))
from categorical_importance_sampler import decode_failures, tilted_channel
from noise_model import MEMORY_BASES, PAULI_PAIRS, REGIMES, build_circuit  # noqa: E402

ALPHA = 5.0
SHRINKAGE = 50.0
TRAIN_SHOTS = 100_000
VALIDATION_SHOTS = 20_000
PREFLIGHT_SHOTS = 100
CONDITIONS = tuple((b, r) for b in MEMORY_BASES for r in REGIMES)
TRAIN_SEEDS = tuple(range(202611701, 202611707))
DIRECT_SEEDS = tuple(range(202611711, 202611717))
GLOBAL_SEEDS = tuple(range(202611721, 202611727))
CLUSTER_SEEDS = tuple(range(202611731, 202611737))
PREFLIGHT_SEEDS = tuple(range(202611741, 202611765))
PAULI = {"X": stim.target_x, "Y": stim.target_y, "Z": stim.target_z}


def group_channels(circuit: stim.Circuit):
    """Return fixed adjacent channel-pair clusters and exact source probabilities."""
    events, groups = [], []
    for instruction_index, inst in enumerate(circuit.flattened()):
        if inst.name != "PAULI_CHANNEL_2":
            continue
        ps = np.asarray(inst.gate_args_copy(), dtype=np.float64)
        if len(ps) != 15:
            raise RuntimeError("expected 15 nonidentity Pauli-pair probabilities")
        local = np.asarray([1.0 - ps.sum(), *ps.tolist()], dtype=np.float64)
        targets = [int(t.value) for t in inst.targets_copy()]
        if len(targets) % 4:
            raise RuntimeError("adjacent two-location grouping requires an even pair count")
        event_start = len(events)
        for offset in range(0, len(targets), 2):
            events.append({"instruction": instruction_index,
                           "qubits": [targets[offset], targets[offset+1]],
                           "p": local.tolist()})
        for j in range(event_start, len(events), 2):
            if j + 1 >= len(events):
                raise RuntimeError("unexpected singleton channel cluster")
            p = np.outer(local, local).reshape(-1)
            groups.append({"events": [j, j+1],
                           "instruction": instruction_index,
                           "qubits": events[j]["qubits"] + events[j+1]["qubits"],
                           "p": p.tolist()})
    return events, groups


def instrument_clusters(circuit: stim.Circuit, groups, proposals):
    source = circuit.flattened()
    by_instruction = {}
    for gi, group in enumerate(groups):
        by_instruction.setdefault(group["instruction"], []).append((gi, group))
    out = stim.Circuit()
    flags, group_order = [], []
    next_flag = circuit.num_qubits
    for instruction_index, inst in enumerate(source):
        if inst.name != "PAULI_CHANNEL_2":
            out.append(inst.name, inst.targets_copy(), inst.gate_args_copy())
            continue
        clusters = by_instruction[instruction_index]
        targets = [int(t.value) for t in inst.targets_copy()]
        if len(clusters) * 4 != len(targets):
            raise RuntimeError("cluster partition does not match channel targets")
        for gi, group in clusters:
            q = np.asarray(proposals[gi], dtype=np.float64)
            if q.shape != (256,) or np.any(q <= 0) or not np.isclose(q.sum(), 1, atol=1e-10):
                raise ValueError(f"invalid 256-category proposal at cluster {gi}")
            qs = tuple(range(next_flag, next_flag+9))
            next_flag += 9
            qubits = group["qubits"]
            remaining = 1.0
            # Identity/identity is the no-branch residual; categories 1..255
            # are explicit mutually exclusive arms.
            for code in range(1, 256):
                probability = q[code]
                conditional = float(probability / remaining)
                outcome_code = code  # zero flags uniquely denotes identity/identity.
                error_targets = []
                left, right = divmod(code, 16)
                for local_code, pair_qubits in ((left, qubits[:2]), (right, qubits[2:])):
                    if local_code:
                        pauli_pair = PAULI_PAIRS[local_code-1]
                        for symbol, qubit in zip(pauli_pair, pair_qubits, strict=True):
                            if symbol != "I":
                                error_targets.append(PAULI[symbol](qubit))
                for bit, flag in enumerate(qs):
                    if (outcome_code >> bit) & 1:
                        error_targets.append(stim.target_x(flag))
                out.append("E" if code == 1 else "ELSE_CORRELATED_ERROR",
                           error_targets, [conditional])
                remaining -= float(probability)
            flags.extend(qs)
            group_order.append(gi)
    if len(group_order) != len(groups):
        raise RuntimeError("not all cluster proposals were instrumented")
    out.append("M", flags)
    n = len(flags)
    for i in range(n):
        out.append("OBSERVABLE_INCLUDE", [stim.target_rec(-n+i)],
                   [circuit.num_observables+i])
    if out.num_detectors != circuit.num_detectors:
        raise RuntimeError("cluster instrumentation changed detector count")
    if out.num_observables != circuit.num_observables + n:
        raise RuntimeError("cluster instrumentation changed observable layout")
    return out


def decode_samples(matching, sampled, observable_count, group_count):
    detectors, outputs = sampled
    logical = outputs[:, :observable_count]
    flag_bits = outputs[:, observable_count:].reshape(len(detectors), group_count, 9)
    flag_codes = (flag_bits.astype(np.uint16) @ (1 << np.arange(9, dtype=np.uint16))).astype(np.int32)
    if np.any(flag_codes > 255):
        raise RuntimeError("invalid cluster flag code")
    categories = flag_codes
    failures = decode_failures(matching, detectors, logical)
    return categories, failures


def sample_arm(circuit, groups, source_groups, proposals, matching, shots, seed):
    started = time.perf_counter()
    instrument_start = time.perf_counter()
    inst = instrument_clusters(circuit, groups, proposals)
    instrument_seconds = time.perf_counter()-instrument_start
    compile_start = time.perf_counter()
    sampler = inst.compile_detector_sampler(seed=seed)
    compile_seconds = time.perf_counter()-compile_start
    sample_start = time.perf_counter()
    sampled = sampler.sample(shots=shots, separate_observables=True)
    sample_seconds = time.perf_counter()-sample_start
    decode_start = time.perf_counter()
    categories, failures = decode_samples(matching, sampled, circuit.num_observables, len(groups))
    decode_seconds = time.perf_counter()-decode_start
    log_ratio = np.zeros(shots, dtype=np.float64)
    for j, group in enumerate(groups):
        p = np.asarray(group["p"], dtype=np.float64)
        q = np.asarray(proposals[j], dtype=np.float64)
        log_ratio += np.log(p[categories[:, j]])-np.log(q[categories[:, j]])
    if not np.all(np.isfinite(log_ratio)):
        raise RuntimeError("nonfinite categorical cluster likelihood ratio")
    weights = np.exp(log_ratio)
    if not np.all(np.isfinite(weights)):
        raise RuntimeError("cluster likelihood ratio overflow")
    weighted_failures = weights*failures
    estimate = float(weighted_failures.mean())
    se = float(weighted_failures.std(ddof=1)/math.sqrt(shots)) if shots > 1 else float("inf")
    wf = weights[failures]
    ess = float(wf.sum()**2/np.square(wf).sum()) if len(wf) and np.square(wf).sum() else 0.0
    return {"shots": shots, "seed": seed, "unweighted_failures": int(failures.sum()),
            "ler_estimate": estimate, "standard_error": se,
            "relative_standard_error": se/estimate if estimate else float("inf"),
            "failure_weight_ess": ess, "max_abs_log_weight": float(np.max(np.abs(log_ratio))),
            "max_weight": float(weights.max()), "compile_seconds": compile_seconds,
            "sample_seconds": sample_seconds, "decode_seconds": decode_seconds,
            "instrument_seconds": instrument_seconds,
            "elapsed_seconds": time.perf_counter()-started}


def train_proposal(circuit, events, groups, global_q, matching, seed):
    inst = instrument_clusters(circuit, groups, global_q)
    sampled = inst.compile_detector_sampler(seed=seed).sample(
        shots=TRAIN_SHOTS, separate_observables=True)
    categories, failures = decode_samples(matching, sampled, circuit.num_observables, len(groups))
    logw = np.zeros(TRAIN_SHOTS, dtype=np.float64)
    for j, group in enumerate(groups):
        p, q = np.asarray(group["p"]), np.asarray(global_q[j])
        logw += np.log(p[categories[:, j]])-np.log(q[categories[:, j]])
    weights = np.exp(logw)
    weighted_failure = weights*failures
    total = float(weighted_failure.sum())
    proposals, diagnostics = [], []
    for j, group in enumerate(groups):
        p = np.asarray(group["p"], dtype=np.float64)
        counts = np.bincount(categories[:, j], weights=weighted_failure, minlength=256)
        q = (counts+SHRINKAGE*p)/(total+SHRINKAGE)
        if not np.all(q > 0) or not np.isclose(q.sum(), 1, atol=1e-10):
            raise RuntimeError(f"bad cluster proposal at {j}")
        proposals.append(q.tolist())
        diagnostics.append({"minimum_q": float(q.min()), "maximum_q": float(q.max()),
                            "source_minimum": float(p.min()),
                            "weighted_failure_categories_observed": int(np.count_nonzero(counts))})
    fweights = weights[failures]
    return proposals, {"shots": TRAIN_SHOTS, "tilted_failures": int(failures.sum()),
                       "weighted_failure_mass": total,
                       "failure_weight_ess": float(fweights.sum()**2/np.square(fweights).sum())
                       if len(fweights) and np.square(fweights).sum() else 0.0,
                       "max_abs_log_weight": float(np.max(np.abs(logw))),
                       "clusters": diagnostics}


def validate_tiny_instrumentation():
    probabilities = [0.01]*15
    tiny = stim.Circuit("R 0 1 2 3\nPAULI_CHANNEL_2("+
                        ",".join(map(str, probabilities))+ ") 0 1 2 3\nM 0 1 2 3")
    _, tiny_groups = group_channels(tiny)
    if len(tiny_groups) != 1:
        raise RuntimeError("synthetic two-location cluster was not constructed")
    proposal = [np.full(256, 1/256, dtype=np.float64)]
    inst = instrument_clusters(tiny, tiny_groups, proposal)
    raw = inst.compile_sampler(seed=202611740).sample(shots=50_000)
    measured = raw[:, :4]
    flag_bits = raw[:, 4:13]
    flags = (flag_bits.astype(np.uint16) @ (1 << np.arange(9, dtype=np.uint16))).astype(np.int32)
    if np.any(flags > 255):
        raise RuntimeError("synthetic cluster flags do not decode")
    categories = flags
    if len(np.unique(categories)) != 256:
        raise RuntimeError("uniform synthetic proposal did not exercise all 256 categories")
    mismatches = 0
    for code in range(16):
        for other in range(16):
            category = code*16+other
            selected = categories == category
            left = ("II" if code == 0 else PAULI_PAIRS[code-1])
            right = ("II" if other == 0 else PAULI_PAIRS[other-1])
            expected = np.asarray([s in "XY" for s in left+right])
            mismatches += int(np.count_nonzero(np.any(measured[selected] != expected, axis=1)))
    if mismatches:
        raise RuntimeError(f"synthetic cluster flag/data mapping has {mismatches} mismatches")
    counts = np.bincount(categories, minlength=256)
    chi2 = float(np.sum((counts-50_000/256)**2/(50_000/256)))
    # 255 df: a deliberately generous deterministic sanity threshold.
    if chi2 > 400:
        raise RuntimeError(f"uniform 256-category branch frequencies failed sanity check: {chi2}")
    return {"synthetic_shots": 50_000, "categories_observed": 256,
            "flag_pauli_mismatches": mismatches, "uniform_category_chi_square": chi2,
            "extra_branch_instructions": 256}


def main():
    started = time.perf_counter()
    synthetic_validation = validate_tiny_instrumentation()
    results, preflights = [], []
    for i, (basis, regime) in enumerate(CONDITIONS):
        circuit = build_circuit(basis, regime)
        events, groups = group_channels(circuit)
        if len(events) != 120 or len(groups) != 60:
            raise RuntimeError(f"unexpected fixed cluster layout: {len(events)} events/{len(groups)} groups")
        matching_dem = circuit.detector_error_model(decompose_errors=True,
                                                     approximate_disjoint_errors=0.0018)
        matching = pymatching.Matching.from_detector_error_model(
            matching_dem, enable_correlations=True)
        source_q = [np.asarray(g["p"], dtype=np.float64) for g in groups]
        global_q = []
        for group in groups:
            local_p = np.asarray(events[group["events"][0]]["p"])
            tilted_nonidentity = np.asarray(tilted_channel(local_p[1:].tolist(), ALPHA))
            tilted = np.asarray([1.0-tilted_nonidentity.sum(), *tilted_nonidentity])
            global_q.append(np.outer(tilted, tilted).reshape(-1))
        if i == 0:
            instrument_count = sum(256 for _ in groups)
            if instrument_count > 20_000:
                raise RuntimeError("cluster instrument exceeds fixed instruction cap")
        # Preflight evaluates source/global/cluster instrument size and throughput.
        if i == 0:
            q_pre = source_q
        else:
            q_pre = source_q
        row_pf = {"condition": [basis, regime], "arms": {}}
        for j, (name, q, seed) in enumerate((
                ("direct", source_q, PREFLIGHT_SEEDS[4*i]),
                ("global_5x", global_q, PREFLIGHT_SEEDS[4*i+1]),
                ("cluster_source_placeholder", q_pre, PREFLIGHT_SEEDS[4*i+2]),
                ("direct_repeat_structure", source_q, PREFLIGHT_SEEDS[4*i+3]))):
            arm = sample_arm(circuit, groups, source_q, q, matching, PREFLIGHT_SHOTS, seed)
            row_pf["arms"][name] = arm
        preflights.append(row_pf)
        print("preflight", basis, regime, flush=True)

    preflight_seconds = time.perf_counter()-started
    projected_seconds = 0.0
    for row in preflights:
        arms = row["arms"]
        # Separate fixed compile/instrument costs from shot-linear sample/decode costs.
        direct, global_, cluster = (arms["direct"], arms["global_5x"],
                                    arms["cluster_source_placeholder"])
        projected_seconds += (
            direct["instrument_seconds"]+direct["compile_seconds"]
            + (direct["sample_seconds"]+direct["decode_seconds"])*VALIDATION_SHOTS/PREFLIGHT_SHOTS
            + 2*(global_["instrument_seconds"]+global_["compile_seconds"])
            + (global_["sample_seconds"]+global_["decode_seconds"])*(TRAIN_SHOTS+VALIDATION_SHOTS)/PREFLIGHT_SHOTS
            + cluster["instrument_seconds"]+cluster["compile_seconds"]
            + (cluster["sample_seconds"]+cluster["decode_seconds"])*VALIDATION_SHOTS/PREFLIGHT_SHOTS)
    pfout = {"status": "cluster_instrumentation_preflight", "preflight_seconds": preflight_seconds,
             "projected_main_seconds_linear": projected_seconds, "preflights": preflights,
             "synthetic_instrumentation_validation": synthetic_validation,
             "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
             "stochastic_samples_generated": len(CONDITIONS)*4*PREFLIGHT_SHOTS}
    (HERE/"categorical_cluster_importance_preflight.json").write_text(json.dumps(pfout, indent=2)+"\n")
    if projected_seconds > 300:
        pfout["status"] = "preflight_resource_stop"
        (HERE/"categorical_cluster_importance_preflight.json").write_text(json.dumps(pfout, indent=2)+"\n")
        print(json.dumps({"status": pfout["status"], "projected_seconds": projected_seconds}, indent=2))
        return

    for i, ((basis, regime), train_seed, direct_seed, global_seed, cluster_seed) in enumerate(zip(
            CONDITIONS, TRAIN_SEEDS, DIRECT_SEEDS, GLOBAL_SEEDS, CLUSTER_SEEDS, strict=True)):
        circuit = build_circuit(basis, regime)
        events, groups = group_channels(circuit)
        dem = circuit.detector_error_model(decompose_errors=True, approximate_disjoint_errors=0.0018)
        matching = pymatching.Matching.from_detector_error_model(dem, enable_correlations=True)
        source_q = [np.asarray(g["p"], dtype=np.float64) for g in groups]
        global_q = []
        for group in groups:
            local_p = np.asarray(events[group["events"][0]]["p"])
            tilted_nonidentity = np.asarray(tilted_channel(local_p[1:].tolist(), ALPHA))
            tilted = np.asarray([1.0-tilted_nonidentity.sum(), *tilted_nonidentity])
            global_q.append(np.outer(tilted, tilted).reshape(-1))
        q, training = train_proposal(circuit, events, groups, global_q, matching, train_seed)
        arms = [
            ("direct", source_q, direct_seed),
            ("global_5x", global_q, global_seed),
            ("pair_cluster", q, cluster_seed),
        ]
        measured = {name: sample_arm(circuit, groups, source_q, proposal, matching,
                                      VALIDATION_SHOTS, seed)
                    for name, proposal, seed in arms}
        candidate = measured["pair_cluster"]
        comparisons = {}
        for name in ("direct", "global_5x"):
            other = measured[name]
            delta = candidate["ler_estimate"]-other["ler_estimate"]
            combined = math.hypot(candidate["standard_error"], other["standard_error"])
            comparisons[name] = {"difference": delta, "combined_se": combined,
                                 "within_3se": abs(delta) <= 3*combined}
        advanced = (all(candidate["standard_error"] <= .75*measured[n]["standard_error"]
                        for n in ("direct", "global_5x"))
                    and all(v["within_3se"] for v in comparisons.values()))
        results.append({"memory_basis": basis, "regime": regime, "training": training,
                        "validation_arms": measured, "comparisons": comparisons,
                        "condition_advancement_gate_passed": bool(advanced)})
        print(basis, regime,
              {k: (round(v["ler_estimate"], 7), round(v["relative_standard_error"], 3))
               for k, v in measured.items()}, "gate", advanced, flush=True)
    passed = sum(x["condition_advancement_gate_passed"] for x in results)
    output = {"status": "pair_cluster_importance_development_validation",
              "proposal": "independent product across fixed adjacent two-channel clusters",
              "cluster_layout": "adjacent channel pairs within each flattened PAULI_CHANNEL_2 instruction",
              "training_shots_per_condition": TRAIN_SHOTS,
              "validation_shots_per_arm_per_condition": VALIDATION_SHOTS,
              "conditions": results, "conditions_passed_gate": passed,
              "all_conditions_passed": passed == 6,
              "elapsed_seconds": time.perf_counter()-started,
              "stochastic_circuit_shots": 6*(TRAIN_SHOTS+3*VALIDATION_SHOTS)+pfout["stochastic_samples_generated"],
              "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              "scope": "development-only weighted LER for fixed correlation-enabled matching; approximate DEM decoder, exact categorical circuit sampling",
              "seeds": {"training": TRAIN_SEEDS, "direct": DIRECT_SEEDS,
                        "global": GLOBAL_SEEDS, "cluster": CLUSTER_SEEDS}}
    (HERE/"categorical_cluster_importance_results.json").write_text(json.dumps(output, indent=2)+"\n")
    print(json.dumps({"status": output["status"], "passed": passed,
                      "elapsed_seconds": output["elapsed_seconds"]}, indent=2))


if __name__ == "__main__":
    main()
