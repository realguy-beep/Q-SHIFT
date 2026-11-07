# Exact inference validation

## Toy checks

Three methods were compared on both categorical toys:

1. Cartesian exhaustive fault enumeration from the earlier exact reference.
2. A direct nonnegative XOR-state dynamic program.
3. Walsh-Hadamard XOR convolution over local categorical factors.

Separately, dense tensor variable elimination was run with min-fill and min-degree fault-variable orders on the explicit parity factor graph. Both orders reproduce `P(s,L)`, MAP decisions, tie syndromes, and risk for every syndrome. A second Stim forced-outcome path independently checks all 320 one- and two-qubit toy configurations. The one-qubit exact/MWPM risk is 0.002646; two-qubit categorical exact risk is 0.060000.

Ties within `1e-15` are resolved toward the smallest logical bit pattern. In the two-qubit toy, syndromes 1 and 2 are tied and both exact procedures choose logical bit 0. Tests explicitly validate these ties and all syndrome decisions, including syndrome 11.

## Structured algorithm

Each location induces a sparse distribution over its XOR mask in the group `Z2^(D+O)`. The total output distribution is the XOR convolution of these local distributions. A Walsh-Hadamard transform turns XOR convolution into pointwise multiplication. The implementation groups local transforms by their touched detector/logical coordinates, multiplies factors in frequency space, then applies an inverse transform. It does not enumerate the Cartesian product of fault assignments.

On the one-round Phase 2B fragment, this posterior agrees with a separately implemented nonnegative direct XOR dynamic program for every joint mask to maximum absolute difference `2.11e-15`. The toy comparisons match exhaustive inference. The two- and three-round fragment runs check posterior normalization and nonnegative probabilities up to a recorded tiny floating-point residue; they do not have an independent exhaustive circuit posterior because their fault configuration counts are `2^249` and `2^369`.

## Numerical limits

The implementation uses float64, not symbolic rational arithmetic. The three-round result had raw mass `1.0000000000000056`; the minimum raw cell was `-9.57e-20` from transform cancellation. It clipped total negative residue `2.36e-15`, renormalized to mass `1.0000000000000002`, and continued. This residue is tiny compared with the reported logical risk, but it is recorded rather than hidden. No Monte Carlo error bars apply to these deterministic calculations.

## Elimination orders

On the explicit toy parity graph, min-fill and min-degree orders both reproduced the exhaustive result. The two-qubit toy has induced width 4 and maximum combined factor 2,048 states under both heuristics; the one-qubit toy has width 4 and maximum 256 states. Circuit fragment results also record a separate, fixed XOR-accumulator frontier width of `D+O` bits; this is not the same as the raw primal-graph heuristic width.

