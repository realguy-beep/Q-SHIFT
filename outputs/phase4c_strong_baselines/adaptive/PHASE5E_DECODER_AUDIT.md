# Phase 5E decoder audit

All nine DEM hashes and edge-weight signatures differ. Phase5D matrices were pooled over regimes inside run_phase5d.py, because the accumulation matrix was initialized outside the regime loop and never reset. Phase5E initializes a separate 9x9 matrix for each regime and checks symmetry and diagonal zero.

IDs #0/#4/#8 show zero disagreement in some sampled regimes, but their graph signatures are distinct; no mathematical equivalence is claimed. IDs #3/#7 and #1/#5 also have distinct graph signatures and nonzero disagreement in at least some regimes.
