# Correlation-aware decoding: mechanism audit

## Scope and evidence

This is a read-only, post-pilot analysis of the 72 saved checkpoints from the 720,000-shot correlation-aware development pilot. It generates no samples and does not change anything under `outputs/correlation_pilot/`. `analyze_saved_pilot.py` recomputes residuals from the saved detector bits, observables, and four predictions, checks root/condition/model-index metadata, and reads the saved Phase 2B DEM and circuit files. It reproduces the saved aggregate errors exactly: **3,532, 3,349, 3,372, and 3,720** in arm order.

The Phase 2B circuit uses categorical `PAULI_CHANNEL_1` and `PAULI_CHANNEL_2` channels at each post-Clifford injection site. One- and two-qubit total fault probabilities are each 0.003; the X:Y:Z one-qubit weights and products for the 15 non-identity two-qubit Pauli pairs follow ratios 10:1:1, 1:1:1, or 1:1:10. Measurement flips are 0.003. The two-qubit Pauli pair is one categorical event, not two independently sampled single-qubit faults. There is no modeled cross-gate correlated noise. The DEM was generated with `decompose_errors=True, approximate_disjoint_errors=True`.

## Direct observations

Across pooled-fixed paired arms, correlation-enabled decoding changed **1,343/720,000 predictions (0.1865%)**. Among changed predictions, the uncorrelated decoder alone failed on 763 shots and the correlated decoder alone failed on 580, a net difference of 183 errors. Every changed binary prediction is necessarily correct for one arm and wrong for the other on that shot; this accounting was recomputed from saved arrays.

The primary equal-stratum correlated-minus-uncorrelated LER difference remains **−0.00025417**, with the frozen root-stratified 95% interval **[−0.00035000, −0.00016250]** and root-cluster sign-flip p=0.000840. The interval does not clear the frozen −0.0002 practical-effect bound. No mechanism-specific test was predeclared; all condition interaction interpretations below are exploratory.

## Immediate algorithmic pathway

For each paired comparison, the stored decoders receive the same detector samples and logical labels. The off/on matchers were built from the same DEM, and the preflight verified equal graph edges, edge weights, detector IDs, and observable/fault IDs. Therefore, the observed on/off prediction changes are attributable to enabling PyMatching's correlation-aware decode behavior on the DEM's retained separator metadata, rather than changing sampled shots, DEM probabilities, matching weights, or labels.

This identifies the *proximate software pathway* but not which separator group or matching path caused a particular correction. The pilot did not save internal matching paths, activated correlation-group IDs, or per-shot likelihood decompositions.

## Root consistency and basis–bias pattern

The same-name combinations—X-memory/X-biased and Z-memory/Z-biased—both worsened. Correlated matching had higher residual LER on 9/12 roots in X-memory/X-biased and 11/12 roots in Z-memory/Z-biased. The other four conditions favored correlation-enabled decoding on 8–12 of 12 roots each. Root-stratified intervals are per-cell and unadjusted; see `STRATUM_METRICS.csv` and `PER_STRATUM_RESULTS.csv` in the pilot.

The two same-name cases are an important mapping control: the pooled fixed index equals the generating-regime index in each case. The pooled and regime-informed predictions are identical in these conditions for both correlation settings. Thus, in these two adverse cases, the outcome is not caused by choosing a different nominal versus regime-informed DEM. It remains possible that the shared DEM is a poor approximation to the categorical circuit distribution.

Descriptively, mean δ was +0.0003333 across the two same-name conditions and −0.0005479 across the other four; the difference of those means is +0.0008813. Because this grouping was highlighted after inspecting results and includes only two conditions in one group, it is not a confirmatory interaction estimate and no post-hoc p-value is presented.

## Syndrome patterns

Prediction-disagreement shots carried a mean 5.13 active detectors (40 detector bits total), versus 0.96 across all shots, where the median syndrome was empty. Disagreement cases were enriched at boundary detector times, as expected for nontrivial decoding events. Both helpful and harmful changes showed this pattern. Their detector-weight profiles overlap substantially; the saved arrays do not reveal a simple syndrome-weight rule separating helpful from harmful changes.

There were 1,137 distinct packed syndromes among 1,343 disagreement occurrences. Thirty-three syndrome signatures appeared with both standard-only and correlation-only logical failures across repeated shots. This demonstrates that the same detector pattern can be associated with both logical outcomes under the stochastic circuit; syndrome-only choice of a correction cannot be expected to succeed on every occurrence.

## Competing explanations

The data support an interaction in the observed pilot, not a settled mechanism. Plausible explanations include basis-dependent logical sensitivity to Pauli composition, correlation-enabled matching choosing a different correction for a small subset of syndromes, distortion from the disjoint-error DEM approximation, and distance-3-specific path degeneracies. See `COMPETING_HYPOTHESES.md` and `DEM_APPROXIMATION_LIMITS.md` for evidence and tests that would separate them.

## Statistical status

The aggregate primary result is the only predeclared comparison. The six per-condition effects, direction counts, syndrome-feature summaries, DEM metadata associations, and same-name grouping are exploratory. The per-condition intervals are root-resampled, but are not simultaneous and do not control selection/multiplicity from examining six conditions. The 12 Holm-adjusted regime-informed comparisons from the original pilot are privileged diagnostics, not tests of the interaction mechanism.
