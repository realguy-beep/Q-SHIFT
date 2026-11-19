# Categorical Bethe prototype is exact on a tree and miscalibrated on loopy toys

## Question

The categorical Bethe prototype performed poorly on one exact toy. This diagnostic separated a broad message/partition implementation error from the expected limitations of Bethe approximation on cyclic graphs, using an exactly enumerable nontrivial tree and the existing loopy toy circuits.

## Findings

- **Nontrivial tree:** three binary locations with factor graph path C—detector—A—logical—B. For both syndromes, Bethe conditional logical probabilities matched exhaustive enumeration to maximum absolute error 2.22e-16. All runs converged in one iteration; exact and Bethe MAP risk were both 0.26, with no decision disagreement.
- **One-qubit loopy toy:** exact MAP risk .002646, Bethe MAP risk .057354, two of four syndrome decisions disagreed, and maximum conditional posterior error was .56594. BP reported convergence, showing convergence alone is not an accuracy guarantee.
- **Two-qubit loopy toy:** exact MAP decisions happened to match in all four syndromes and risk was .06, but maximum conditional posterior error was .26000. Matching the MAP on this toy does not establish calibrated logical-class probabilities.

The tree result is consistent with the implementation's message and Bethe-partition calculations being correct on an acyclic factor graph. The severe one-qubit error is therefore likely tied to loopy approximation/topology rather than a general implementation defect. This is a targeted diagnostic, not a proof for every model or factor graph.

## Decision

Keep the generic loopy Bethe decoder stopped before circuit evaluation. Its tree exactness control passes, but its loopy posterior can be badly wrong despite convergence. A viable redesign needs loop correction or bounded exact regions, then must pass multiple small exact cyclic fixtures before any circuit-level test. No tuning was done.

## Scope and reproduction

No stochastic samples or Q-SHIFT circuit samples were generated. The exhaustive counts, per-syndrome posterior comparisons, runtime inputs, and script hash are in `categorical_bp_tree_diagnostic_results.json`.

```bash
MPLCONFIGDIR=/tmp/qshift-mpl ./.venv/bin/python outputs/independent_research_v2/categorical_bp_tree_diagnostic.py
```
