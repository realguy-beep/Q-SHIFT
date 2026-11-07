# Prospective follow-up: Is the basis–bias interaction a DEM approximation effect?

**Status:** This is a bounded, prospective design derived from the saved pilot. No follow-up shots have been generated. The protocol text and this package will be hash-recorded; before any sampling, a separate pre-test freeze must include the validated circuit/DEM implementation, full seed scan, runner, and analysis code. Any change after that freeze requires a new freeze before sampling.

## Scientific question

Does the observed difference between correlation-enabled and correlation-disabled PyMatching in the two same-name basis/bias cells, versus the other four cells, depend materially on Stim's `approximate_disjoint_errors=True` conversion of categorical Pauli channels?

The study distinguishes (a) an interaction that persists under a validated non-approximated disjoint-error conversion from (b) an interaction that changes when the DEM conversion changes. It does not claim an exact likelihood decoder or establish a physical hardware mechanism.

## Circuits and noise

Use the Phase 2B Stim generator, distance 3, five rounds, X- and Z-memory, 40 detector bits, one logical observable. Conditions, in fixed order:

1. X-memory / X-biased.
2. X-memory / balanced.
3. X-memory / Z-biased.
4. Z-memory / X-biased.
5. Z-memory / balanced.
6. Z-memory / Z-biased.

Keep 1Q and 2Q total categorical gate-fault probabilities at 0.003; measurement flip probability at 0.003; Pauli ratios X:Y:Z at 10:1:1, 1:1:1, and 1:1:10. Keep the same Stim circuit and injection locations. Build two DEM families: **A** `decompose_errors=True, approximate_disjoint_errors=True` (pilot reproduction); **B** `decompose_errors=True, approximate_disjoint_errors=False` (non-approximated disjoint-event conversion, only if supported and validated). Do not call family B “exact” merely because the flag is false.

### Mandatory no-sampling model gate

Before any new shot generation, build all 12 DEMs and graph models deterministically. Family B must construct for every basis/regime, preserve detector and observable definitions, retain valid error probabilities/correlation separators, and construct PyMatching-compatible graphs. A model audit must confirm that the change is specifically the disjoint-error conversion, not a changed circuit or noise insertion. If any B model fails or its semantics cannot be verified, stop; do not launch a reduced substitute under this protocol.

## Decoder arms and selection

Within each DEM family and memory basis, build the three regime-indexed model candidates. On independent calibration samples only, choose a single pooled model index by minimizing the equal-weight mean logical error across all three generating regimes; ties use the lowest bank index. Use the same selected index for correlation-off and correlation-on, so their paired contrast changes only the correlation option. Preserve the Phase 2B indices (X index 0, Z index 2) as a locked legacy reference.

For each DEM family, evaluate four decoder outputs on the same sampled detector shots:

- pooled calibration-selected, correlations disabled;
- the same pooled DEM, correlations enabled;
- regime-informed DEM, correlations disabled (privileged diagnostic);
- the same regime-informed DEM, correlations enabled (privileged diagnostic).

This yields eight predictions per test shot across two DEM families. The regime-informed arms may use the known generating condition only as an offline upper-reference diagnostic; no adaptive policy is tested.

## Data partitions and candidate seeds

Per stratum, proposed independent streams are:

- Calibration: 20 roots × 10,000 shots = 1,200,000 total shots.
- Validation: 10 roots × 10,000 shots = 600,000 total shots.
- Final paired test: 60 roots × 20,000 shots = 7,200,000 total test shots.
- Total generated: 9,000,000 samples across the six strata.

Each root's detector/observable sample is decoded by all eight arms. Calibration labels choose pooled indices; validation estimates ranking stability and checks implementation; neither can be used to alter analysis rules after the protocol freeze. Final test labels are opened only after model/seed/source hashes and analysis code are frozen.

