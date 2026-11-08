# Secondary Holm validation extension — frozen before its Monte Carlo

This is a separately versioned, prospective design-only validation. It follows completion and independent replay of the primary n=1,210 operating-characteristic simulation. It does not alter any primary result, Stage 5 protocol, target effect, endpoint, or sampling rule.

## Procedure under audit

Audit the exact condition-level secondary procedure already present in the reviewed Stage 5 candidate `outputs/stage5_candidate_v3_n666/stage5_statistics_candidate.py`: one-sided Student-t/Welch reference p-values for each of the four nonzero root-level paired differences against mean zero, with Holm step-down familywise adjustment at alpha=.05. The estimand remains a condition's mean root-paired LER difference. This work does not replace the historical v2 sign-flip procedure or silently amend it; it evaluates the explicit later candidate implementation.

## Operating-characteristic test

At 1,210 independent roots, for each of the ten non-offset distribution/variability cells covering all five families at 1.5× and all five at 2×, draw four independent condition vectors with zero means and the frozen unequal condition SDs. Use 200,000 Monte Carlo family replicates per cell. Compute the same one-sided t-reference p-values as the candidate. Check each marginal p-value against every Holm step threshold `[.0125, .0166666667, .025, .05]`. Also apply the actual four-test Holm algorithm and record complete-null familywise rejection.

The marginal p-value validity checks use simultaneous one-sided Wilson upper bounds over 160 rates (10 scenario cells × 4 conditions × 4 Holm thresholds), with Bonferroni family confidence .95. For each rate, require the bound to be no greater than its Holm threshold + .002, carrying forward the same maximum two-percentage-point-in-the-thousand Monte Carlo tolerance used in the primary size check. Complete-null Holm familywise rates use Bonferroni one-sided Wilson bounds over ten scenario cells and must be ≤.052. These are simulation acceptance criteria for this finite envelope, not mathematical proof or distribution-free guarantees.

The simulation includes skew, heavy tails, and a 65% point mass/tie structure. Ties use the candidate's deterministic p-value comparisons. This validates only the named family models and root-SD estimates. It cannot validate unmodeled root-effect distributions.

## Streams and isolation

All ten PCG64 streams are separately allocated and collision-screened against the explicit nonsealed historical metadata allowlist and the 65 parent design-validation streams. The evaluator uses no Stim, no Stage 5 calibration/evaluation samples, no logical test outcomes, and no sealed-test paths. An independently written auditor replays each stream and independently computes p-value threshold counts, Holm rejections, and simultaneous Wilson bounds.

**No sampling authorization.** Failure of any cell means the secondary family remains unsupported and the Stage 5 readiness decision remains NO-GO. No threshold or method changes are allowed after inspecting these results.
