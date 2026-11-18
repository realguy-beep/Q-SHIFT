"""Exact log-domain variable elimination for small native-categorical models."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, product
import json
import math
from pathlib import Path
import sys
import time

import numpy as np
from scipy.special import logsumexp

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "outputs/categorical_decoder_feasibility"))
from categorical_reference import (  # noqa: E402
    CategoricalLocation, CategoricalModel, FaultOutcome, exact_posterior,
)
from toy_circuits import one_qubit_model, two_qubit_model, stim_exhaustive_joint  # noqa: E402


@dataclass
class Factor:
    scope: tuple[int, ...]
    log_values: np.ndarray


@dataclass
class Stats:
    induced_width: int = 0
    max_factor_entries: int = 1
    elimination_order: tuple[int, ...] = ()


def _weighted_min_fill(scopes: list[tuple[int, ...]], domains: dict[int, int],
                       strategy: str = "weighted_min_fill") -> tuple[int, ...]:
    graph: dict[int, set[int]] = {v: set() for v in domains}
    for scope in scopes:
        for a, b in combinations(scope, 2):
            graph[a].add(b)
            graph[b].add(a)
    order = []
    while graph:
        def key(v: int) -> tuple[int, int, int, int]:
            ns = graph[v]
            missing = sum(1 for a, b in combinations(ns, 2) if b not in graph[a])
            entries = domains[v] * math.prod(domains[n] for n in ns)
            if strategy == "weighted_min_fill":
                return missing, entries, len(ns), v
            if strategy == "weighted_min_product":
                return entries, missing, len(ns), v
            if strategy == "min_fill":
                return missing, len(ns), entries, v
            if strategy == "min_degree":
                return len(ns), missing, entries, v
            raise ValueError(f"unknown ordering strategy {strategy}")

        v = min(graph, key=key)
        neighbors = list(graph[v])
        for a, b in combinations(neighbors, 2):
            graph[a].add(b)
            graph[b].add(a)
        for n in neighbors:
            graph[n].discard(v)
        del graph[v]
        order.append(v)
    return tuple(order)


def _model_scopes(model: CategoricalModel) -> tuple[dict[int, int], list[tuple[int, ...]]]:
    n = len(model.locations)
    domains = {i: len(loc.outcomes) for i, loc in enumerate(model.locations)}
    domains.update({n + i: 2 for i in range(n)})
    scopes = [(i,) for i in range(n)]
    for detector in range(model.detector_count):
        scope = tuple(i for i, loc in enumerate(model.locations)
                      if any((outcome.detector_mask >> detector) & 1 for outcome in loc.outcomes))
        if scope:
            scopes.append(scope)
    for i in range(n):
        carry = n + i
        previous = None if i == 0 else n + i - 1
        scopes.append(tuple(sorted((i, carry) if previous is None else (previous, i, carry))))
    scopes.append((2 * n - 1,))
    return domains, scopes


def estimate_factor_growth(model: CategoricalModel, strategy: str = "weighted_min_fill") -> dict:
    """Estimate min-fill factor sizes from scopes only; allocate no dense tables."""
    domains, scopes = _model_scopes(model)
    n = len(model.locations)
    if strategy == "natural":
        order = tuple(range(2 * n))
    elif strategy == "reverse_natural":
        order = tuple(reversed(range(2 * n)))
    elif strategy == "location_carry_interleaved":
        order = tuple(v for i in range(n) for v in (i, n + i))
    elif strategy == "carry_location_interleaved":
        order = tuple(v for i in range(n) for v in (n + i, i))
    else:
        order = _weighted_min_fill(scopes, domains, strategy)
    scopes = list(scopes)
    induced_width = 0
    max_entries = 1
    records = []
    for variable in order:
        bucket = [scope for scope in scopes if variable in scope]
        scopes = [scope for scope in scopes if variable not in scope]
        union = tuple(sorted({v for scope in bucket for v in scope}))
        entries = math.prod(domains[v] for v in union)
        width = len(union) - 1
        induced_width = max(induced_width, width)
        max_entries = max(max_entries, entries)
        records.append({"variable": variable, "induced_width_at_step": width,
                        "intermediate_factor_entries": entries})
        reduced = tuple(v for v in union if v != variable)
        if reduced:
            scopes.append(reduced)
    return {"strategy": strategy, "elimination_order": order, "induced_width": induced_width,
            "max_intermediate_factor_entries": max_entries, "steps": records}


def _multiply_bucket(bucket: list[Factor], domains: dict[int, int], stats: Stats) -> Factor:
    union = tuple(sorted({v for f in bucket for v in f.scope}))
    shape = tuple(domains[v] for v in union)
    entries = math.prod(shape)
    stats.max_factor_entries = max(stats.max_factor_entries, entries)
    pos = {v: i for i, v in enumerate(union)}
    total = np.zeros(shape, dtype=np.float64)
    for factor in bucket:
        reshape = [1] * len(union)
        axes = [pos[v] for v in factor.scope]
        for v, axis in zip(factor.scope, axes, strict=True):
            reshape[axis] = domains[v]
        total += factor.log_values.reshape(reshape)
    return Factor(union, total)


def _make_factors(model: CategoricalModel, syndrome: int, logical: int):
    n = len(model.locations)
    domains = {i: len(loc.outcomes) for i, loc in enumerate(model.locations)}
    domains.update({n + i: 2 for i in range(n)})
    factors: list[Factor] = []

    # Categorical location priors.
    for i, location in enumerate(model.locations):
        probs = np.asarray([o.probability for o in location.outcomes], dtype=np.float64)
        with np.errstate(divide="ignore"):
            factors.append(Factor((i,), np.log(probs)))

    # Detector XOR checks. Each factor touches exactly the locations that can
    # toggle that detector; identity outcomes remain in each location prior.
    for detector in range(model.detector_count):
        scope = tuple(i for i, loc in enumerate(model.locations)
                      if any((o.detector_mask >> detector) & 1 for o in loc.outcomes))
        target = (syndrome >> detector) & 1
        if not scope:
            if target:
                return domains, factors, -np.inf
            continue
        table = np.full(tuple(domains[v] for v in scope), -np.inf, dtype=np.float64)
        for states in product(*(range(domains[v]) for v in scope)):
            parity = 0
            for v, state in zip(scope, states, strict=True):
                parity ^= (model.locations[v].outcomes[state].detector_mask >> detector) & 1
            if parity == target:
                table[states] = 0.0
        factors.append(Factor(scope, table))

    # Prefix XOR chain over observable contributions; this avoids a global
    # parity factor that would make all participating locations a clique.
    for i, location in enumerate(model.locations):
        carry = n + i
        previous = None if i == 0 else n + i - 1
        scope = tuple(sorted((i, carry) if previous is None else (previous, i, carry)))
        table = np.full(tuple(domains[v] for v in scope), -np.inf, dtype=np.float64)
        for states in product(*(range(domains[v]) for v in scope)):
            state_by_variable = dict(zip(scope, states, strict=True))
            if i == 0:
                state = state_by_variable[i]
                prev_carry = 0
            else:
                prev_carry = state_by_variable[previous]
                state = state_by_variable[i]
            next_carry = state_by_variable[carry]
            outcome = location.outcomes[state]
            if (prev_carry ^ (outcome.observable_mask & 1)) == next_carry:
                table[states] = 0.0
        factors.append(Factor(scope, table))
    factors.append(Factor((n + n - 1,), np.asarray([0.0, -np.inf]) if logical == 0
                          else np.asarray([-np.inf, 0.0])))
    return domains, factors, None


def exact_joint_mass(model: CategoricalModel, syndrome: int, logical: int, *,
                     max_factor_entries: int = 1_000_000) -> tuple[float, Stats]:
    model.validate()
    domains, factors, impossible = _make_factors(model, syndrome, logical)
    stats = Stats()
    if impossible is not None:
        return 0.0, stats
    order = _weighted_min_fill([f.scope for f in factors], domains)
    stats.elimination_order = order
    for variable in order:
        bucket = [f for f in factors if variable in f.scope]
        factors = [f for f in factors if variable not in f.scope]
        if not bucket:
            continue
        union = {v for f in bucket for v in f.scope}
        predicted_entries = math.prod(domains[v] for v in union)
        if predicted_entries > max_factor_entries:
            raise RuntimeError(
                f"pre-multiplication factor cap exceeded: {predicted_entries} > {max_factor_entries}"
            )
        joined = _multiply_bucket(bucket, domains, stats)
        axis = joined.scope.index(variable)
        stats.induced_width = max(stats.induced_width, len(joined.scope) - 1)
        reduced = logsumexp(joined.log_values, axis=axis)
        scope = tuple(v for v in joined.scope if v != variable)
        factors.append(Factor(scope, np.asarray(reduced)))
    log_mass = 0.0
    for factor in factors:
        if factor.scope:
            raise RuntimeError(f"uneliminated variables in factor {factor.scope}")
        log_mass += float(factor.log_values)
    return (0.0 if log_mass == -np.inf else math.exp(log_mass)), stats


def single_location_tree() -> CategoricalModel:
    return CategoricalModel(1, 1, (CategoricalLocation(
        "single-location", (
            FaultOutcome("I", 0.8, 0, 0),
            FaultOutcome("X", 0.2, 1, 1),
        ), "I"),))


def grid_model(distance: int) -> tuple[CategoricalModel, int, int]:
    """Binary categorical variables on grid vertices, with edge-parity checks."""
    locations = []
    for r in range(distance):
        for c in range(distance):
            observable = int(c == 0)
            locations.append(CategoricalLocation(
                f"v{r}_{c}",
                (FaultOutcome("I", 0.9, 0, 0),
                 FaultOutcome("X", 0.1, 0, observable)),
                "I"))
    edges = []
    for r in range(distance):
        for c in range(distance):
            if r + 1 < distance:
                edges.append(((r, c), (r + 1, c)))
            if c + 1 < distance:
                edges.append(((r, c), (r, c + 1)))
    masks = [0] * (distance * distance)
    assignment = [((r + c) & 1) for r in range(distance) for c in range(distance)]
    syndrome = 0
    for detector, (a, b) in enumerate(edges):
        ia = a[0] * distance + a[1]
        ib = b[0] * distance + b[1]
        masks[ia] |= 1 << detector
        masks[ib] |= 1 << detector
        syndrome |= (assignment[ia] ^ assignment[ib]) << detector
    updated = []
    for i, location in enumerate(locations):
        outcomes = (FaultOutcome("I", 0.9, 0, 0),
                    FaultOutcome("X", 0.1, masks[i], int(i % distance == 0)))
        updated.append(CategoricalLocation(location.name, outcomes, "I"))
    model = CategoricalModel(len(edges), 1, tuple(updated))
    logical = sum(assignment[r * distance] for r in range(distance)) & 1
    return model, syndrome, logical


def main() -> None:
    models = {
        "single_location_tree_control": single_location_tree(),
        "one_qubit_repetition_cycle": one_qubit_model(),
        "two_qubit_repetition_cycle": two_qubit_model(),
    }
    case_rows = []
    global_max_width = 0
    global_max_entries = 1
    max_abs_error = 0.0
    for name, model in models.items():
        reference = exact_posterior(model)
        stim_joint = None
        if name == "one_qubit_repetition_cycle":
            stim_joint, _ = stim_exhaustive_joint(model, "one_qubit")
        elif name == "two_qubit_repetition_cycle":
            stim_joint, _ = stim_exhaustive_joint(model, "two_qubit")
        joint = {}
        width = 0
        max_entries = 1
        max_target_delta = 0.0
        max_stim_delta = 0.0
        start = time.perf_counter()
        for syndrome in range(1 << model.detector_count):
            pair = []
            for logical in range(2):
                mass, stats = exact_joint_mass(model, syndrome, logical)
                pair.append(mass)
                width = max(width, stats.induced_width)
                max_entries = max(max_entries, stats.max_factor_entries)
                if stats.max_factor_entries > 1_000_000:
                    raise RuntimeError(f"factor cap exceeded in {name}: {stats.max_factor_entries}")
            joint[syndrome] = tuple(pair)
            expected = reference.joint.get(syndrome, (0.0, 0.0))
            max_target_delta = max(max_target_delta,
                                   max(abs(pair[l] - expected[l]) for l in range(2)))
            if stim_joint is not None:
                stim_expected = stim_joint.get(syndrome, (0.0, 0.0))
                max_stim_delta = max(max_stim_delta,
                                     max(abs(pair[l] - stim_expected[l]) for l in range(2)))
        elapsed = time.perf_counter() - start
        post_error = 0.0
        decisions = {}
        for syndrome, pair in joint.items():
            mass = sum(pair)
            if mass > 0:
                posterior = (pair[0] / mass, pair[1] / mass)
                exact = reference.conditional[syndrome]
                post_error = max(post_error, abs(posterior[1] - exact[1]))
                decisions[syndrome] = int(pair[1] > pair[0] + 1e-15)
        decision_agreement = sum(decisions[s] == reference.decisions[s] for s in decisions)
        risk = sum(sum(p for l, p in enumerate(pair) if l != decisions[s])
                   for s, pair in joint.items())
        row = {
            "model": name,
            "fault_locations": len(model.locations),
            "max_outcomes_per_location": max(len(loc.outcomes) for loc in model.locations),
            "syndromes_evaluated": 1 << model.detector_count,
            "joint_mass_max_abs_error": max_target_delta,
            "independent_stim_joint_mass_max_abs_error": max_stim_delta if stim_joint is not None else None,
            "posterior_max_abs_error": post_error,
            "map_decisions_matching_reference": decision_agreement,
            "map_decisions_total": len(reference.decisions),
            "map_risk": risk,
            "reference_map_risk": reference.logical_error_probability,
            "induced_width": width,
            "max_intermediate_factor_entries": max_entries,
            "elapsed_seconds_all_syndromes": elapsed,
        }
        if max_target_delta > 1e-10 or post_error > 1e-10:
            raise RuntimeError(f"exact inference mismatch for {name}: {row}")
        if stim_joint is not None and max_stim_delta > 1e-10:
            raise RuntimeError(f"independent Stim mapping mismatch for {name}: {row}")
        if decision_agreement != len(reference.decisions):
            raise RuntimeError(f"MAP decision mismatch for {name}: {row}")
        if abs(risk - reference.logical_error_probability) > 1e-10:
            raise RuntimeError(f"risk mismatch for {name}: {row}")
        case_rows.append(row)
        global_max_width = max(global_max_width, width)
        global_max_entries = max(global_max_entries, max_entries)
        max_abs_error = max(max_abs_error, max_target_delta, post_error)

    grid_rows = []
    for distance in (2, 3, 5, 7, 9, 11):
        model, syndrome, logical = grid_model(distance)
        grid_start = time.perf_counter()
        mass, stats = exact_joint_mass(model, syndrome, logical)
        grid_elapsed = time.perf_counter() - grid_start
        row = {
            "grid_distance": distance,
            "fault_locations": len(model.locations),
            "detector_checks": model.detector_count,
            "target_syndrome": syndrome,
            "target_logical": logical,
            "target_joint_mass": mass,
            "induced_width": stats.induced_width,
            "max_intermediate_factor_entries": stats.max_factor_entries,
            "elapsed_seconds": grid_elapsed,
            "exhaustive_reference_checked": distance == 2,
        }
        if stats.max_factor_entries > 1_000_000:
            raise RuntimeError(f"grid factor cap exceeded: {row}")
        if distance == 2:
            reference = exact_posterior(model)
            expected = reference.joint.get(syndrome, (0.0, 0.0))[logical]
            if abs(mass - expected) > 1e-10:
                raise RuntimeError(f"grid exhaustive reference mismatch: {row}; expected={expected}")
            row["exhaustive_reference_abs_error"] = abs(mass - expected)
        grid_rows.append(row)
        global_max_width = max(global_max_width, stats.induced_width)
        global_max_entries = max(global_max_entries, stats.max_factor_entries)

    out = {
        "status": "exact_toy_feasibility_pass",
        "algorithm": "log-domain dense factor variable elimination; weighted greedy min-fill; categorical location states retained; prefix logical-XOR chain",
        "models": case_rows,
        "synthetic_grid_width_stress": grid_rows,
        "max_abs_probability_error": max_abs_error,
        "max_induced_width": global_max_width,
        "max_intermediate_factor_entries": global_max_entries,
        "state_cap": 1_000_000,
        "circuit_level_application": "not attempted; these controls are not representative Phase 2B circuit fragments",
        "stochastic_qshift_shots_generated": 0,
    }
    path = HERE / "categorical_elimination_results.json"
    path.write_text(json.dumps(out, indent=2) + "\n")
    print(f"Wrote {path}; max error={max_abs_error:.3g}; width={global_max_width}; factor entries={global_max_entries}")


if __name__ == "__main__":
    main()
