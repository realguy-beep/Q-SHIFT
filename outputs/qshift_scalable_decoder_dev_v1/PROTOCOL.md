# Scalable correlated decoder development protocol v1

Prospective, deterministic-only development; no evaluation outcomes, sampling, training, sealed data or new dependencies. Source base 257b0b0bdb740d771d731d30c768adb955bda02e. No scientific effect size or accuracy claim is authorized by this stage.

## Question and mechanism

Can bounded sum-product belief propagation (BP) on the undecomposed detector error model preserve each multi-detector mechanism and calculate an approximate logical posterior at d=3, 5 and 7 within fixed resources? Introduce a logical parity factor and infer its marginal jointly with detector parity checks. BP is approximate on loopy graphs; preserve duplicate mechanisms and logical-only faults. Reject unsupported DEM semantics rather than silently decompose. BP+OSD and BeliefMatching need unavailable `ldpc`/`beliefmatching` packages in this interpreter; no install is authorized. Factor-graph BP provides an explicit, inspectable first feasibility step, not a claim of superiority over those methods.

Exact logical-class inference, correlated-noise representation, learned support and rate adaptation are separate contributions. V1.6b combines them against static matching; 61.5% is not an adaptation-specific effect. Its two d=3 synthetic bursts and device-level calibration with 1,500 labeled shots per condition limit generalization. The 900-shot replay and 340 calibration comparisons reused frozen code for core calculations; metadata hashes were observed after the run. Full prediction replay remains unverified.

## Deterministic gate

- Input: preconstructed DEMs; no detector sampler. Conditions q=0 and q=0.01, `scaled_v1` family; distance/rounds (3,5), (5,5), (7,5). Use only analytical syndrome fixtures: all-zero and each of the first five deterministic burst-event supports; no evaluation arrays. Candidate sees the same model as oracle-information PyMatching; d=3 exact DEM decoder is a reference. Logical predictions are not evaluation outcomes.
- BP update: fixed synchronous sum-product iterations, damping 0.5, maximum 50 iterations, numerical clipping 1e-12, convergence tolerance 1e-8. Logical variable has uniform prior and logical parity factor enforces its relationship to faults. Report nonconvergence; never silently claim exactness. Zero-probability syndromes fail closed when detected.
- Unit checks: independent exhaustive toy-model likelihoods including multi-detector events, logical-only events and degeneracy; detector shape/binary validation; DEM representation with separator handling; logical parity and logical dimension; no sampling; compare d=3 BP and frozen exact predictions/posteriors on synthetic fixtures and report all differences. Do not tune after viewing fixture comparisons.
- Resources: local verification total <= 30 minutes, each command <= 10 minutes; fixture subprocess timeout 120 s per distance, peak memory reported as sampled process RSS, not a hard tree limit. Limit per-model variables and edges to 50,000 each; fail closed above limits. Report construction and inference separately. Stop on unsupported mechanism semantics, wrong output shape, invalid posterior, inability to finish within limits, or source integrity failure.
- Decision GO only if tests pass, all six d/q fixtures complete within limits with valid outputs, and d=3 comparison is reported; this is engineering feasibility only. REVISE for bounded nonconvergence, model mismatch, or resource failure; STOP for invalid semantics, leakage or sampling. No advantage is required for engineering GO and no performance superiority is implied.

## Future evaluation outline, not authorized

If engineering GO, propose a separate protocol before sampling: paired decoder observations across matched models; calibrated and static PyMatching, BeliefMatching and BP+OSD if explicitly installed/approved, exact d=3 and small tractable references; equal calibration information and explicit oracle arms. Freeze noise families, independent roots, seeds, samples, LER contrasts, root-stratified uncertainty, zero-noise safety, runtime/memory and failure handling. Reserve separate development/held-out samples and unknown-noise conditions; do not tune using held-out outcomes. d=5/7 performance and budgets require separate resource/power analysis and explicit owner authorization.

## Checklist

☑ Review V1.6b closure and candidate dependency availability.
◐ Commit this protocol before implementation.
☐ Implement bounded BP and deterministic tests.
☐ Run fixtures and report GO / REVISE / STOP.
☐ Commit verified source and results locally.