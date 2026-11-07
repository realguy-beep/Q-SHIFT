# Controlled categorical toy variants

The original two-qubit toy remains the primary diagnostic. Supporting variations were enumerated analytically over all four syndromes; no stochastic samples were used.

## Fixed-marginal, fixed-total correlation perturbation

To change within-gate Pauli-pair correlation without changing single-qubit Pauli marginals or total two-qubit fault probability, a 2x2 cycle was applied:

`P(XX)+=delta`, `P(XY)-=delta`, `P(YX)-=delta`, `P(YY)+=delta`, with `delta=0.004*alpha` and `alpha` in `{-1,-0.5,0,0.5,1}`.

Every probability table remains a valid 16-outcome categorical draw, including identity `II`; both qubit marginals, `P(II)=0.88`, and total nonidentity mass 0.12 remain fixed. Across all five values, the exact MAP decisions stay `(s=00,01,10,11) -> (0,0,0,1)`, while both PyMatching modes using the generated separator DEM stay `(0,0,0,0)`. Exact risk stays 0.0600 and PyMatching risk stays 0.1128. Thus this one controlled correlation direction does not explain the original mismatch.

## Product-of-marginals mixture (exploratory, confounded)

An earlier supporting sweep interpolated the joint channel toward the product of its single-qubit marginals. The local draw remained categorical, and the marginals stayed fixed, but `P(II)` changed from 0.88 to 0.800944; total nonidentity probability rose from 0.12 to 0.199056. Exact risk decreased from 0.0600 to 0.016324, while the generated approximate-DEM PyMatching risk increased from 0.1128 to 0.200152. Because the total pair-fault probability changes, this sweep is not used to attribute the primary discrepancy. It is retained as a warning about confounding in naive “correlation removal” comparisons.

## Separator-only decoder-input ablation

This is the decisive controlled test: preserve the six independent DEM mechanisms and their exact event parity masks, but remove only the `^` decomposition hints when constructing a graphlike DEM representation. Exact independent-DEM posteriors match exactly. PyMatching's syndrome-11 output changes from 0 to 1 in both modes, restoring agreement with exact MAP. This changes decoder graph construction, not the fault channel. Full data are in `SEPARATOR_ABLATION.json`.

