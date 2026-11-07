"""Deterministic graph-representation and local-posterior feasibility suite.

No Monte Carlo Phase 2B samples are generated. All toy and reduced-fragment
risks are computed by exact syndrome enumeration of the stated probability
model (categorical channel or independent DEM, kept separate).
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from itertools import product
import hashlib
import importlib.util
import json
import math
import os
import ctypes
from pathlib import Path
import sys
import time

import numpy as np
import pymatching
import stim

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FEAS = ROOT / "outputs" / "categorical_decoder_feasibility"
INF = ROOT / "outputs" / "categorical_inference_investigation"
PLAN = json.loads((HERE / "CASE_PLAN.json").read_text(encoding="utf-8"))
sys.path.insert(0, str(FEAS))

from categorical_reference import (  # noqa: E402
    CategoricalLocation, CategoricalModel, FaultOutcome, exact_posterior,
)
from toy_circuits import (  # noqa: E402
    PAULI_PAIRS, repetition_masks, two_qubit_model, two_qubit_probabilities,
    stim_exhaustive_joint,
)


@dataclass(frozen=True)
class DemEvent:
    probability: float
    detector_mask: int
    observable_mask: int
    separator_groups: tuple[tuple[int, int], ...]
    text: str


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def parse_dem(dem: stim.DetectorErrorModel | str) -> tuple[stim.DetectorErrorModel, list[DemEvent]]:
    """Extract each independent error instruction and its XOR-total mask."""
    if isinstance(dem, str):
        dem = stim.DetectorErrorModel(dem)
    events: list[DemEvent] = []
    for inst in dem.flattened():
        if inst.type != "error":
            continue
        groups: list[list[int]] = [[]]
        detectors: set[int] = set()
        observables: set[int] = set()
        for t in inst.targets_copy():
            if t.is_separator():
                groups.append([])
            elif t.is_relative_detector_id():
                i = int(t.val)
                detectors.symmetric_difference_update({i})
                groups[-1].append((0, i))
            elif t.is_logical_observable_id():
                i = int(t.val)
                observables.symmetric_difference_update({i})
                groups[-1].append((1, i))
            else:
                raise ValueError(f"Unsupported DEM target: {t}")
        dmask = sum(1 << i for i in detectors)
        omask = sum(1 << i for i in observables)
        # Retain parity-cancelled target groups as masks, not the textual tokens.
        group_masks: list[tuple[int, int]] = []
        for group in groups:
            gd: set[int] = set()
            go: set[int] = set()
            for typ, i in group:
                (gd if typ == 0 else go).symmetric_difference_update({i})
            group_masks.append((sum(1 << i for i in gd), sum(1 << i for i in go)))
        p = float(inst.args_copy()[0])
        if not (0 <= p <= 1):
            raise ValueError(f"Invalid event probability {p}")
        events.append(DemEvent(p, dmask, omask, tuple(group_masks), str(inst)))
    return dem, events


def exact_dem_joint(detector_count: int, observable_count: int,
                    events: list[DemEvent]) -> np.ndarray:
    """Exact XOR-DP over independent Bernoulli DEM mechanisms."""
    bits = detector_count + observable_count
    n = 1 << bits
    state = np.zeros(n, dtype=np.float64)
    state[0] = 1.0
    idx = np.arange(n, dtype=np.uint32)
    for e in events:
        mask = e.detector_mask | (e.observable_mask << detector_count)
        old = state
        nxt = old * (1.0 - e.probability)
        nxt[idx ^ mask] += old * e.probability
        state = nxt
    if not math.isclose(float(state.sum()), 1.0, rel_tol=0, abs_tol=1e-10):
        raise ArithmeticError(f"DEM posterior mass is {state.sum()}")
    return state


def categorical_joint(model: CategoricalModel) -> np.ndarray:
    """Exact XOR-DP over mutually exclusive categorical locations."""
    model.validate()
    n = 1 << (model.detector_count + model.observable_count)
    state = np.zeros(n, dtype=np.float64)
    state[0] = 1.0
    idx = np.arange(n, dtype=np.uint32)
    for loc in model.locations:
        nxt = np.zeros_like(state)
        for outcome in loc.outcomes:
            mask = outcome.detector_mask | (outcome.observable_mask << model.detector_count)
            nxt[idx ^ mask] += state * outcome.probability
        state = nxt
    if not math.isclose(float(state.sum()), 1.0, rel_tol=0, abs_tol=1e-10):
        raise ArithmeticError(f"categorical posterior mass is {state.sum()}")
    return state


def posterior_metrics(joint: np.ndarray, detector_count: int,
                      observable_count: int = 1, tie_atol: float = 1e-15) -> dict:
    """Return exact MAP decisions and Bayes risk for a flattened XOR posterior."""
    n_s = 1 << detector_count
    n_l = 1 << observable_count
    table = np.asarray(joint, dtype=np.float64).reshape(n_l, n_s)
    decisions: dict[int, int] = {}
    ties: list[int] = []
    risk = 0.0
    for s in range(n_s):
        probs = table[:, s]
        maximum = float(np.max(probs))
        winners = [l for l, p in enumerate(probs) if abs(float(p) - maximum) <= tie_atol]
        choice = min(winners)
        decisions[s] = choice
        if len(winners) > 1:
            ties.append(s)
        risk += float(probs.sum()) - float(probs[choice])
    return {"decisions": decisions, "ties": ties, "risk": risk,
            "mass": float(table.sum()), "syndrome_count": n_s}


def decoder_predictions(dem: stim.DetectorErrorModel, *, correlated: bool,
                        feasible_syndromes: np.ndarray | None = None) -> tuple[np.ndarray, float, dict]:
    """Decode all positive-mass syndromes; impossible syndromes are unscored.

    A DEM graph can have syndrome parity constraints without boundaries. Passing
    impossible syndromes to PyMatching raises a no-perfect-matching error, so
    exact posterior support determines the scored syndrome set. Output 0 for
    off-support rows only; they have exactly zero contribution to decoder risk.
    """
    started = time.perf_counter()
    matcher = pymatching.Matching.from_detector_error_model(dem, enable_correlations=correlated)
    build_s = time.perf_counter() - started
    d = int(dem.num_detectors)
    n = 1 << d
    if n > 1 << 17:
        raise MemoryError(f"refusing to enumerate {n} syndromes")
    ids = np.arange(n, dtype=np.uint32)
    all_syndromes = ((ids[:, None] >> np.arange(d, dtype=np.uint32)) & 1).astype(np.uint8)
    if feasible_syndromes is None:
        selected = np.ones(n, dtype=bool)
    else:
        selected = np.asarray(feasible_syndromes, dtype=bool)
        if selected.shape != (n,):
            raise ValueError(f"feasible_syndromes shape {selected.shape}, expected {(n,)}")
    syndromes = all_syndromes[selected]
    started = time.perf_counter()
    undecodable: list[int] = []
    if len(syndromes):
        try:
            decoded = np.asarray(matcher.decode_batch(syndromes, enable_correlations=correlated), dtype=np.uint8)
        except TypeError:  # older minor APIs allow correlation only at construction
            decoded = np.asarray(matcher.decode_batch(syndromes), dtype=np.uint8)
        except ValueError as batch_error:
            # A categorical reference may support a syndrome absent in this DEM.
            # Isolate these unsupported rows instead of discarding the whole case.
            if "No perfect matching" not in str(batch_error):
                raise
            decoded = np.zeros((len(syndromes), int(dem.num_observables)), dtype=np.uint8)
            for j, row in enumerate(syndromes):
                try:
                    one = matcher.decode(row, enable_correlations=correlated)
                except TypeError:
                    one = matcher.decode(row)
                except ValueError as e:
                    if "No perfect matching" not in str(e):
                        raise
                    undecodable.append(int(np.flatnonzero(selected)[j]))
                    continue
                decoded[j] = np.asarray(one, dtype=np.uint8).reshape(-1)
    else:
        decoded = np.zeros((0, int(dem.num_observables)), dtype=np.uint8)
    pred = np.zeros((n, int(dem.num_observables)), dtype=np.uint8)
    if decoded.ndim == 1:
        decoded = decoded[:, None]
    pred[selected] = decoded
    decode_s = time.perf_counter() - started
    if pred.shape != (n, int(dem.num_observables)):
        raise AssertionError(f"prediction shape {pred.shape}, expected {(n, dem.num_observables)}")
    if not np.isin(pred, (0, 1)).all():
        raise AssertionError("nonbinary PyMatching output")
    return pred, build_s, {"build_seconds": build_s, "feasible_syndromes_decoded": int(selected.sum()),
                           "off_support_syndromes_unscored": int(n-selected.sum()),
                           "selected_but_undecodable_syndromes": undecodable,
                           "feasible_syndrome_decode_seconds": decode_s,
                           "seconds_per_feasible_syndrome": decode_s / max(1, int(selected.sum())),
                           "nodes": int(matcher.num_nodes), "edges": int(matcher.num_edges),
                           "correlated": correlated}


def transform_graphlike(dem: stim.DetectorErrorModel) -> tuple[stim.DetectorErrorModel | None, dict]:
    """Erase separator hints only when each complete event is graphlike."""
    started = time.perf_counter()
    _, events = parse_dem(dem)
    counts = [e.detector_mask.bit_count() for e in events]
    unsupported = [i for i, c in enumerate(counts) if c > 2]
    logical_only = [i for i,e in enumerate(events) if e.detector_mask == 0 and e.observable_mask != 0]
    unsupported = sorted(set(unsupported) | set(logical_only))
    if unsupported:
        reason = ("logical-only event has no syndrome edge" if logical_only else
                  "complete event has more than two distinct detector symptoms")
        return None, {"accepted": False, "reason": reason,
                      "unsupported_event_indices": unsupported,
                      "logical_only_event_indices": logical_only,
                      "max_detector_symptoms": max(counts, default=0),
                      "preprocessing_seconds": time.perf_counter() - started}
    lines = [f"detector D{i}" for i in range(int(dem.num_detectors))]
    lines.extend(f"logical_observable L{i}" for i in range(int(dem.num_observables)))
    no_effect_events_dropped = 0
    for e in events:
        targets = [f"D{i}" for i in range(int(dem.num_detectors)) if (e.detector_mask >> i) & 1]
        targets.extend(f"L{i}" for i in range(int(dem.num_observables)) if (e.observable_mask >> i) & 1)
        if not targets:
            # Independent event with zero detector and zero observable parity is a true no-op.
            no_effect_events_dropped += 1
            continue
        suffix = (" " + " ".join(targets)) if targets else ""
        lines.append(f"error({e.probability:.17g}){suffix}")
    transformed = stim.DetectorErrorModel("\n".join(lines) + "\n")
    _, transformed_events = parse_dem(transformed)
    # This checks equality of the independent mechanism list as a multiset, including p and total parity masks.
    before = sorted((round(e.probability, 15), e.detector_mask, e.observable_mask)
                    for e in events if e.detector_mask or e.observable_mask)
    after = sorted((round(e.probability, 15), e.detector_mask, e.observable_mask) for e in transformed_events)
    if before != after:
        raise AssertionError("separator removal changed event probability/effect multiset")
    return transformed, {"accepted": True, "reason": "all complete event masks graphlike; mechanism distribution preserved",
                         "event_count": len(events), "transformed_event_count": len(transformed_events),
                         "no_effect_events_dropped": no_effect_events_dropped,
                         "max_detector_symptoms": max(counts, default=0),
                         "all_nontrivial_event_probability_and_total_mask_multiset_preserved": True,
                         "joint_detector_observable_distribution_preserved": True,
                         "preprocessing_seconds": time.perf_counter() - started}


def unchecked_separator_erasure_for_diagnostic(dem: stim.DetectorErrorModel) -> stim.DetectorErrorModel:
    """Materialize total masks without graphlike validation for audit only."""
    _, events = parse_dem(dem)
    lines = [f"detector D{i}" for i in range(int(dem.num_detectors))]
    lines.extend(f"logical_observable L{i}" for i in range(int(dem.num_observables)))
    for e in events:
        targets = [f"D{i}" for i in range(int(dem.num_detectors)) if (e.detector_mask >> i) & 1]
        targets.extend(f"L{i}" for i in range(int(dem.num_observables)) if (e.observable_mask >> i) & 1)
        lines.append(f"error({e.probability:.17g}) " + " ".join(targets))
    return stim.DetectorErrorModel("\n".join(lines) + "\n")


def audit_unsafe_separator_erasure(dem: stim.DetectorErrorModel) -> dict:
    """Record library behavior for an invalid transformation; never a candidate arm."""
    raw = unchecked_separator_erasure_for_diagnostic(dem)
    out = {"label": "invalid diagnostic only; must not be used as a decoder candidate",
           "source_has_unsupported_complete_hyperedge": True,
           "separator_free_dem_error_count": int(raw.num_errors), "dem_text": str(raw), "modes": {}}
    for correlated in (False, True):
        name = "correlated" if correlated else "standard"
        try:
            m = pymatching.Matching.from_detector_error_model(raw, enable_correlations=correlated)
            out["modes"][name] = {"construction": "accepted", "nodes": int(m.num_nodes), "edges": int(m.num_edges)}
        except Exception as e:
            out["modes"][name] = {"construction": "rejected", "exception_type": type(e).__name__, "exception": str(e)}
    return out


def local_restricted_decoder(detector_count: int, observable_count: int,
                             events: list[DemEvent], syndrome: int,
                             fallback: int, max_events: int = 12) -> tuple[int, dict]:
    """Exact local posterior under explicit exterior-zero conditioning.

    Retain events touching any active detector plus detector-free events. All
    omitted event variables are conditioned to identity. This is an exact
    posterior for that restricted model, not for the full DEM.
    """
    active = syndrome
    selected = [e for e in events if (e.detector_mask & active) or e.detector_mask == 0]
    if len(selected) > max_events:
        return fallback, {"used": False, "reason": "local event cap exceeded", "selected_events": len(selected)}
    n_l = 1 << observable_count
    joint: dict[tuple[int, int], float] = {(0, 0): 1.0}
    for e in selected:
        nxt: dict[tuple[int, int], float] = defaultdict(float)
        for (s, l), mass in joint.items():
            nxt[(s, l)] += mass * (1.0 - e.probability)
            nxt[(s ^ e.detector_mask, l ^ e.observable_mask)] += mass * e.probability
        joint = dict(nxt)
    post = [joint.get((syndrome, l), 0.0) for l in range(n_l)]
    mass = sum(post)
    if mass <= 0:
        return fallback, {"used": False, "reason": "syndrome outside restricted model support", "selected_events": len(selected)}
    maximum = max(post)
    winners = [i for i, x in enumerate(post) if abs(x - maximum) <= 1e-15]
    decision = min(winners)
    return decision, {"used": True, "selected_events": len(selected), "local_configurations": 1 << len(selected),
                      "restricted_syndrome_mass": mass, "conditional_posterior": [x / mass for x in post],
                      "tie": len(winners) > 1, "boundary_condition": "all omitted mechanisms fixed to identity"}


def categorical_toy_circuit(profiles: list[dict[str, float]]) -> stim.Circuit:
    c = stim.Circuit()
    c.append("R", [0, 1, 2])
    for (q0, q1), probs in zip(((0, 1), (1, 2)), profiles):
        args = [float(probs[p]) for p in PAULI_PAIRS]
        c.append("PAULI_CHANNEL_2", [q0, q1], args)
    c.append("MZZ", [0, 1]); c.append("DETECTOR", [stim.target_rec(-1)])
    c.append("MZZ", [1, 2]); c.append("DETECTOR", [stim.target_rec(-1)])
    c.append("M", [0, 1, 2])
    c.append("OBSERVABLE_INCLUDE", [stim.target_rec(-1), stim.target_rec(-2), stim.target_rec(-3)], 0)
    return c


def categorical_toy_model(profiles: list[dict[str, float]]) -> CategoricalModel:
    locs = []
    for j, (q0, q1) in enumerate(((0, 1), (1, 2))):
        p = profiles[j]
        outcomes = [FaultOutcome("II", 1 - sum(p.values()), 0, 0)]
        for pair in PAULI_PAIRS:
            paulis = ["I", "I", "I"]
            paulis[q0], paulis[q1] = pair
            d, l = repetition_masks(tuple(paulis))
            outcomes.append(FaultOutcome(pair, p[pair], d, l))
        locs.append(CategoricalLocation(f"pair_{j}", tuple(outcomes), "II"))
    m = CategoricalModel(2, 1, tuple(locs)); m.validate(); return m


def event_distribution_signature(events: list[DemEvent]) -> list[tuple[float, int, int]]:
    return sorted((round(e.probability, 15), e.detector_mask, e.observable_mask) for e in events)


def evaluate_dem_case(name: str, dem: stim.DetectorErrorModel, *, categorical_joint_ref: np.ndarray | None = None) -> dict:
    d, o = int(dem.num_detectors), int(dem.num_observables)
    _, events = parse_dem(dem)
    dem_joint = exact_dem_joint(d, o, events)
    exact = posterior_metrics(dem_joint, d, o)
    risk_ref = categorical_joint_ref if categorical_joint_ref is not None else dem_joint
    feasible_syndromes = dem_joint.reshape(1 << o, 1 << d).sum(axis=0) > 0
    if categorical_joint_ref is not None:
        feasible_syndromes |= categorical_joint_ref.reshape(1 << o, 1 << d).sum(axis=0) > 0
    baseline_pred, _, standard_timing = decoder_predictions(dem, correlated=False, feasible_syndromes=feasible_syndromes)
    corr_pred, _, corr_timing = decoder_predictions(dem, correlated=True, feasible_syndromes=feasible_syndromes)
    ref_metrics = posterior_metrics(risk_ref, d, o)
    pred_maps = {
        "exact_independent_dem_map": np.asarray([exact["decisions"][s] for s in range(1 << d)]),
        "pymatching_standard": baseline_pred[:, 0].astype(int),
        "pymatching_correlated": corr_pred[:, 0].astype(int),
    }
    risks = {k: decision_risk_from_array(risk_ref, d, o, v) for k, v in pred_maps.items()}
    categorical_map = None
    categorical_tv = None
    categorical_dem_map_disagreements = None
    if categorical_joint_ref is not None:
        categorical_exact = posterior_metrics(categorical_joint_ref, d, o)
        categorical_map = np.asarray([categorical_exact["decisions"][s] for s in range(1 << d)], dtype=int)
        pred_maps["exact_categorical_map"] = categorical_map
        risks["exact_categorical_map"] = decision_risk_from_array(risk_ref, d, o, categorical_map)
        categorical_tv = float(0.5 * np.abs(categorical_joint_ref - dem_joint).sum())
        categorical_dem_map_disagreements = int(np.count_nonzero(
            categorical_map != pred_maps["exact_independent_dem_map"]))
    transformed, trans = transform_graphlike(dem)
    unsafe_erasure = None if transformed is not None else audit_unsafe_separator_erasure(dem)
    if transformed is not None:
        free, _, free_timing = decoder_predictions(transformed, correlated=False, feasible_syndromes=feasible_syndromes)
        free_corr, _, free_corr_timing = decoder_predictions(transformed, correlated=True, feasible_syndromes=feasible_syndromes)
        pred_maps["separator_free_standard"] = free[:, 0].astype(int)
        pred_maps["separator_free_correlated"] = free_corr[:, 0].astype(int)
        risks["separator_free_standard"] = decision_risk_from_array(risk_ref, d, o, pred_maps["separator_free_standard"])
        risks["separator_free_correlated"] = decision_risk_from_array(risk_ref, d, o, pred_maps["separator_free_correlated"])
        trans["timing_standard"] = free_timing
        trans["timing_correlated"] = free_corr_timing
    local_preds = []
    local_diagnostics = []
    if d <= 8 and o == 1:
        local_started = time.perf_counter()
        for s in range(1 << d):
            lp, diag = local_restricted_decoder(d, o, events, s, int(pred_maps["pymatching_standard"][s]))
            local_preds.append(lp); local_diagnostics.append(diag)
        local_runtime = time.perf_counter() - local_started
        pred_maps["local_restricted_posterior"] = np.asarray(local_preds, dtype=int)
        risks["local_restricted_posterior"] = decision_risk_from_array(risk_ref, d, o, pred_maps["local_restricted_posterior"])
    nsynd = 1 << d
    disagreements = {}
    for a, b in product(pred_maps, repeat=2):
        if a < b:
            disagreements[f"{a}_vs_{b}"] = int(np.count_nonzero(pred_maps[a] != pred_maps[b]))
    return {
        "name": name, "detectors": d, "observables": o, "event_count": len(events),
        "dem_text": str(dem),
        "separator_event_count": sum(len(e.separator_groups) > 1 for e in events),
        "max_detector_symptoms_per_complete_event": max((e.detector_mask.bit_count() for e in events), default=0),
        "exact_independent_dem_map_risk": exact["risk"],
        "scoring_reference": "exact_categorical_channel" if categorical_joint_ref is not None else "exact_independent_dem",
        "exact_reference_risk": ref_metrics["risk"], "posterior_mass": exact["mass"],
        "tie_syndromes": exact["ties"], "risk_by_decoder": risks,
        "disagreements_by_syndrome_count": disagreements,
        "prediction_maps": {k: v.tolist() for k, v in pred_maps.items()},
        "transform": trans,
        "unchecked_separator_erasure_diagnostic": unsafe_erasure,
        "local_refinement": ({"applied_syndromes": sum(x["used"] for x in local_diagnostics),
                              "fallback_syndromes": sum(not x["used"] for x in local_diagnostics),
                              "max_selected_events": max((x.get("selected_events", 0) for x in local_diagnostics), default=0),
                              "max_local_configurations": max((x.get("local_configurations", 0) for x in local_diagnostics), default=0),
                              "all_syndrome_local_evaluation_seconds": local_runtime,
                              "seconds_per_syndrome": local_runtime / (1 << d),
                              "reason_counts": dict((why, sum(x.get("reason") == why for x in local_diagnostics))
                                                    for why in sorted({x.get("reason") for x in local_diagnostics if x.get("reason")})),
                              "per_syndrome": local_diagnostics} if local_diagnostics else {"status": "not attempted; detector count exceeds exact local sweep limit"}),
        "runtime": {"standard": standard_timing, "correlated": corr_timing},
        "all_syndromes": nsynd,
        "categorical_vs_independent_dem_joint_tv_distance": categorical_tv,
        "categorical_vs_independent_dem_map_disagreements": categorical_dem_map_disagreements,
    }


def decision_risk_from_array(joint: np.ndarray, detector_count: int, observable_count: int,
                             predictions: np.ndarray) -> float:
    table = np.asarray(joint).reshape(1 << observable_count, 1 << detector_count)
    preds = np.asarray(predictions, dtype=int)
    risk = 0.0
    for s, pred in enumerate(preds):
        risk += float(table[:, s].sum() - table[int(pred), s])
    return risk


def make_custom_dem(d: int, o: int, events: list[tuple[float, int, int, list[tuple[int, int]]]]) -> stim.DetectorErrorModel:
    lines = [f"detector D{i}" for i in range(d)] + [f"logical_observable L{i}" for i in range(o)]
    for p, _, _, groups in events:
        toks = []
        for gi, (dm, om) in enumerate(groups):
            if gi:
                toks.append("^")
            toks.extend(f"D{i}" for i in range(d) if (dm >> i) & 1)
            toks.extend(f"L{i}" for i in range(o) if (om >> i) & 1)
        lines.append(f"error({p:.17g}) " + " ".join(toks))
    return stim.DetectorErrorModel("\n".join(lines) + "\n")


def make_separator_grid_case(p: float, q: float, r: float, *, separators: bool = True) -> stim.DetectorErrorModel:
    main_groups = [(1, 1), (2, 0)] if separators else [(3, 1)]
    return make_custom_dem(2, 1, [(p, 3, 1, main_groups), (q, 1, 0, [(1, 0)]), (r, 2, 0, [(2, 0)])])


def all_syndrome_agg(dem: stim.DetectorErrorModel) -> dict:
    d, o = int(dem.num_detectors), int(dem.num_observables)
    _, events = parse_dem(dem)
    joint = exact_dem_joint(d, o, events)
    exact = posterior_metrics(joint, d, o)
    feasible = joint.reshape(1 << o, 1 << d).sum(axis=0) > 0
    a, _, _ = decoder_predictions(dem, correlated=False, feasible_syndromes=feasible)
    b, _, _ = decoder_predictions(dem, correlated=True, feasible_syndromes=feasible)
    no_sep, valid = transform_graphlike(dem)
    results = {"exact": exact, "standard": a[:, 0].astype(int), "correlated": b[:, 0].astype(int), "transform": valid}
    if no_sep is not None:
        c, _, _ = decoder_predictions(no_sep, correlated=False, feasible_syndromes=feasible)
        d2, _, _ = decoder_predictions(no_sep, correlated=True, feasible_syndromes=feasible)
        results["no_separator"] = c[:, 0].astype(int)
        results["no_separator_correlated"] = d2[:, 0].astype(int)
    for k, pred in list(results.items()):
        if isinstance(pred, np.ndarray):
            results[k + "_risk"] = decision_risk_from_array(joint, d, o, pred)
    results["joint"] = joint
    return results


def reproduce_historical() -> dict:
    m = two_qubit_model()
    cat = categorical_joint(m)
    cat_metrics = posterior_metrics(cat, 2, 1)
    cartesian = exact_posterior(m)
    cartesian_vec = np.zeros_like(cat)
    for syndrome, masses in cartesian.joint.items():
        for logical, mass in enumerate(masses):
            cartesian_vec[syndrome | (logical << m.detector_count)] = mass
    stim_joint, stim_configurations = stim_exhaustive_joint(m, "two_qubit")
    stim_vec = np.zeros_like(cat)
    for syndrome, masses in stim_joint.items():
        for logical, mass in enumerate(masses):
            stim_vec[syndrome | (logical << m.detector_count)] = mass
    if max(float(np.max(np.abs(cat-cartesian_vec))), float(np.max(np.abs(cat-stim_vec)))) > 1e-12:
        raise AssertionError("independent categorical DP, Cartesian enumeration, and Stim forced outcomes disagree")
    # Rebuild the original two-qubit DEM from the frozen fixture helper.
    from toy_circuits import noisy_stim_circuit
    dem = noisy_stim_circuit("two_qubit").detector_error_model(
        decompose_errors=True, approximate_disjoint_errors=True)
    result = evaluate_dem_case("historical_two_qubit_categorical_toy", dem, categorical_joint_ref=cat)
    # Independent exact DEM MAP must agree with exact categorical MAP for all four syndromes.
    dem_exact = posterior_metrics(exact_dem_joint(2, 1, parse_dem(dem)[1]), 2, 1)
    result["categorical_exact_map_decisions"] = {str(k): v for k, v in cat_metrics["decisions"].items()}
    result["independent_dem_exact_map_decisions"] = {str(k): v for k, v in dem_exact["decisions"].items()}
    result["categorical_vs_dem_map_all_four_agree"] = cat_metrics["decisions"] == dem_exact["decisions"]
    result["categorical_profiles"] = [two_qubit_probabilities(), two_qubit_probabilities()]
    result["categorical_reference_crosschecks"] = {"cartesian_and_stim_forced_outcome_configurations": stim_configurations,
        "max_abs_difference_xor_dp_vs_cartesian": float(np.max(np.abs(cat-cartesian_vec))),
        "max_abs_difference_xor_dp_vs_stim_forced_outcomes": float(np.max(np.abs(cat-stim_vec))),
        "all_three_independent_routes_agree": True}
    # Historical separator-free graph was formed by retaining event masks and removing only separators.
    return result


def run_suite() -> dict:
    started = time.perf_counter()
    result: dict = {
        "software": {"python": sys.version.split()[0], "stim": stim.__version__,
                     "pymatching": pymatching.__version__, "numpy": np.__version__},
        "plan_sha256": sha256(HERE / "CASE_PLAN.json"),
        "no_stochastic_shots": True,
        "historical_reproduction": reproduce_historical(),
        "categorical_seed_cases": [], "separator_grid": [], "decomposition_fixtures": [],
        "reduced_surface_fragments": [], "full_phase2b_structure": [],
    }
    # Eight deterministic channel profiles from the preregistered independent seeds.
    for seed in [61001, 61002, 61003, 61004, 61005, 61006, 61007, 61008]:
        rng = np.random.default_rng(seed)
        profiles = []
        for _ in range(2):
            probs = rng.dirichlet(np.full(15, 0.35)) * 0.12
            profiles.append(dict(zip(PAULI_PAIRS, probs.tolist())))
        cat_model = categorical_toy_model(profiles)
        cat = categorical_joint(cat_model)
        circ = categorical_toy_circuit(profiles)
        dem = circ.detector_error_model(decompose_errors=True, approximate_disjoint_errors=True)
        row = evaluate_dem_case(f"random_categorical_chain_seed_{seed}", dem, categorical_joint_ref=cat)
        row["seed"] = seed
        row["categorical_profiles"] = profiles
        row["categorical_channel_probability_checks"] = [sum(p.values()) for p in profiles]
        result["categorical_seed_cases"].append(row)
    # Complete preregistered 4x4x4 grid; each pair of DEMs has identical event masks/probabilities.
    # Analyze all cells of the prespecified grid, retaining paired representation arms.
    grid = []
    for p, q, r in product([0.01, 0.03, 0.1, 0.2], repeat=3):
        sep = make_separator_grid_case(p, q, r, separators=True)
        no = make_separator_grid_case(p, q, r, separators=False)
        d, events = parse_dem(sep); joint = exact_dem_joint(d.num_detectors, d.num_observables, events)
        exact = posterior_metrics(joint, 2, 1)
        feasible = joint.reshape(2, 4).sum(axis=0) > 0
        s0, _, _ = decoder_predictions(sep, correlated=False, feasible_syndromes=feasible)
        s1, _, _ = decoder_predictions(sep, correlated=True, feasible_syndromes=feasible)
        n0, _, _ = decoder_predictions(no, correlated=False, feasible_syndromes=feasible)
        n1, _, _ = decoder_predictions(no, correlated=True, feasible_syndromes=feasible)
        v_s0=s0[:,0].astype(int); v_s1=s1[:,0].astype(int); v_n0=n0[:,0].astype(int); v_n1=n1[:,0].astype(int)
        grid.append({"p": p, "q": q, "r": r, "event_distribution_identical": event_distribution_signature(events)==event_distribution_signature(parse_dem(no)[1]),
                     "separator_dem_text": str(sep), "separator_free_dem_text": str(no),
                     "exact_dem_risk": exact["risk"],
                     "separator_standard_risk": decision_risk_from_array(joint,2,1,v_s0),
                     "separator_correlated_risk": decision_risk_from_array(joint,2,1,v_s1),
                     "separator_free_standard_risk": decision_risk_from_array(joint,2,1,v_n0),
                     "separator_free_correlated_risk": decision_risk_from_array(joint,2,1,v_n1),
                     "separator_standard_decisions": v_s0.tolist(), "separator_correlated_decisions": v_s1.tolist(),
                     "separator_free_standard_decisions": v_n0.tolist(), "separator_free_correlated_decisions": v_n1.tolist(),
                     "standard_disagreements_sep_vs_free": int(np.count_nonzero(v_s0 != v_n0)),
                     "correlated_disagreements_sep_vs_free": int(np.count_nonzero(v_s1 != v_n1))})
    result["separator_grid"] = grid
    # One two-detector same-event alternate separator partition, and a four-detector two-pairing hyperedge.
    fixture_specs = [
        ("same_two_detector_event_logical_on_left_vs_right", 2,
         [(0.03, 3, 1, [(1, 1), (2, 0)]), (0.08, 1, 0, [(1, 0)]), (0.05, 2, 0, [(2, 0)])],
         [(0.03, 3, 1, [(1, 0), (2, 1)]), (0.08, 1, 0, [(1, 0)]), (0.05, 2, 0, [(2, 0)])]),
        ("four_detector_alternative_pairing_A", 4,
         [(0.07, 15, 1, [(3, 1), (12, 0)]), (0.05, 3, 0, [(3, 0)]), (0.05, 12, 0, [(12, 0)])], None),
        ("four_detector_alternative_pairing_B", 4,
         [(0.07, 15, 1, [(5, 1), (10, 0)]), (0.05, 3, 0, [(3, 0)]), (0.05, 12, 0, [(12, 0)])], None),
    ]
    for name, d, events1, events2 in fixture_specs:
        dem_a = make_custom_dem(d, 1, events1)
        _, ev_a = parse_dem(dem_a)
        entry = {"name": name, "primary": evaluate_dem_case(name, dem_a)}
        if events2 is not None:
            dem_b = make_custom_dem(d, 1, events2)
            _, ev_b = parse_dem(dem_b)
            b = evaluate_dem_case(name + "_alternate", dem_b)
            entry["alternate_decomposition"] = b
            entry["same_total_independent_event_distribution"] = event_distribution_signature(ev_a) == event_distribution_signature(ev_b)
        else:
            entry["alternate_decomposition"] = None
        result["decomposition_fixtures"].append(entry)
    pair_specs = [
        ("same_two_detector_event_logical_on_left_vs_right",
         result["decomposition_fixtures"][0]["primary"],
         result["decomposition_fixtures"][0]["alternate_decomposition"], True),
        ("four_detector_alternative_pairing_A_vs_B",
         result["decomposition_fixtures"][1]["primary"],
         result["decomposition_fixtures"][2]["primary"],
         event_distribution_signature(parse_dem(make_custom_dem(4,1,fixture_specs[1][2]))[1]) ==
         event_distribution_signature(parse_dem(make_custom_dem(4,1,fixture_specs[2][2]))[1])),
    ]
    pair_rows = []
    for name, a, b, same_distribution in pair_specs:
        pairs = {}
        common = set(a["prediction_maps"]) & set(b["prediction_maps"])
        for decoder in sorted(common):
            pa = np.asarray(a["prediction_maps"][decoder]); pb = np.asarray(b["prediction_maps"][decoder])
            changed = np.flatnonzero(pa != pb).tolist()
            pairs[decoder] = {"decision_disagreement_count": len(changed), "syndromes": changed}
        pair_rows.append({"comparison": name, "same_independent_event_distribution": bool(same_distribution),
                          "decoder_comparisons": pairs,
                          "risk_primary": a["risk_by_decoder"], "risk_alternate": b["risk_by_decoder"],
                          "separator_free_candidate_exists": "separator_free_standard" in common})
    result["decomposition_pair_comparisons"] = pair_rows
    # Small, fixed Phase 2B generator fragments; reduced rounds only, full five-round unchanged.
    frag_spec = importlib.util.spec_from_file_location("qshift_phase2b_fragments", INF / "phase2b_fragments.py")
    assert frag_spec and frag_spec.loader
    frag_mod = importlib.util.module_from_spec(frag_spec); sys.modules[frag_spec.name] = frag_mod; frag_spec.loader.exec_module(frag_mod)
    for basis, rounds in product(("z", "x"), (1, 2)):
        circ = frag_mod.build_fragment(rounds=rounds, memory_basis=basis, regime="balanced")
        dem = circ.detector_error_model(decompose_errors=True, approximate_disjoint_errors=True)
        exact_dem = evaluate_dem_case(f"phase2b_{basis}_memory_r{rounds}_balanced", dem)
        exact_dem["circuit_sha256"] = hashlib.sha256(str(circ).encode()).hexdigest()
        exact_dem["circuit_detectors"] = int(circ.num_detectors); exact_dem["circuit_observables"] = int(circ.num_observables)
        exact_dem["rounds"] = rounds; exact_dem["basis"] = basis; exact_dem["noise_regime"] = "balanced"
        result["reduced_surface_fragments"].append(exact_dem)
    # Structural-only full Phase 2B model inspection, no exponentially large syndrome enumeration.
    noise_path = ROOT / "outputs" / "phase2b_pauli_bias" / "noise_model.py"
    spec = importlib.util.spec_from_file_location("qshift_phase2b_noise", noise_path)
    assert spec and spec.loader
    noise = importlib.util.module_from_spec(spec); sys.modules[spec.name] = noise; spec.loader.exec_module(noise)
    for basis, regime in product(noise.MEMORY_BASES, noise.REGIMES):
        circ = noise.build_circuit(basis, regime, distance=3, rounds=5)
        dem = circ.detector_error_model(decompose_errors=True, approximate_disjoint_errors=True)
        saved_circuit = ROOT / "outputs" / "phase2b_pauli_bias" / "dems" / f"circuit_{basis}_{regime}.stim"
        saved_dem = ROOT / "outputs" / "phase2b_pauli_bias" / "dems" / f"dem_{basis}_{regime}.dem"
        build_started = time.perf_counter()
        matcher_standard = pymatching.Matching.from_detector_error_model(dem, enable_correlations=False)
        standard_build = time.perf_counter() - build_started
        build_started = time.perf_counter()
        matcher_correlated = pymatching.Matching.from_detector_error_model(dem, enable_correlations=True)
        correlated_build = time.perf_counter() - build_started
        _, ev = parse_dem(dem)
        _, trans = transform_graphlike(dem)
        support_counts = {str(k): sum(e.detector_mask.bit_count()==k for e in ev) for k in range(5)}
        result["full_phase2b_structure"].append({"basis": basis, "regime": regime,
            "circuit_sha256": hashlib.sha256(str(circ).encode()).hexdigest(),
            "dem_sha256": hashlib.sha256(str(dem).encode()).hexdigest(),
            "saved_circuit_text_matches_rebuild": saved_circuit.is_file() and saved_circuit.read_text(encoding="utf-8")==str(circ),
            "saved_dem_text_matches_rebuild": saved_dem.is_file() and saved_dem.read_text(encoding="utf-8")==str(dem),
            "saved_circuit_file_sha256": sha256(saved_circuit) if saved_circuit.is_file() else None,
            "saved_dem_file_sha256": sha256(saved_dem) if saved_dem.is_file() else None,
            "detectors": int(dem.num_detectors), "observables": int(dem.num_observables),
            "error_mechanisms": len(ev), "separator_mechanisms": sum(len(e.separator_groups)>1 for e in ev),
            "complete_event_detector_support_counts": support_counts,
            "matching_graphs": {"standard": {"nodes": int(matcher_standard.num_nodes), "edges": int(matcher_standard.num_edges), "build_seconds": standard_build},
                                "correlated": {"nodes": int(matcher_correlated.num_nodes), "edges": int(matcher_correlated.num_edges), "build_seconds": correlated_build}},
            "max_complete_detector_symptoms": max((e.detector_mask.bit_count() for e in ev), default=0),
            "graphlike_transform": trans, "stochastic_shots": 0})
    result["elapsed_seconds"] = time.perf_counter() - started
    result["peak_memory"] = peak_working_set()
    result["stochastic_phase2b_shots_generated"] = 0
    result["phase2b_full_test_labels_read"] = False
    return result


def write_outputs(result: dict) -> None:
    (HERE / "RESULTS.json").write_text(json.dumps(result, indent=2, default=_json_default) + "\n", encoding="utf-8")
    rows = []
    for r in result["separator_grid"]:
        rows.append({k: r[k] for k in ("p", "q", "r", "exact_dem_risk", "separator_standard_risk", "separator_correlated_risk", "separator_free_standard_risk", "separator_free_correlated_risk", "standard_disagreements_sep_vs_free", "correlated_disagreements_sep_vs_free")})
    import csv
    with (HERE / "SEPARATOR_GRID.csv").open("w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    sr=[]
    for r in result["reduced_surface_fragments"]:
        sr.append({"name":r["name"],"basis":r["basis"],"rounds":r["rounds"],"detectors":r["detectors"],"events":r["event_count"],"separators":r["separator_event_count"],"exact_dem_risk":r["exact_independent_dem_map_risk"],"standard_risk":r["risk_by_decoder"]["pymatching_standard"],"correlated_risk":r["risk_by_decoder"]["pymatching_correlated"],"transform_accepted":r["transform"]["accepted"],"transform_reason":r["transform"]["reason"]})
    with (HERE / "SURFACE_FRAGMENT_SUMMARY.csv").open("w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=list(sr[0])); w.writeheader(); w.writerows(sr)


def _json_default(v):
    if isinstance(v, np.generic): return v.item()
    if isinstance(v, np.ndarray): return v.tolist()
    raise TypeError(type(v).__name__)


def peak_working_set() -> dict:
    """Read Windows process peak working set; no third-party sampler needed."""
    try:
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
        counters = Counters(); counters.cb = ctypes.sizeof(counters)
        kernel = ctypes.WinDLL("Kernel32.dll")
        psapi = ctypes.WinDLL("Psapi.dll")
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            return {"status": "unavailable", "reason": "GetProcessMemoryInfo returned false"}
        return {"status": "measured", "peak_working_set_bytes": int(counters.PeakWorkingSetSize),
                "current_working_set_bytes": int(counters.WorkingSetSize), "method": "Windows GetProcessMemoryInfo peak for this process"}
    except Exception as e:
        return {"status": "unavailable", "reason": f"{type(e).__name__}: {e}"}


def main() -> None:
    results = run_suite()
    write_outputs(results)
    print(json.dumps({"status":"COMPLETED", "elapsed_seconds":results["elapsed_seconds"],
        "categorical_toys":len(results["categorical_seed_cases"]),"separator_grid":len(results["separator_grid"]),
        "surface_fragments":len(results["reduced_surface_fragments"]),"full_phase2b_structure":len(results["full_phase2b_structure"]),
        "stochastic_phase2b_shots":results["stochastic_phase2b_shots_generated"],
        "output":str(HERE/"RESULTS.json")},indent=2))


if __name__ == "__main__": main()
