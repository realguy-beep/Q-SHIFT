"""Categorical fault/parity factor graph and small dense variable elimination."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
import math

import numpy as np


@dataclass
class Factor:
    scope: tuple[int, ...]
    values: np.ndarray


def make_factor_graph(model):
    """Create priors plus one parity constraint for each D and L output bit."""
    fault_n = len(model.locations)
    output_n = model.detector_count + model.observable_count
    output_ids = tuple(range(fault_n, fault_n + output_n))
    domains = {i: len(loc.outcomes) for i, loc in enumerate(model.locations)}
    domains.update({i: 2 for i in output_ids})
    scopes = [(i,) for i in range(fault_n)]  # categorical priors
    parity_scopes = []
    for bit in range(output_n):
        active = []
        for i, loc in enumerate(model.locations):
            if any((((o.detector_mask >> bit) & 1) if bit < model.detector_count
                    else ((o.observable_mask >> (bit-model.detector_count)) & 1)) for o in loc.outcomes):
                active.append(i)
        scope = tuple([output_ids[bit], *active])
        parity_scopes.append(scope)
        scopes.append(scope)
    graph = {i: set() for i in domains}
    for scope in scopes:
        for a, b in product(scope, repeat=2):
            if a != b:
                graph[a].add(b)
    return {"fault_count": fault_n, "output_ids": output_ids, "domains": domains,
            "factor_scopes": scopes, "parity_scopes": parity_scopes, "graph": graph}


def elimination_order(graph_info, heuristic: str):
    """Symbolically eliminate fault variables while retaining output variables."""
    if heuristic not in ("min_fill", "min_degree"):
        raise ValueError(heuristic)
    graph = {v: set(ns) for v, ns in graph_info["graph"].items()}
    domains = graph_info["domains"]
    candidates = set(range(graph_info["fault_count"]))
    order, steps = [], []
    while candidates:
        scored = []
        for v in candidates:
            ns = graph[v]
            missing = sum(1 for a,b in product(ns, repeat=2) if a < b and b not in graph[a])
            if heuristic == "min_fill":
                score = (missing, len(ns), v)
            else:
                score = (len(ns), missing, v)
            scored.append((score, v, missing, tuple(sorted(ns))))
        _, v, fill, neighbors = min(scored)
        neighbor_state_count = math.prod(domains[n] for n in neighbors)
        combined_state_count = domains[v] * neighbor_state_count
        steps.append({"variable": v, "neighbor_count": len(neighbors), "fill_edges": fill,
                      "neighbor_states": neighbor_state_count,
                      "combined_factor_states": combined_state_count,
                      "log2_combined_states": math.log2(combined_state_count) if combined_state_count else 0.0})
        for a,b in product(neighbors, repeat=2):
            if a != b:
                graph[a].add(b)
        for n in neighbors:
            graph[n].discard(v)
        graph[v].clear()
        candidates.remove(v)
        order.append(v)
    return {"heuristic": heuristic, "order": order, "steps": steps,
            "induced_width": max((s["neighbor_count"] for s in steps), default=0),
            "max_combined_factor_states": max((s["combined_factor_states"] for s in steps), default=1),
            "max_combined_log2_states": max((s["log2_combined_states"] for s in steps), default=0.0)}


def _parity_bit(outcome, bit, detector_count):
    return ((outcome.detector_mask >> bit) & 1) if bit < detector_count else ((outcome.observable_mask >> (bit-detector_count)) & 1)


def make_dense_toy_factors(model):
    """Materialize parity tensors; intended only for toy graph validation."""
    info = make_factor_graph(model)
    fault_n = len(model.locations)
    domains = info["domains"]
    factors = []
    for i, loc in enumerate(model.locations):
        factors.append(Factor((i,), np.asarray([o.probability for o in loc.outcomes], dtype=np.float64)))
    for bit, scope in enumerate(info["parity_scopes"]):
        shape = tuple(domains[v] for v in scope)
        table = np.zeros(shape, dtype=np.float64)
        for assignment in product(*(range(n) for n in shape)):
            output = assignment[0]
            parity = 0
            for var, state in zip(scope[1:], assignment[1:]):
                parity ^= _parity_bit(model.locations[var].outcomes[state], bit, model.detector_count)
            if output == parity:
                table[assignment] = 1.0
        factors.append(Factor(scope, table))
    return info, factors


def _combine(factors, domains):
    scope = tuple(sorted(set().union(*(f.scope for f in factors))))
    shape = tuple(domains[v] for v in scope)
    result = np.ones(shape, dtype=np.float64)
    positions = {v: i for i,v in enumerate(scope)}
    for factor in factors:
        reshape = [1] * len(scope)
        ordered_axes = sorted(range(len(factor.scope)), key=lambda axis: positions[factor.scope[axis]])
        for axis in ordered_axes:
            v = factor.scope[axis]
            reshape[positions[v]] = domains[v]
        values = factor.values if ordered_axes == list(range(len(factor.scope))) else np.transpose(factor.values, ordered_axes)
        result *= values.reshape(reshape)
    return Factor(scope, result)


def run_dense_ve(model, heuristic: str):
    info, factors = make_dense_toy_factors(model)
    initial_max = max((f.values.size for f in factors), default=1)
    ordering = elimination_order(info, heuristic)
    max_cells = initial_max
    for v in ordering["order"]:
        bucket = [f for f in factors if v in f.scope]
        factors = [f for f in factors if v not in f.scope]
        if not bucket:
            continue
        combined = _combine(bucket, info["domains"])
        max_cells = max(max_cells, combined.values.size)
        axis = combined.scope.index(v)
        new_scope = tuple(x for x in combined.scope if x != v)
        factors.append(Factor(new_scope, combined.values.sum(axis=axis)))
    final = _combine(factors, info["domains"])
    output_scope = info["output_ids"]
    if final.scope != tuple(sorted(output_scope)):
        raise AssertionError((final.scope, output_scope))
    decisions = {}
    risk = 0.0
    total = 0.0
    for mask in range(1 << len(output_scope)):
        index = tuple((mask >> (v-info["fault_count"])) & 1 for v in final.scope)
        mass = float(final.values[index]); total += mass
        # Output bits are detector bits first, followed by observable bits.
        syndrome = mask & ((1 << model.detector_count)-1)
        logical = mask >> model.detector_count
        # Collect below after grouping by syndrome.
    joint = {}
    for mask in range(1 << len(output_scope)):
        index = tuple((mask >> (v-info["fault_count"])) & 1 for v in final.scope)
        mass = float(final.values[index])
        syndrome = mask & ((1 << model.detector_count)-1)
        logical = mask >> model.detector_count
        bucket = joint.setdefault(syndrome, [0.0] * (1 << model.observable_count))
        bucket[logical] = mass
    ties = []
    for s, probs in joint.items():
        maximum = max(probs)
        winners = [l for l,p in enumerate(probs) if abs(p-maximum) <= 1e-15]
        decisions[s] = min(winners)
        if len(winners)>1: ties.append(s)
        risk += sum(probs)-probs[decisions[s]]
    return {"heuristic": heuristic, "joint": {s: tuple(p) for s,p in joint.items()},
            "decisions": decisions, "risk": risk, "total_mass": total,
            "tie_syndromes": tuple(sorted(ties)), "max_intermediate_cells": max_cells,
            "induced_width": ordering["induced_width"],
            "max_combined_factor_states": ordering["max_combined_factor_states"],
            "order": ordering["order"]}
