"""Non-sampling structural round-trip against HAMLD's pinned DEM parser.

This imports the exact upstream dem_to_hypergraph.py while bypassing HAMLD's
package __init__ (which imports the unbuilt C++ extension). It does NOT import
or emulate a decoder and does not call any sampling or inference API.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import types
from collections import Counter
from decimal import Decimal
from pathlib import Path


def load_upstream_parser(hamld_source_root: Path):
    src = hamld_source_root / "src" / "hamld"
    parser = src / "contraction_strategy" / "dem_to_hypergraph.py"
    if not parser.is_file():
        raise FileNotFoundError(f"pinned HAMLD parser not found: {parser}")
    # Import exact source modules without executing package __init__.py. The
    # shim only supplies package search paths; the parser implementation is
    # loaded from the pinned upstream file at the user-supplied source root.
    hamld_pkg = types.ModuleType("hamld")
    hamld_pkg.__path__ = [str(src)]
    sys.modules["hamld"] = hamld_pkg
    strategy_pkg = types.ModuleType("hamld.contraction_strategy")
    strategy_pkg.__path__ = [str(src / "contraction_strategy")]
    sys.modules["hamld.contraction_strategy"] = strategy_pkg
    from hamld.contraction_strategy.dem_to_hypergraph import (  # noqa: PLC0415
        DetectorErrorModelHypergraph,
    )

    return DetectorErrorModelHypergraph


def targets_to_edge(targets) -> tuple[str, ...]:
    edge = []
    for t in targets:
        if t.is_relative_detector_id():
            edge.append(f"D{t.val}")
        elif t.is_logical_observable_id():
            edge.append(f"L{t.val}")
        elif t.is_separator():
            raise AssertionError("undecomposed input unexpectedly contains a separator")
    return tuple(edge)


def event_probability_from_text(line: str) -> Decimal:
    match = re.match(r"^error\(([^)]*)\)", line)
    if not match:
        raise AssertionError(f"could not parse DEM probability from {line!r}")
    return Decimal(match.group(1))


def summarize(dem, hypergraph) -> dict:
    lines = str(dem).splitlines()
    expected_edges: list[tuple[str, ...]] = []
    expected_probs: list[Decimal] = []
    instruction_types = Counter()
    for i, inst in enumerate(dem):
        instruction_types[inst.type] += 1
        if inst.type == "error":
            expected_edges.append(targets_to_edge(inst.targets_copy()))
            expected_probs.append(event_probability_from_text(lines[i]))

    actual_edges = [tuple(x) for x in hypergraph.hyperedges]
    actual_probs = list(hypergraph.weights)
    if len(actual_edges) != len(expected_edges) or len(actual_probs) != len(expected_probs):
        raise AssertionError("HAMLD parser changed mechanism cardinality")
    if actual_edges != expected_edges:
        mismatch = next(i for i, (a, b) in enumerate(zip(actual_edges, expected_edges)) if a != b)
        raise AssertionError(f"target mapping/order differs at mechanism {mismatch}")
    if actual_probs != expected_probs:
        mismatch = next(i for i, (a, b) in enumerate(zip(actual_probs, expected_probs)) if a != b)
        raise AssertionError(f"probability differs at mechanism {mismatch}: {actual_probs[mismatch]} != {expected_probs[mismatch]}")

    duplicates = len(actual_edges) - len(set(actual_edges))
    if duplicates:
        raise AssertionError(f"unexpected duplicate signatures: {duplicates}")
    if any(t in instruction_types for t in ("repeat", "shift_detectors")):
        raise AssertionError("Q-SHIFT DEM unexpectedly includes repeat/shift instructions")

    detector_only_boundary = [e for e in actual_edges if sum(x.startswith("D") for x in e) == 1 and not any(x.startswith("L") for x in e)]
    single_detector = [e for e in actual_edges if sum(x.startswith("D") for x in e) == 1]
    mult_detector = [e for e in actual_edges if sum(x.startswith("D") for x in e) > 1]
    logical_bearing = [e for e in actual_edges if any(x.startswith("L") for x in e)]
    logical_only = [e for e in actual_edges if not any(x.startswith("D") for x in e)]
    return {
        "num_detectors": dem.num_detectors,
        "num_observables": dem.num_observables,
        "node_ids_in_order": hypergraph.nodes,
        "instruction_types": dict(sorted(instruction_types.items())),
        "error_mechanisms": len(expected_edges),
        "ordered_target_roundtrip_all_equal": True,
        "exact_decimal_probability_roundtrip_all_equal": True,
        "unique_target_signatures": len(set(actual_edges)),
        "duplicate_signatures": duplicates,
        "single_detector_mechanisms_total": len(single_detector),
        "detector_only_single_detector_boundary_mechanisms": len(detector_only_boundary),
        "single_detector_with_logical_target": len(single_detector) - len(detector_only_boundary),
        "multi_detector_hyperedges": len(mult_detector),
        "max_detector_degree": max((sum(x.startswith("D") for x in e) for e in actual_edges), default=0),
        "logical_bearing_mechanisms": len(logical_bearing),
        "logical_only_mechanisms": len(logical_only),
        "repeat_or_shift_present": False,
        "independent_bernoulli_weights_range": [
            str(min(actual_probs)), str(max(actual_probs))
        ] if actual_probs else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hamld-source-root", type=Path, required=True,
                        help="checkout/archive root of HAMLD commit b80c627...")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo / "outputs" / "phase3a_correlated_noise_preflight"))
    from simulator import build_spatial_burst_circuit  # noqa: PLC0415
    import stim  # noqa: PLC0415

    DetectorErrorModelHypergraph = load_upstream_parser(args.hamld_source_root)
    results = []
    models = {}
    circuit_metadata = None
    for burst_p in (0.0, 0.01):
        circuit = build_spatial_burst_circuit(
            memory_basis="z", regime="balanced", distance=3, rounds=5,
            gate_p=0.003, measurement_p=0.003, burst_probability=burst_p,
        )
        dem = circuit.detector_error_model(
            decompose_errors=False, approximate_disjoint_errors=True
        )
        if (dem.num_detectors, dem.num_observables) != (40, 1):
            raise AssertionError("unexpected Q-SHIFT detector/observable dimensions")
        if circuit_metadata is None:
            coords = circuit.get_detector_coordinates()
            obs = [str(inst) for inst in circuit.flattened() if inst.name == "OBSERVABLE_INCLUDE"]
            circuit_metadata = {
                "first_four_detector_coordinates": {str(k): v for k, v in list(coords.items())[:4]},
                "last_three_detector_coordinates": {str(k): v for k, v in list(coords.items())[-3:]},
                "observable_include": obs,
            }
        h = DetectorErrorModelHypergraph(dem, have_logical_observable=True)
        if h.nodes != [*(f"D{i}" for i in range(40)), "L0"]:
            raise AssertionError("HAMLD parser changed detector or logical node IDs/order")
        results.append({"burst_probability": burst_p, **summarize(dem, h)})
        models[burst_p] = dem

    def error_map(dem):
        out = {}
        for inst in dem:
            if inst.type == "error":
                out[targets_to_edge(inst.targets_copy())] = inst.args_copy()[0]
        return out

    base = error_map(models[0.0])
    burst = error_map(models[0.01])
    common_probability_changes = [
        {"targets": list(k), "p0": base[k], "p01": burst[k]}
        for k in sorted(set(base) & set(burst)) if base[k] != burst[k]
    ]
    new_burst_events = [
        {"targets": list(k), "probability": burst[k]}
        for k in sorted(set(burst) - set(base))
    ]
    if len(new_burst_events) != 5:
        raise AssertionError(f"expected five deterministic burst DEM events; got {len(new_burst_events)}")
    if common_probability_changes:
        raise AssertionError("burst injection changed probabilities of existing signatures")

    print(json.dumps({
        "stim_version": stim.__version__,
        "decompose_errors": False,
        "approximate_disjoint_errors": True,
        "hamld_parser_module": str(args.hamld_source_root / "src/hamld/contraction_strategy/dem_to_hypergraph.py"),
        "decoder_imported_or_called": False,
        "sampling_called": False,
        "circuit_metadata": circuit_metadata,
        "results": results,
        "new_p01_burst_events_relative_to_p0": new_burst_events,
        "common_event_probability_changes": common_probability_changes,
    }, indent=2))


if __name__ == "__main__":
    main()
