# Decomposition diagnosis

## The two-qubit example

The toy DEM has two detectors, one logical observable, and six independent Bernoulli mechanisms. Two mechanisms contain a separator; the complete event `D0 L0 ^ D1` has total parity mask `error(0.03) D0 L0 ^ D1`. The exact enumerator treats each complete line as one event: it either occurs with its stated probability or does not. The separator partitions a *suggested graph decomposition*; it is not a second independent random event.

The matching graph imported from the separator-bearing DEM has two detector nodes and two boundary edges; the graph has no direct `D0`–`D1` logical edge for the relevant combined event. The resulting standard and correlation-enabled PyMatching predictions are identical on this toy. At syndrome 11, exact categorical MAP selects logical flip 1, whereas the separator-bearing matching graph predicts 0. Across the full distribution that yields risk 0.1128 rather than 0.0600. Correlation-enabled matching does not repair this particular decision.

Replacing the single complete event with a single graph edge `D0 D1 L0` preserves its Bernoulli probability and complete detector/logical mask in this two-detector case. This changes the graph presented to matching: the exact risk 0.0600 is recovered. This is a valid representation for this graphlike event, not evidence that all separator hints should be erased.

## Generalization boundary

The pattern recurs in a deterministic 64-point family built from the same 2-detector graphlike motif: valid separator-free matching has lower exact risk in 59/64 cells, ties in 5/64, and is worse in 0/64. This is a structured family, not a random sample of Stim circuits. In the eight independent categorical chain toys, standard matching differs from exact MAP in 1–3 of four syndromes per case; separator-free matching reduces, but does not always eliminate, the disagreement. The two-decoder equivalence across a case does not establish equivalence in general.

The four-detector alternative-decomposition fixtures preserve the same full event distribution while changing the proposed partition. Standard/correlated matching can give different decisions for a changed partition. Candidate A rejects both because the complete event has four detector symptoms. Unchecked removal is only a diagnostic and is not a valid candidate method.

## Interpretation

The failure generalizes as **representation sensitivity in selected small graphlike cases**, not as a universal PyMatching defect or a universal benefit of separator removal. A separated DEM carries a decomposition hint that helps represent a hyperedge/correlated mechanism as graph components. Matching then optimizes under its graph construction and correlation procedure; that is not identical to exact summation over all logical classes. No software bug was demonstrated.