Proposed seed formulas (not yet screened, and not historical frozen seeds): for stratum `s=0..5` and root `r`, `seed = stream_base + 100*s + r`. Bases: calibration `120000001` with r=0..19; validation `130000001` with r=0..9; test `140000001` with r=0..59. Diagnostic seed `150000003`, bootstrap seed `150000001`, sign-flip seed `150000002`. Before freezing, scan every proposed value against all recoverable Phase 2A–5, headroom, Phase 2B, and correlation-pilot seed records. If any collision exists, select and document new bases before sampling. Do not claim disjointness until that scan passes.

## Endpoints and statistics

For each stratum `s` and DEM family `m`, define paired `δ(s,m) = LER(correlation-on) − LER(correlation-off)` using the same test shots. Define the post-pilot mechanism interaction:

`I(m) = mean(δ over X/X and Z/Z) − mean(δ over the other four cells)`.

Primary endpoint: `G = I(approximate) − I(non-approximated)`. Positive G means the approximate DEM increases the same-name-vs-other-cell contrast. The practical interaction margin is **0.0002 absolute LER**, matching the prior pilot threshold.

- Primary 95% CI: stratified root-cluster percentile bootstrap with 50,000 resamples; resample roots within each of the six fixed strata and reuse each sampled root index for all paired arms and both DEM families.
- Primary two-sided root-cluster sign-flip test of G=0: 100,000 Monte Carlo assignments, independent signs at root level within strata, weighted by the fixed interaction coefficients, add-one p-value.
- Report `I(approximate)`, `I(non-approximated)`, and G with CIs. Treat only G as the primary test. Six cell-specific DEM-family contrasts are secondary and Holm-adjusted as one family. No per-cell selection or retuning.
- Evidence that approximation materially amplifies the interaction requires G≥+0.0002 and the primary 95% CI lower bound >0. A sign-reversed or inconclusive interval is reported as such. If `I(non-approximated)` remains positive, describe it as persistence under this alternative conversion, not proof of a physical cause.

## Sample-size justification

The saved pilot supplies a paired-disagreement rate of 1,343/720,000 = 0.001865 overall, with per-cell rates 0.000717–0.003217, and 12-root standard deviations of paired LER differences. For the fixed interaction coefficients (+0.5 in each same-name cell, −0.25 in each other cell), the estimated variance coefficient for one DEM family's interaction was 9.776×10⁻⁸ LER² per root count at the pilot's 10,000 shots/root. For planning only, assume equal variance in the second DEM family and zero covariance between family-specific interaction estimates; this doubles the coefficient. At 60 roots/stratum, the resulting approximate SE is 0.0000571 and 95% half-width 0.000112; under a normal planning approximation this is about 94% power to detect G=0.0002 at two-sided α=0.05. This is **not a guaranteed upper bound on variance** because family covariance and the alternate DEM's variance are unknown. It is based on only 12 pilot roots. The 20,000-shot roots may reduce shot noise, but no reduction is credited. Before the final freeze, use calibration/validation-only evidence to check the assumed variance; if the implied power is below 90% at the 0.0002 margin, stop before final test sampling and revise the prospective protocol. Never use final test outcomes for sample-size changes.

## Compute and storage budget

The pilot measured about 3.05 seconds for 720,000 shots with four decoder outputs. Linear scaling suggests roughly 60 seconds for 7.2 million test shots with eight outputs; calibration, validation, and more expensive alternate DEM models add uncertain overhead. The execution allowance is **15 CPU minutes**, with a small benchmark before full sampling. The eight byte predictions plus five packed detector bytes and one observable byte require at most about 101 MB uncompressed for test evidence; calibration/validation detector+label bundles add about 11 MB. Reserve a **1 GB** directory budget for compression overhead, metadata, checkpoints, and reports. Abort before test sampling if benchmark extrapolation exceeds either bound.

## Interpretation and limits

This design tests whether a basis/bias interaction is associated with the DEM conversion approximation in this d=3, five-round circuit. It does not test distance scaling, coherent/crosstalk noise, a deployable adaptive decoder, or hardware. If the non-approximated DEM cannot be validated, this mechanism question remains unanswered; a native-channel posterior decoder would require a separately reviewed protocol.
