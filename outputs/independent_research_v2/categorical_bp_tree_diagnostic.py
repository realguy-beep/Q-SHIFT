"""Deterministic exactness diagnostic for categorical Bethe sum-product."""
from __future__ import annotations

import hashlib
import json
import platform
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "outputs/independent_research_v1"))
sys.path.insert(0, str(ROOT / "outputs/categorical_decoder_feasibility"))

from categorical_bp import logical_one_probability
from categorical_reference import (
    CategoricalLocation, CategoricalModel, FaultOutcome, decoder_risk, exact_posterior,
)
from toy_circuits import one_qubit_model, two_qubit_model


def evaluate(name: str, model: CategoricalModel, topology: str) -> dict:
    exact = exact_posterior(model)
    decisions = {}
    rows = []
    for syndrome, posterior in exact.conditional.items():
        result = logical_one_probability(model, syndrome)
        decisions[syndrome] = int(result.logical_one_probability > 0.5)
        rows.append({
            "syndrome": syndrome,
            "exact_probability_logical_one": posterior[1],
            "bethe_probability_logical_one": result.logical_one_probability,
            "absolute_probability_error": abs(posterior[1] - result.logical_one_probability),
            "exact_map": exact.decisions[syndrome],
            "bethe_map": decisions[syndrome],
            "iterations": result.iterations,
            "converged": result.converged,
        })
    return {
        "name": name,
        "factor_graph_topology": topology,
        "configuration_count": exact.configuration_count,
        "syndrome_count": len(rows),
        "exact_map_risk": exact.logical_error_probability,
        "bethe_map_risk": decoder_risk(exact.joint, decisions),
        "map_decision_disagreements": sum(r["exact_map"] != r["bethe_map"] for r in rows),
        "max_absolute_conditional_posterior_error": max(r["absolute_probability_error"] for r in rows),
        "all_bp_runs_converged": all(r["converged"] for r in rows),
        "syndromes": rows,
    }


def main() -> None:
    tree = CategoricalModel(1, 1, (
        CategoricalLocation("A", (
            FaultOutcome("I", 0.7, 0, 0), FaultOutcome("X", 0.3, 1, 1),
        ), "I"),
        CategoricalLocation("B", (
            FaultOutcome("I", 0.8, 0, 0), FaultOutcome("X", 0.2, 0, 1),
        ), "I"),
        CategoricalLocation("C", (
            FaultOutcome("I", 0.9, 0, 0), FaultOutcome("X", 0.1, 1, 0),
        ), "I"),
    ))
    fixtures = [
        evaluate("nontrivial_tree", tree, "path C—detector—A—logical—B"),
        evaluate("one_qubit_repetition", one_qubit_model(), "loopy"),
        evaluate("two_qubit_repetition", two_qubit_model(), "loopy"),
    ]
    payload = {
        "status": "completed_deterministic_exactness_diagnostic",
        "fixtures": fixtures,
        "unique_stochastic_samples": 0,
        "unique_qshift_circuit_samples": 0,
        "software_versions": {"python": platform.python_version()},
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "scope": "exact toy enumeration for algorithm diagnosis; no circuit efficacy claim",
    }
    output = HERE / "categorical_bp_tree_diagnostic_results.json"
    output.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({
        "fixtures": [{key: row[key] for key in (
            "name", "factor_graph_topology", "exact_map_risk", "bethe_map_risk",
            "map_decision_disagreements", "max_absolute_conditional_posterior_error",
            "all_bp_runs_converged")}
            for row in fixtures],
        "unique_stochastic_samples": 0,
    }, indent=2))


if __name__ == "__main__":
    main()
