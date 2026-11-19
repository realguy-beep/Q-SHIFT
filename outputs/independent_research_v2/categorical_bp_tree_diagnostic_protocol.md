# Categorical Bethe inference: tree exactness diagnostic

## Question

Is the large posterior error in the existing loopy categorical Bethe prototype caused by a general message/partition implementation defect, or is exactness preserved on a nontrivial tree and lost on loopy fixtures as Bethe theory predicts?

## Design

- Use exact exhaustive enumeration on three deterministic fixtures: a three-location factor-graph tree, the existing one-qubit repetition toy, and the existing two-qubit repetition toy.
- The tree has three binary locations and two parity checks. Its nontrivial factor graph is the path C—detector—A—logical—B; compare both conditional logical posteriors, MAP risk, convergence, and iterations.
- For the two loopy fixtures, compare the maximum absolute conditional logical-posterior error and MAP risk/decisions against the existing exhaustive reference. Do not change or tune the BP implementation.
- No stochastic samples or Q-SHIFT circuit experiments. This is a deterministic code/algorithm diagnostic, not decoder efficacy evidence.

## Stop rule and interpretation

The diagnostic is complete after all exact fixture values are recomputed. Agreement on the tree and divergence only on cyclic fixtures supports approximation/topology error as the explanation; disagreement on the tree would trigger a code audit before any method redesign. Neither outcome supports circuit evaluation.

## Reproduction

```bash
MPLCONFIGDIR=/tmp/qshift-mpl ./.venv/bin/python outputs/independent_research_v2/categorical_bp_tree_diagnostic.py
```
