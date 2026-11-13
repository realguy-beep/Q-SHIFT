# Exact logical-class MAP reference: validation and limits

## Contract

`ExactMAPOracle` is a bounded reference for small independent-Bernoulli detector error models. It exhaustively enumerates fault assignments and sums their probabilities by detector syndrome and logical class, then returns the more probable logical class. It computes logical-class MAP, not a most-likely fault configuration. Ties deterministically select L0=0. The implementation uses log-sum-exp and refuses models with more than `2^20` fault assignments.

## Independent validation performed

The unit test `test_exact_oracle_matches_independent_fraction_enumeration` independently enumerates all 16 assignments of a four-mechanism/two-detector model using Python `Fraction` arithmetic. It checks all four possible syndromes and agrees on all logical-class decisions. Additional exact boundary tests cover probabilities 0 and 1, zero-probability syndromes, a tie, repeated mechanisms, repeated targets that cancel modulo two, one-detector boundary mechanisms, hyperedges, and combinations of mechanisms.

The test reference uses rational arithmetic and does not call the oracle's log-domain routines. This is an independent arithmetic implementation on one exhaustive nontrivial model, plus explicit edge cases; it is not a proof for every possible model. No Q-SHIFT-size oracle call was attempted: 448 mechanisms imply `2^448` assignments and are deliberately outside the oracle's bounded role.

## BP comparison scope

For a three-mechanism tree factor graph, BP and exact MAP agree on all four two-detector syndromes. This validates that simple tree case only. It does not establish loopy BP correctness on the Q-SHIFT graph. The Q-SHIFT deterministic benchmark reports prediction agreement with PyMatching on five hand-selected rows, not agreement with MAP or truth labels. Those five rows are not an accuracy estimate.

Reproduce with:

```powershell
python -m unittest -v test_decoder_prototypes
```
