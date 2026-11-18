# Preserved preflight failure: doubled gate-noise shift

The initial run of `fast_flagged_logistic_gate_shift.py` generated only the 60,000 preflight samples (10,000 per six conditions) and then stopped while building the shifted-profile diagnostic DEM. `approximate_disjoint_errors=.0018` was below a shifted PAULI_CHANNEL_2 component probability of .00357143. No main samples were generated and no result gate was evaluated.

The fixed nominal matcher, classifier, and protocol were not changed. The diagnostic graph alone was rebuilt with threshold .004, above the largest shifted component. The rerun uses the same preflight seeds; those trajectories are duplicates and count once toward cumulative unique samples. The separate fresh-stream replication uses its own frozen seeds only if the corrected initial run passes.
