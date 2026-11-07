# Why the two-qubit toy disagrees

## Primary observation

The categorical channel has four possible detector syndromes. At syndrome `11`, the exact categorical posterior is `P(L0=1 | s)=0.9680851064`, so MAP chooses `L0=1`. The approximate-DEM independent-mechanism posterior is `0.9691017201`, and it also chooses 1. Standard and correlation-enabled PyMatching built from the separator-bearing DEM both choose 0.

Across all four syndromes, categorical exact MAP and exact independent-DEM MAP make the same decisions. Both achieve risk 0.0600 when scored against the original categorical channel. Separator-bearing PyMatching makes one of four syndrome decisions differently and has risk 0.1128, a `+0.0528` absolute risk gap on this finite toy.

## Direct mechanism found

The six DEM instructions each have probability 0.03. Two include Stim's `^` decomposition separators. PyMatching's graph exported from this DEM has two detector-to-boundary edges, both with empty observable fault-ID sets and merged edge probability 0.10962552. It has no direct `D0-D1` logical edge. Standard and correlation-enabled decoding both output logical bit 0 for syndrome `11`.

We constructed a controlled graphlike representation that removes only the two separator hints, preserving each of the six Bernoulli probabilities and the total detector/logical parity mask of every event. This representation is accepted by Stim and PyMatching. Exact enumeration confirms that its full independent-DEM posterior is unchanged. The resulting PyMatching graph has a direct `D0-D1` edge carrying logical fault ID 0; both standard and correlation-enabled PyMatching now predict 1 at syndrome `11`, and all four predictions match exact MAP. Its risk on the original categorical channel is 0.0600.

## Attribution

For this toy and this specific syndrome, the mismatch is attributable to the decoder's graph decomposition/inference behavior, not to a categorical-versus-independent-DEM MAP change. The DEM approximation does alter posterior probabilities (see `INDEPENDENT_DEM_POSTERIOR.md`), but it changes none of the four MAP decisions. The observed 0.0528 risk gap disappears when the same independent mechanism distribution is represented without separator decomposition.

This attribution is narrow. It does not prove that PyMatching mishandles all separators, that the edited representation is a recommended general preprocessing rule, or that exact categorical decoding improves a surface code. Correlation-enabled PyMatching is a matching variant, not exact Bayesian marginalization; its prediction matching the standard mode here is an observed result, not an expectation of general equivalence.

The installed PyMatching 2.4.0 decoder was invoked with `enable_correlations=True` at construction and decode time. PyMatching documents this option as a two-pass correlated-matching variant that uses decomposed graphlike hyperedges, not as exact posterior summation; see the [PyMatching API source documentation](https://github.com/oscarhiggott/PyMatching/blob/master/src/pymatching/matching.py).

