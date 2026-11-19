"""Review check for categorical_bp.py (see REVIEW_2026-11-19_categorical_bp_and_cusum.md).

Runs the three fixtures of categorical_bp_tree_diagnostic.py with:
  AS WRITTEN                    outputs/independent_research_v1/categorical_bp.py unchanged
  INDEXING FIXED ONLY           check->variable messages built per parity bit (0, 1), as they are initialised and read
  INDEXING + CONVERGENCE FIXED  additionally, convergence measured over check->variable messages too
The fixes are applied to an in-memory copy; categorical_bp.py on disk is not modified. Deterministic; no sampling.

    python outputs/independent_research_v2/review_categorical_bp_fix_check.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BP = ROOT / "outputs/independent_research_v1/categorical_bp.py"
sys.path.insert(0, str(ROOT / "outputs/independent_research_v1"))
sys.path.insert(0, str(ROOT / "outputs/categorical_decoder_feasibility"))
import categorical_bp as CB  # noqa: E402
from categorical_reference import (CategoricalLocation, CategoricalModel, FaultOutcome,  # noqa: E402
                                   decoder_risk, exact_posterior)
from toy_circuits import one_qubit_model, two_qubit_model  # noqa: E402

SRC = BP.read_text(encoding="utf-8")
CONV_OLD = """        var_to_check = updated_variable
        check_to_var = updated_check
        if largest_change < tolerance:"""
CONV_NEW = """        for key, msg in updated_check.items():
            largest_change = max(largest_change, max(abs(msg[k] - check_to_var[key][k]) for k in range(len(msg))))
        var_to_check = updated_variable
        check_to_var = updated_check
        if largest_change < tolerance:"""
INDEX_OLD = "                for bit in effects[variable][check]:"
INDEX_NEW = "                for bit in (0, 1):"
assert SRC.count(CONV_OLD) == 1 and SRC.count(INDEX_OLD) == 1, "categorical_bp.py changed; review patch no longer applies"


def _variant(src: str, name: str):
    ns: dict = {}
    exec(compile(src, name, "exec"), ns)
    return ns["logical_one_probability"]


VARIANTS = {
    "as_written": CB.logical_one_probability,
    "indexing_fixed_only": _variant(SRC.replace(INDEX_OLD, INDEX_NEW), "categorical_bp_index_fixed"),
    "indexing_and_convergence_fixed": _variant(SRC.replace(INDEX_OLD, INDEX_NEW).replace(CONV_OLD, CONV_NEW),
                                               "categorical_bp_both_fixed"),
}
TREE = CategoricalModel(1, 1, (       # identical to categorical_bp_tree_diagnostic.py
    CategoricalLocation("A", (FaultOutcome("I", 0.7, 0, 0), FaultOutcome("X", 0.3, 1, 1)), "I"),
    CategoricalLocation("B", (FaultOutcome("I", 0.8, 0, 0), FaultOutcome("X", 0.2, 0, 1)), "I"),
    CategoricalLocation("C", (FaultOutcome("I", 0.9, 0, 0), FaultOutcome("X", 0.1, 1, 0)), "I"),
))
FIXTURES = {"nontrivial_tree": TREE, "one_qubit_repetition": one_qubit_model(), "two_qubit_repetition": two_qubit_model()}


def evaluate(model, fn) -> dict:
    ex = exact_posterior(model)
    dec, errs, its, conv = {}, [], [], []
    for s, post in ex.conditional.items():
        r = fn(model, s)
        dec[s] = int(r.logical_one_probability > 0.5)
        errs.append(abs(post[1] - r.logical_one_probability))
        its.append(r.iterations)
        conv.append(r.converged)
    return {"exact_map_risk": ex.logical_error_probability, "bethe_map_risk": decoder_risk(ex.joint, dec),
            "max_abs_posterior_error": max(errs), "iterations": its, "all_converged": all(conv),
            "outcomes_per_location": sorted({len(loc.outcomes) for loc in model.locations})}


def main() -> None:
    out = {v: {f: evaluate(m, fn) for f, m in FIXTURES.items()} for v, fn in VARIANTS.items()}
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
