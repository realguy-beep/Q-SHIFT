# Computational Feasibility

## Exact likelihood enumeration

The audited d=3, five-round circuit has 40 one-qubit categorical gate-noise targets, 120 two-qubit categorical Pauli-pair events, and 49 measurement-flip targets. Before parity-equivalent histories are combined, naive enumeration has up to `4^40 × 16^120 × 2^49 = 2^609` event-outcome assignments. Full-circuit exact enumeration is infeasible. The exact calculator in `exact_toy.py` is intentionally limited to small finite examples.

An exact factor-graph contraction or variable-elimination decoder could exploit parity structure, but would require a separately validated circuit factorization and width/cost analysis. This pilot does not implement or claim such a solver.

## Pilot compute and storage

- 360,000 development shots (60,000 for each of six memory/regime cells).
- 60,000 independent calibration shots.
- 120,000 paired pilot shots across 24 roots.
- Six 128-tree forests; combined fitting time was 12.79 seconds. The prepare command completed in 22.0 seconds.
- The full pilot runner completed in 12.4 seconds wall time. Recorded decoder prediction calls totalled 4.43 seconds.
- Mean inference time was about 0.94–1.00 microseconds per shot for an individual PyMatching model and 11.26–11.53 microseconds per shot for an individual forest probability prediction (about 11–12× the matching call in this run). Hardware/software and batching affect these timings.
- Forest files range from 0.98 to 1.66 MB each. Combined forest storage is about 8.6 MB. PyMatching graphs are represented by the six frozen DEM files; process-level resident memory includes the Python, NumPy, Stim, sklearn and all loaded candidates.
- Process working set was 188.1 MB before fitting, peaked at 217.6 MB during model fitting, and was 215.9 MB after pilot inference. This is a coarse process measurement, not an isolated decoder allocation.

## Interpretation

The sample-trained posterior surrogate is computationally practical at this code size, but slower and substantially less accurate than the approximate-DEM matching baseline. Its measured posterior scores are informative but not sufficiently calibrated at the MAP threshold to serve as a stronger reference. A more exact circuit likelihood algorithm is not justified for a new held-out study until its predictive quality exceeds the current baseline on development data.
