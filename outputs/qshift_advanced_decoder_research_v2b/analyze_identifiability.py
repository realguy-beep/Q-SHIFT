"""Deterministic Q-SHIFT detector-feature identifiability audit.

This script does not call a Stim sampler, decoder, trainer, or seed source.
It obtains a single-fault detector mask by replacing every stochastic circuit
location except one categorical outcome with identity, making that outcome
probability one, and converting the resulting Clifford circuit to a DEM. The
full physical model is then evaluated by exact independent-location parity
algebra. A second, direct parity-state convolution independently checks the
45 expected features. A separately parsed ordinary Stim DEM is analyzed as
its own approximate independent-error distribution.

Run from repository root:
    python outputs/qshift_advanced_decoder_research_v2b/analyze_identifiability.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import stim

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from outputs.phase2b_pauli_bias.noise_model import PAULI_PAIRS
from outputs.phase3a_correlated_noise_preflight.simulator import build_spatial_burst_circuit
from outputs.stage4_noise_adaptive_feasibility_v1.prototype import BURST_DETECTOR_PAIRS


OUT = Path(__file__).resolve().parent / "analysis_results.json"
P_GRID = (0.0, 0.002, 0.004, 0.006, 0.008, 0.010, 0.012, 0.014, 0.016, 0.018, 0.020)
PROFILE_KNOTS = (0.0, 0.005, 0.010, 0.015, 0.020)
DETECTORS = 40
FEATURES: tuple[tuple[int, ...], ...] = tuple((i,) for i in range(DETECTORS)) + tuple(BURST_DETECTOR_PAIRS)
NOISE_NAMES = {
    "PAULI_CHANNEL_1", "PAULI_CHANNEL_2", "X_ERROR", "Y_ERROR", "Z_ERROR",
    "E", "ELSE_CORRELATED_ERROR", "DEPOLARIZE1", "DEPOLARIZE2",
    "I_ERROR", "HERALDED_ERASE", "HERALDED_PAULI_CHANNEL_1",
}


def toggle_mask(mask: int, detector: int) -> int:
    return mask ^ (1 << detector)


def mask_from_dem_error_line(line: str) -> int:
    mask = 0
    for d in re.findall(r"\bD(\d+)\b", line):
        mask = toggle_mask(mask, int(d))
    return mask


def only_fault_circuit(circuit: stim.Circuit, selected_index: int,
                       target_group: int, outcome_index: int) -> stim.Circuit:
    """Keep ideal circuit instructions and exactly one p=1 fault alternative."""
    out = stim.Circuit()
    for ix, ins in enumerate(circuit.flattened()):
        if ins.name not in NOISE_NAMES:
            out.append(ins)
            continue
        if ix != selected_index:
            if ins.name == "ELSE_CORRELATED_ERROR":
                raise ValueError("ELSE_CORRELATED_ERROR is not handled by the current model audit")
            continue
        targets = ins.targets_copy()
        if ins.name == "PAULI_CHANNEL_1":
            one_target = [targets[target_group]]
            args = [1.0 if j == outcome_index else 0.0 for j in range(3)]
            out.append(ins.name, one_target, args)
        elif ins.name == "PAULI_CHANNEL_2":
            pair_targets = targets[2 * target_group:2 * target_group + 2]
            args = [1.0 if j == outcome_index else 0.0 for j in range(15)]
            out.append(ins.name, pair_targets, args)
        elif ins.name in {"X_ERROR", "Y_ERROR", "Z_ERROR"}:
            out.append(ins.name, [targets[target_group]], [1.0])
        elif ins.name == "E":
            out.append(ins.name, targets, [1.0])
        else:
            raise ValueError(f"Unhandled stochastic instruction in source circuit: {ins.name}")
    return out


def exact_fault_mask(circuit: stim.Circuit, selected_index: int,
                     target_group: int, outcome_index: int) -> int:
    """Extract one deterministic fault's syndrome via a single-event DEM.

    approximate_disjoint_errors=True is required syntactically by Stim when a
    PAULI_CHANNEL_2 instruction is present. Only one categorical outcome is
    nonzero in this circuit and every other noise instruction is removed, so
    there are no disjoint alternatives for this call to approximate.
    """
    fault = only_fault_circuit(circuit, selected_index, target_group, outcome_index)
    dem = fault.detector_error_model(decompose_errors=False, approximate_disjoint_errors=True)
    terms = [line for line in str(dem.flattened()).splitlines() if line.startswith("error(")]
    if not terms:
        return 0
    if len(terms) != 1 or not re.match(r"error\(1(?:\.0*)?\)", terms[0]):
        raise ValueError(f"Expected one deterministic p=1 DEM term, got {terms[:4]}")
    return mask_from_dem_error_line(terms[0])


def physical_location_specs(circuit: stim.Circuit, masks: dict[tuple[int, int, int], int]) -> list[dict]:
    """Represent each circuit noise location as categorical alternatives."""
    specs: list[dict] = []
    for ix, ins in enumerate(circuit.flattened()):
        name = ins.name
        targets = ins.targets_copy()
        args = [float(x) for x in ins.gate_args_copy()]
        if name == "PAULI_CHANNEL_1":
            total = sum(args)
            if total > 1 + 1e-12:
                raise ValueError("PAULI_CHANNEL_1 alternatives sum above one")
            for g, target in enumerate(targets):
                if not target.is_qubit_target:
                    raise ValueError(f"Unexpected P1 target {target}")
                alts = [(args[a], masks[(ix, g, a)]) for a in range(3) if args[a] > 0]
                specs.append({"kind": "categorical_1q", "identity": max(0.0, 1-total), "alts": alts,
                              "source": f"instruction {ix} qubit {target.value}"})
        elif name == "PAULI_CHANNEL_2":
            total = sum(args)
            if total > 1 + 1e-12:
                raise ValueError("PAULI_CHANNEL_2 alternatives sum above one")
            for g in range(len(targets) // 2):
                pair = targets[2*g:2*g+2]
                if not all(t.is_qubit_target for t in pair):
                    raise ValueError(f"Unexpected P2 targets {pair}")
                alts = [(args[a], masks[(ix, g, a)]) for a in range(15) if args[a] > 0]
                specs.append({"kind": "categorical_2q", "identity": max(0.0, 1-total), "alts": alts,
                              "source": f"instruction {ix} pair {pair[0].value},{pair[1].value}"})
        elif name in {"X_ERROR", "Y_ERROR", "Z_ERROR"}:
            p = args[0]
            for g, target in enumerate(targets):
                specs.append({"kind": "bernoulli_measurement", "identity": 1-p,
                              "alts": [(p, masks[(ix, g, 0)])] if p else [],
                              "source": f"instruction {ix} {name} target {target.value}"})
        elif name == "E":
            p = args[0]
            specs.append({"kind": "bernoulli_burst", "identity": 1-p,
                          "alts": [(p, masks[(ix, 0, 0)])] if p else [],
                          "source": f"instruction {ix} E targets {targets}"})
        elif ("ERROR" in name or "PAULI_CHANNEL" in name or "DEPOLARIZE" in name
              or "HERALDED" in name) and name not in NOISE_NAMES:
            raise ValueError(f"Unrecognized stochastic instruction {name}")
        elif name == "ELSE_CORRELATED_ERROR":
            raise ValueError("Current source circuit unexpectedly contains ELSE_CORRELATED_ERROR")
    return specs


def extract_physical_signatures(circuit: stim.Circuit) -> tuple[list[dict], dict]:
    masks: dict[tuple[int, int, int], int] = {}
    counts: Counter[str] = Counter()
    burst_rows = []
    for ix, ins in enumerate(circuit.flattened()):
        if ins.name == "PAULI_CHANNEL_1":
            for g, _ in enumerate(ins.targets_copy()):
                for alt in range(3):
                    masks[(ix, g, alt)] = exact_fault_mask(circuit, ix, g, alt)
                    counts["1q_alternatives"] += 1
        elif ins.name == "PAULI_CHANNEL_2":
            for g in range(len(ins.targets_copy()) // 2):
                for alt in range(15):
                    masks[(ix, g, alt)] = exact_fault_mask(circuit, ix, g, alt)
                    counts["2q_alternatives"] += 1
        elif ins.name in {"X_ERROR", "Y_ERROR", "Z_ERROR"}:
            for g, _ in enumerate(ins.targets_copy()):
                masks[(ix, g, 0)] = exact_fault_mask(circuit, ix, g, 0)
                counts["measurement_alternatives"] += 1
        elif ins.name == "E":
            mask = exact_fault_mask(circuit, ix, 0, 0)
            masks[(ix, 0, 0)] = mask
            counts["burst_alternatives"] += 1
            burst_rows.append({"instruction_index": ix, "detector_indices": [i for i in range(DETECTORS) if mask >> i & 1]})
    return physical_location_specs(circuit, masks), {"alternative_counts": dict(counts), "burst_masks": burst_rows}


def physical_specs_at(specs: list[dict], pb: float, pm: float) -> list[dict]:
    out = []
    for spec in specs:
        q = dict(spec)
        if spec["kind"] == "bernoulli_burst":
            p = pb
            q["identity"] = 1-p
            q["alts"] = [(p, spec["alts"][0][1])] if p else []
        elif spec["kind"] == "bernoulli_measurement":
            p = pm
            q["identity"] = 1-p
            q["alts"] = [(p, spec["alts"][0][1])] if p else []
        out.append(q)
    return out


def parity_expectation(specs: list[dict], subset_mask: int) -> float:
    value = 1.0
    for spec in specs:
        factor = spec["identity"]
        for probability, mask in spec["alts"]:
            factor += probability * (-1.0 if (mask & subset_mask).bit_count() % 2 else 1.0)
        value *= factor
    return value


def feature_mean_from_characters(specs: list[dict]) -> np.ndarray:
    means = []
    for inds in FEATURES:
        chis = [parity_expectation(specs, 1 << i) for i in inds]
        if len(inds) == 1:
            means.append((1-chis[0])/2)
        else:
            both = parity_expectation(specs, (1 << inds[0]) | (1 << inds[1]))
            means.append((1-chis[0]-chis[1]+both)/4)
    return np.asarray(means, dtype=float)


def subset_distribution(specs: list[dict], detector_indices: tuple[int, ...]) -> np.ndarray:
    """Independent reference: convolve categorical parity states directly."""
    k = len(detector_indices)
    state_count = 1 << k
    dist = np.zeros(state_count, dtype=float)
    dist[0] = 1.0
    for spec in specs:
        local = np.zeros(state_count, dtype=float)
        local[0] += spec["identity"]
        for p, mask in spec["alts"]:
            state = 0
            for bit, detector in enumerate(detector_indices):
                if mask >> detector & 1:
                    state ^= 1 << bit
            local[state] += p
        nxt = np.zeros_like(dist)
        for old in range(state_count):
            for new in range(state_count):
                nxt[old ^ new] += dist[old] * local[new]
        dist = nxt
    return dist


def feature_mean_from_convolution(specs: list[dict]) -> np.ndarray:
    means = []
    for inds in FEATURES:
        dist = subset_distribution(specs, tuple(inds))
        if len(inds) == 1:
            means.append(dist[1])
        else:
            means.append(dist[3])
    return np.asarray(means, dtype=float)


def dem_specs(circuit: stim.Circuit) -> list[dict]:
    """Parse the approximate Stim DEM as independent DEM error mechanisms."""
    dem = circuit.detector_error_model(decompose_errors=True, approximate_disjoint_errors=True)
    specs = []
    for line in str(dem.flattened()).splitlines():
        match = re.match(r"error\(([^)]+)\)(.*)$", line.strip())
        if not match:
            continue
        p = float(match.group(1))
        mask = mask_from_dem_error_line(match.group(2))
        specs.append({"kind": "independent_dem_error", "identity": 1-p, "alts": [(p, mask)] if p else [],
                      "source": line.strip()})
    return specs


def feature_moments(specs: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    """Exact first and second moments for the listed binary detector features."""
    mu = feature_mean_from_characters(specs)
    second = np.empty((len(FEATURES), len(FEATURES)), dtype=float)
    for a, fa in enumerate(FEATURES):
        for b, fb in enumerate(FEATURES):
            union = tuple(sorted(set(fa) | set(fb)))
            moment = 0.0
            for sub in range(1 << len(union)):
                mask = 0
                parity = 0
                for j, detector in enumerate(union):
                    if sub >> j & 1:
                        mask |= 1 << detector
                        parity += 1
                moment += (-1.0 if parity % 2 else 1.0) * parity_expectation(specs, mask)
            second[a, b] = moment / (1 << len(union))
    cov = second - np.outer(mu, mu)
    return mu, (cov + cov.T) / 2


def jacobian(fun, pb: float, pm: float, h: float = 1e-6) -> np.ndarray:
    columns = []
    for j, value in enumerate((pb, pm)):
        lo, hi = (pb, pm), (pb, pm)
        if value <= h:
            hi = list(hi); hi[j] += h
            columns.append((fun(*hi)-fun(pb, pm))/h)
        elif value >= 0.020-h and j == 0:
            lo = list(lo); lo[j] -= h
            columns.append((fun(pb, pm)-fun(*lo))/h)
        elif value >= 0.010-h and j == 1:
            lo = list(lo); lo[j] -= h
            columns.append((fun(pb, pm)-fun(*lo))/h)
        else:
            lo = list(lo); hi = list(hi)
            lo[j] -= h; hi[j] += h
            columns.append((fun(*hi)-fun(*lo))/(2*h))
    return np.column_stack(columns)


def conditioning(spec_provider, pb: float, pm: float) -> dict:
    specs = spec_provider(pb, pm)
    mean, cov = feature_moments(specs)
    J = jacobian(lambda x, y: feature_mean_from_characters(spec_provider(x, y)), pb, pm)
    raw_s = np.linalg.svd(J, compute_uv=False)
    colnorm = np.linalg.norm(J, axis=0)
    cosine = float(np.dot(J[:, 0], J[:, 1])/(colnorm[0]*colnorm[1])) if min(colnorm) else 1.0
    eig, vec = np.linalg.eigh(cov)
    keep = eig > max(float(eig.max()), 1e-30)*1e-10
    whitening = (vec[:, keep] / np.sqrt(eig[keep])) @ vec[:, keep].T
    whitened_s = np.linalg.svd(whitening @ J, compute_uv=False)
    return {
        "pb": pb, "pm": pm,
        "raw_jacobian_singular_values": raw_s.tolist(),
        "raw_condition_number": float(raw_s[0]/raw_s[-1]) if raw_s[-1] else None,
        "raw_jacobian_rank_tol_1e-10": int(np.count_nonzero(raw_s > raw_s[0]*1e-10)),
        "column_cosine_burst_measurement": cosine,
        "column_norms": colnorm.tolist(),
        "noise_whitened_singular_values_per_shot": whitened_s.tolist(),
        "noise_whitened_condition_number": float(whitened_s[0]/whitened_s[-1]) if whitened_s[-1] else None,
        "feature_covariance_rank_tol_1e-10": int(np.count_nonzero(keep)),
        "jacobian": J.tolist(), "means": mean.tolist(),
    }


def estimator_scales(profile_means: list[np.ndarray]) -> np.ndarray:
    stack = np.stack(profile_means)
    pooled_mean = stack.mean(axis=0)
    within = np.mean(stack*(1-stack), axis=0)
    between = np.mean((stack-pooled_mean)**2, axis=0)
    return np.sqrt(np.maximum(within+between, 1e-6))


def profile_projection(spec_provider, pb: float, pm: float) -> dict:
    template_means = [feature_mean_from_characters(spec_provider(p, 0.003)) for p in PROFILE_KNOTS]
    scales = estimator_scales(template_means)
    grid = np.arange(0.0, 0.0200001, 0.00001)
    templ = np.stack(template_means)
    exp = np.column_stack([np.interp(grid, PROFILE_KNOTS, templ[:, j]) for j in range(len(FEATURES))])
    target = feature_mean_from_characters(spec_provider(pb, pm))
    scores = np.mean(((exp-target)/scales)**2, axis=1)
    idx = int(np.argmin(scores))
    return {"true_pb": pb, "actual_pm": pm, "assumed_pm": 0.003,
            "estimated_pb": float(grid[idx]), "bias": float(grid[idx]-pb),
            "minimum_profile_score": float(scores[idx]), "runner_up_gap": float(np.partition(scores, 1)[1]-scores[idx])}


def distance_scan(spec_provider) -> dict:
    points = [(p, m) for p in P_GRID for m in (0.0, 0.003, 0.006, 0.010)]
    profiles = [feature_mean_from_characters(spec_provider(p, m)) for p, m in points]
    refs = [feature_mean_from_characters(spec_provider(p, 0.003)) for p in PROFILE_KNOTS]
    scales = estimator_scales(refs)
    pairs = []
    cross_pairs = []
    same_burst_pairs = []
    same_measurement_pairs = []
    exact_collisions = 0
    for i in range(len(points)):
        for j in range(i+1, len(points)):
            raw = float(np.max(np.abs(profiles[i]-profiles[j])))
            if raw <= 1e-12:
                exact_collisions += 1
            scaled = float(np.sqrt(np.mean(((profiles[i]-profiles[j])/scales)**2)))
            row = (scaled, raw, points[i], points[j])
            pairs.append(row)
            if points[i][0] != points[j][0] and points[i][1] != points[j][1]:
                cross_pairs.append(row)
            elif points[i][0] == points[j][0]:
                same_burst_pairs.append(row)
            else:
                same_measurement_pairs.append(row)
    pairs.sort(key=lambda q:q[0])
    cross_pairs.sort(key=lambda q:q[0])
    same_burst_pairs.sort(key=lambda q:q[0])
    same_measurement_pairs.sort(key=lambda q:q[0])
    render = lambda q: {"distance": q[0], "max_abs_feature_gap": q[1], "point1": list(q[2]), "point2": list(q[3])}
    return {"grid_points": len(points), "exact_mean_profile_collision_pairs_tol_1e-12": exact_collisions,
            "nearest_standardized_pairs": [render(q) for q in pairs[:10]],
            "nearest_cross_parameter_pairs": [render(q) for q in cross_pairs[:5]],
            "nearest_burst_only_pairs": [render(q) for q in same_measurement_pairs[:5]],
            "nearest_measurement_only_pairs": [render(q) for q in same_burst_pairs[:5]]}


def feature_snapshot(provider, pb: float, pm: float) -> dict:
    mu = feature_mean_from_characters(provider(pb, pm))
    return {"pb": pb, "pm": pm,
            "burst_pair_cofires": {f"D{i}&D{j}": float(mu[40+k])
                                   for k,(i,j) in enumerate(BURST_DETECTOR_PAIRS)},
            "burst_site_detector_rates": {f"D{i}": float(mu[i]) for i in (8,10,16,18,24,26,32,34,36,38)},
            "last_round_detector_rates": {f"D{i}": float(mu[i]) for i in (36,37,38,39)}}


def feature_sensitivity(spec_provider, pb: float, pm: float) -> dict:
    J = jacobian(lambda x, y: feature_mean_from_characters(spec_provider(x, y)), pb, pm)
    names = [f"D{i}" for i in range(DETECTORS)] + [f"D{i}&D{j}" for i,j in BURST_DETECTOR_PAIRS]
    rows = [{"feature": names[i], "d_mean_d_burst": float(J[i,0]), "d_mean_d_measurement": float(J[i,1])}
            for i in range(len(names))]
    return {"top_abs_burst_sensitivity": sorted(rows, key=lambda r: -abs(r["d_mean_d_burst"]))[:10],
            "top_abs_measurement_sensitivity": sorted(rows, key=lambda r: -abs(r["d_mean_d_measurement"]))[:10],
            "all_features": rows}


def main() -> None:
    # Nonzero reference burst makes the five insertion instructions present.
    ref = build_spatial_burst_circuit(gate_p=0.003, measurement_p=0.003, burst_probability=0.008)
    locations, mapping = extract_physical_signatures(ref)

    def physical_provider(pb: float, pm: float) -> list[dict]:
        return physical_specs_at(locations, pb, pm)

    validation = []
    for pb, pm in ((0.008, 0.003), (0.008, 0.006), (0.0, 0.003), (0.020, 0.003)):
        specs = physical_provider(pb, pm)
        a = feature_mean_from_characters(specs)
        b = feature_mean_from_convolution(specs)
        validation.append({"pb": pb, "pm": pm, "max_abs_char_vs_convolution": float(np.max(np.abs(a-b))),
                           "allclose_1e-12": bool(np.allclose(a,b,rtol=0,atol=1e-12))})

    nominal_j = conditioning(physical_provider, 0.008, 0.003)
    mismatch_j = conditioning(physical_provider, 0.008, 0.006)
    boundary = {"pb_zero_pm003": conditioning(physical_provider, 0.0, 0.003),
                "pb_max_pm003": conditioning(physical_provider, 0.020, 0.003),
                "pm_zero_pb008": conditioning(physical_provider, 0.008, 0.0),
                "pm_max_pb008": conditioning(physical_provider, 0.008, 0.010)}

    profile_bias = [profile_projection(physical_provider, pb, pm)
                    for pb, pm in ((0.0,0.003),(0.004,0.003),(0.008,0.003),(0.012,0.003),
                                   (0.016,0.003),(0.020,0.003),(0.008,0.006))]
    distances = distance_scan(physical_provider)

    # Compare with the exact independent-error distribution represented by the
    # repository's approximate DEM conversion. This is a different model.
    dem_results = {}
    for pb, pm in ((0.008,0.003),(0.008,0.006),(0.0,0.003),(0.020,0.003)):
        c = build_spatial_burst_circuit(gate_p=0.003, measurement_p=pm, burst_probability=pb)
        ds = dem_specs(c)
        em = feature_mean_from_characters(ds)
        pmphys = feature_mean_from_characters(physical_provider(pb, pm))
        dem_results[f"pb={pb:.3f},pm={pm:.3f}"] = {
            "dem_independent_error_terms": len(ds),
            "max_abs_feature_mean_dem_minus_exact_circuit": float(np.max(np.abs(em-pmphys))),
            "rms_feature_mean_dem_minus_exact_circuit": float(np.sqrt(np.mean((em-pmphys)**2))),
            "pair_feature_differences": (em[40:]-pmphys[40:]).tolist(),
        }
    dem_nominal_provider = lambda pb, pm: dem_specs(build_spatial_burst_circuit(
        gate_p=0.003, measurement_p=pm, burst_probability=pb))
    dem_bias = profile_projection(dem_nominal_provider, 0.008, 0.006)
    dem_identifiability = {
        "nominal_pb008_pm003": conditioning(dem_nominal_provider, 0.008, 0.003),
        "mismatch_pb008_pm006": conditioning(dem_nominal_provider, 0.008, 0.006),
        "boundaries": {
            "pb_zero_pm003": conditioning(dem_nominal_provider, 0.0, 0.003),
            "pb_max_pm003": conditioning(dem_nominal_provider, 0.020, 0.003),
            "pm_zero_pb008": conditioning(dem_nominal_provider, 0.008, 0.0),
            "pm_max_pb008": conditioning(dem_nominal_provider, 0.008, 0.010),
        },
    }

    result = {
        "provenance": {"stim_version": stim.__version__, "circuit": "distance-3 rotated Z-memory, 5 rounds, balanced bias ratio 10, gate_p=.003",
                       "physical_expectations": "exact under independent categorical fault-location model, using deterministic p=1 single-fault detector signatures; no sampling",
                       "dem_expectations": "exact only for the independent-error distribution emitted by Stim with decompose_errors=True, approximate_disjoint_errors=True",
                       "profile_knots": list(PROFILE_KNOTS), "jacobian_step": 1e-6},
        "circuit_shape": {"detectors": ref.num_detectors, "observables": ref.num_observables,
                          "flattened_instructions": len(list(ref.flattened()))},
        "fault_mapping": mapping,
        "physical_independent_locations": len(locations),
        "formula_validation": validation,
        "physical_local_identifiability": {"nominal_pb008_pm003": nominal_j,
                                            "mismatch_pb008_pm006": mismatch_j,
                                            "boundaries": boundary},
        "physical_feature_sensitivity_nominal": feature_sensitivity(physical_provider, 0.008, 0.003),
        "physical_feature_snapshots": [feature_snapshot(physical_provider, pb, pm)
                                        for pb,pm in ((0.0,0.003),(0.008,0.003),(0.008,0.006))],
        "exact_feature_profile_distance_scan": distances,
        "detector_only_estimator_projection_exact_circuit": profile_bias,
        "approximate_dem_comparison": dem_results,
        "approximate_dem_local_identifiability": dem_identifiability,
        "approximate_dem_feature_snapshots": [feature_snapshot(dem_nominal_provider, pb, pm)
                                               for pb,pm in ((0.0,0.003),(0.008,0.003),(0.008,0.006))],
        "detector_only_estimator_projection_approximate_dem": dem_bias,
    }
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"out": str(OUT), "physical_locations": len(locations),
                      "mapping": mapping, "validation": validation,
                      "nominal_singular_values": nominal_j["raw_jacobian_singular_values"],
                      "nominal_condition": nominal_j["raw_condition_number"],
                      "nominal_column_cosine": nominal_j["column_cosine_burst_measurement"],
                      "mismatch_bias_exact": profile_bias[-1],
                      "dem_mismatch_bias": dem_bias,
                      "dem_comparison": dem_results}, indent=2))


if __name__ == "__main__":
    main()
