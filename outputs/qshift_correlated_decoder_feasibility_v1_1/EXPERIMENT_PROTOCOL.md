# Correlated decoder feasibility V1.1 protocol

**Status:** prospective, single bounded development-only evaluation. This is not independent confirmation and does not authorize Stage 5 access or follow-up sampling.

## Repair and evidence lineage

V1 stopped after 3,000 training and 15,000 calibration shots, before evaluation. Its affine fit assigned NumPy's `polyfit` output in the wrong order: NumPy returns `[slope, intercept]`, while the V1 code stored `(intercept, slope)`. V1.1 corrects this in a new source file and pins a regression test that fails under the reversed assignment. A corrected-algebra inspection had already occurred after the V1 failure; that inspection is disclosed as prior development exposure. The original V1 code, freeze, run, 33 archives, and reports remain unchanged.

V1.1 first verifies all 33 preserved archives against both V1's status manifest and failed-attempt evidence manifest, including byte counts, seed-to-partition mappings, and the original source/freeze identities. The verifier inspects only archive bytes and ZIP member names; it does not load array values. V1.1 then loads **only** the `detectors` member from the three training and 30 calibration archives. Stored V1 observables are not read or copied. Their prior presence in the historical archives remains a disclosed retention deviation. V1 had zero evaluation sampler calls, no evaluation archives, and no evaluation outcomes.

## Frozen candidate and decoder arms

Retain the V1 circuit unchanged: balanced rotated distance-3 Z-memory, five rounds, gate and measurement probabilities 0.003, with independent synthetic `CORRELATED_ERROR(q) X8 X12 X15` events immediately after each of five `MR` boundaries. The candidate conditions remain `q={0,0.01,0.02}`. These are synthetic common-cause events, not a calibrated hardware noise process.

The detector-only estimator fits the mean of five three-detector cofire indicators against known q values using the V1 training detector rows and training partition metadata only. The repaired assignment is `(slope, intercept) = polyfit(...)`; estimates are clipped to `[0,0.02]`.

- **A:** one global correlation-aware PyMatching model based on a single detector-only estimate from all 15,000 calibration detector rows pooled across conditions.
- **A2:** correlation-aware PyMatching configured from each matching 500-row root calibration detector batch.
- **B:** the V1 five-factor enumeration decoder configured from the same per-root detector-only estimate as A2, with background matching. This is a finite-factor hybrid, not exact whole-circuit maximum likelihood.
- **C:** the same five-factor reference configured with the true simulated q. C is privileged and is not deployable.

A and A2/B have intentionally different calibration aggregation scopes fixed by V1: A uses the pooled calibration batch for one global profile, while A2 and B share the matched root batch. C alone receives true q. All evaluation arms receive the identical detector array per root. No decoder receives logical labels.

For execution efficiency, B and C may share the deterministic PyMatching results for their identical 32 residual syndromes. A regression test compares these paired outputs bit-for-bit against separate B and C decoding calls, including q=0. This reuses computation only; each arm's candidate cost and q-specific prior remain unchanged. Paired B/C wall time is reported as a shared component rather than misattributed as independent per-arm time.

## Reuse and new allocation

Reuse the already generated V1 detector arrays: 3,000 training and 15,000 calibration shots. They are not regenerated. Generate only 60,000 new paired evaluation shots: ten roots at each of three q values, 2,000 shots per root, one sampler call per root (30 calls total). Every evaluation batch is sampled once, passed unchanged to A/A2/B/C, and persisted with all predictions. Predictions for all four arms are completed before the corresponding observable array is accessed for scoring. New evaluation seed identities and two bootstrap stream identities are generated in the V1.1 seed namespace and screened against the V1 inventory (65 values) and the earlier named development inventory (108 values). No Stage 5 or sealed inventory is accessed.

If the corrected training slope is nonpositive, or mean root q-hat values fail the original strict order `q=0 < q=0.01 < q=0.02`, stop before the first evaluation sampler call. No thresholds, q values, or model rules may be adjusted after seeing this gate.

## Endpoints and decision rules

Primary estimand: equal-weight mean over q=0.01 and q=0.02 of root-paired `LER(B)-LER(A)`; negative favors B. Use 20,000 root-stratified paired percentile bootstrap replicates, resampling ten roots with replacement separately within each q and preserving the paired B/A observations for each root. Quantiles use NumPy `method="linear"`; report a two-sided 95% interval.

Zero-burst safety: at q=0 report the one-sided 95th percentile bootstrap upper bound for `LER(B)-LER(A)` against the fixed +0.0005 harm tolerance. Also report lower bound, condition/root results, paired prediction disagreements, B-only/A-only errors, estimation bias/MAE, and A2/C contrasts. These are exploratory or descriptive; no confirmatory claim is made.

Decision rules remain unchanged from V1:

- **GO (development evidence only):** at least 100 A errors pooled over nonzero q; primary interval entirely below zero; B has lower point LER than A in both nonzero conditions; and q=0 one-sided upper bound below +0.0005.
- **NO-GO:** primary interval entirely at or above zero, or q=0 one-sided lower bound above +0.0005.
- **INCONCLUSIVE:** all other cases, including insufficient A errors, an interval crossing zero, calibration-gate failure, or incomplete evidence.

Representation change (B versus A2) is distinct from the combined representation/adaptation comparison (B versus A). A positive result is development evidence only and does not establish superiority on hardware, other noise models, or an independent test.

## Execution and stop controls

Before sampling, commit V1.1 source, tests, config, protocol, seed inventory, verified-reuse manifest, and a pretest source hash freeze. The launch command requires the exact resulting commit SHA, a clean V1.1 branch, valid file hashes, exact dependency versions, and a rerun of the reuse verification. The default runner mode is sampler-free. The only execution path is the Windows watchdog plus one `--execute --expected-head <SHA>` call. Refuse an existing run directory. Cap at 60,000 new shots/30 calls, 600 seconds, sampled current-process RSS high-water of 2 GiB (not hard OS enforcement), at least 1 GiB free disk, and 256 MiB run artifacts. Preserve partial evidence and stop on any failure; no automatic retry, seed substitution, or recovery execution.

The fixed 600-second cap may be insufficient for the five-factor decoder. A deterministic preflight measures model construction and fixture inference and projects the workload conservatively. If that projection exceeds the cap or is too uncertain, stop before sampling. No statistical or performance claim will be derived from this fixture timing.

No Stage 5, sealed-test, or independent-test data are read. This one evaluation cannot trigger a larger experiment automatically.
