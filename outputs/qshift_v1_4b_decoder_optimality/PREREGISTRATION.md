# V1.4B pre-registration: decoder-optimality screen (development only)

Committed **before** any screen statistics were computed. The only prior look was one root (V1.3 `eval_q2_r00`, 4,000 shots), used to time the exact decoder. On that root the errors were: exact true-q decoder 25, Boff 33, BoffStatic 33, Astar 69. That single-root look is disclosed here and is not part of any decision.

## Data roles (all already exposed; none is independent confirmation)

| Set | Source | Role |
|---|---|---|
| **S1** | V1.3 `pilot_runs/attempt_001` evaluation: 72 roots × 4,000 = 288,000 shots, with saved Astar/A2sw/Boff/BoffStatic predictions and per-root q̂ | Primary screen and residual diagnosis |
| **S2** | V1.2 `pilot_runs/attempt_001` evaluation: 288,000 shots, which were used for V1.3's baseline selection | Replication check (direction only) |

Any later confirmatory experiment must use **fresh seeds**. S1 and S2 will never be described as independent evidence.

## Decoders

- **R_true** (diagnostic reference, privileged): `mld.ExactLogicalDecoder` on the non-decomposed DEM at the true q. This is exact logical-class (maximum-likelihood) decoding *for the DEM*. The DEM itself approximates each categorical PAULI_CHANNEL_2 as independent mechanisms (`approximate_disjoint_errors=True`). It is called "DEM-exact", never "optimal" or "oracle".
- **Candidate A**, mask marginalization: Boff's cost-consistent options (32 masks), with each logical class scored by log-sum-exp over the masks predicting it. The prior is the per-root q̂.
- **Candidate B**, joint exact inference: `ExactLogicalDecoder` on the DEM at the per-root detector-only q̂. Deployable.
- **Candidate C**, a practical approximation: to be specified in `WORKLOG.md`, *after* the residual diagnosis and *before* its own screen run.

## Metrics

- Equal-weight nonzero LER over q ∈ {0.01, 0.02}.
- Root-paired differences, with 20,000 root-stratified bootstrap replicates and a fixed seed (20261116), as in V1.2/V1.3.
- q=0 LER, reported separately.
- Cost in ms/shot on this machine (Python/NumPy).

## Decision thresholds (prospective)

The comparator is **best-V1.3**, whichever of {Boff, BoffStatic} has the lower S1 nonzero LER.

- **Headroom check:** if R_true's nonzero LER is less than 10% (relative) below best-V1.3 on S1, the result is **STOP** (little remaining headroom), regardless of the candidates.
- **GO** for a fresh, separately authorized bounded experiment needs one deployable candidate (A, B or C) to meet all of:
  1. at least 10% relative nonzero-LER reduction vs best-V1.3 on S1;
  2. a root-paired 95% CI of the difference entirely below 0;
  3. q=0 LER no more than 0.05 pp above Boff's;
  4. a cost of at most 50 ms/shot;
  5. on S2, the same direction with at least 5% relative reduction vs the S2 equivalent of best-V1.3, recomputed.
- **REVISE:** the headroom check passes, but no candidate meets all of 1–5.
- **STOP:** the headroom check fails, or every candidate is non-improving or prohibitively costly.

These thresholds are not optimized for any percentage target. They mark what counts as a meaningful, replicating development improvement.
