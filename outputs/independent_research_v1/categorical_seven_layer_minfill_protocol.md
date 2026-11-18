# Min-fill ordering challenge for the exact seven-layer posterior

## Question

Was the natural detector order's maximum tensor-train rank 91 an ordering artifact for the exact seven-layer P/Z posterior, or does a deterministic graph-informed order also miss the prior rank-64 / 1e-10 gate?

## Frozen method

Reconstruct the same exact 20-bit P and signed Z arrays from the hash-verified seven-layer event map. Build the detector primal graph by making the detector bits in each nonzero event signature a clique. Repeatedly eliminate the remaining detector with lexicographically smallest `(missing neighbor edges, current degree, compact detector ID)`, filling its neighbors into a clique. Use this single elimination sequence directly as the tensor axis order for both arrays. At each cut, compute exact SVD singular values and report the numerical rank and relative-Frobenius ranks at 1e-6 and 1e-10. Compare with the already saved natural order; do not try alternative/reversed orders or tune the heuristic after seeing ranks.

## Gates and scope

Require the event-map hash and exact P/Z invariants to pass. If the maximum matrix dimension, runtime, or memory exceeds the prior audit caps (1,048,576; 300s; 1 GiB), stop. The ordering hypothesis advances only if both P and Z have rank <=64 at every cut at 1e-10 relative Frobenius error. This is deterministic reanalysis of the same exact tail and yields no new circuit samples, full-circuit result, or novelty claim.
