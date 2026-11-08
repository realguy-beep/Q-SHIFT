# Stage 5 final statistical repair and readiness

## Decision: GO for readiness; sampling is not authorized

The n=1,210 Stage 5 design is ready for a separate sampling authorization under the conditional statistical scope below. All prespecified statistical checks passed, the independent replay matched, and the frozen no-sampling preflight passed. This GO is not permission to sample: STAGE5_PRETEST_FREEZE_V2.json records PRETEST_FROZEN_NOT_AUTHORIZED, the runner requires both explicit flags, and zero Stage 5 evaluation shots were generated.

## Statistical decision

The primary Endpoint B remains unchanged: the equal-weight mean of the four nonzero-condition paired root LER differences, tested against the practical boundary -0.0002 at planning effect -0.0003, with 1,210 roots per each of five conditions. The separate p=0 no-harm procedure and all original primary critical values remain intact.

The original condition-level Student-t/Welch p-values followed by Holm were anti-conservative under right-skew and tied/asymmetric root effects. The highest complete-null familywise error was 9.3815%, exceeding the frozen 5.2% upper-bound criterion. Holm cannot correct invalid marginal p-values. The prospective replacement uses a studentized root-mean statistic and the maximum upper empirical CDF over six predeclared shape families, with a six-way DKW correction and a right-continuous tie rule. Holm is then applied to four conservative p-values. The unconditional familywise bound is at most 0.051 on the finite family envelope; this is not distribution-free.

The 200,000-replicate-per-cell repaired validation passed all 192 marginal size cells, 516 complete/partial-null FWER cells, and 12 simultaneous coverage cells. Worst marginal simultaneous Wilson upper bound was 0.050316 (allowed up to 0.052 at alpha 0.05); worst FWER upper bound was 0.050444; minimum simultaneous coverage lower bound was 0.957419 (required at least 0.94). The independent replay regenerated six reference fingerprints and matched all 744 simulation cell counts. The independent interval auditor recomputed all saved Wilson intervals from successes/trials, including all 144 reported power rates.

The earlier primary n=1,210 design audit remains PASS. Its 2x sensitivity includes zero-inflated power of 82.440% at -0.0003 (95% Wilson interval 82.203%-82.675%); the weakest primary 2x case was right-skew lognormal at 80.703% (80.457%-80.946%). Secondary power is descriptive with no frozen minimum: its weakest cell is 74.882% at 2x right-skew lognormal and -0.0003.

## Frozen allocation and preflight

If separately authorized, the experiment uses 6,050 roots, 12,100,000 detector-only calibration shots, and 15,125,000 paired evaluation shots, totaling 27,225,000 unique shots. The sample seed inventory contains 12,100 unique streams from namespace 14,000,000,001-14,000,012,100, screened against 11,464 distinct recoverable historical integer values in 25 nonsealed metadata files with zero collisions. Undocumented historical RNG use cannot be ruled out.

The v2 pre-test freeze binds 53 protocol, source, configuration, test, seed and historical-evidence files. Historical Stage 5 v2 and n=1,210 design hashes were checked before creating it. STAGE5_NO_SAMPLING_PREFLIGHT_V2.json records PASS after 253.35 seconds: all five circuit/DEM/matching constructions had 40 detectors and one observable; graph edge counts were 142 at zero burst and 147 at each nonzero burst setting. The preflight process used 45,142,016 bytes RSS; available RAM was 7,094,747,136 bytes and free disk was 275,136,548,864 bytes. It did not call a Stim sampler.

Environment recorded for the preflight: Python 3.12.10, Stim 1.16.0, PyMatching 2.4.0, NumPy 2.5.3, SciPy 1.18.1, and psutil 7.2.2. The combined unittest discovery command passed 19 tests; the separately repeated v2-only command passed 4 tests. Both commands are recorded in the evidence manifest and REPRODUCE_V2.md.

The runner enforces a two-hour cumulative runtime limit, a 2 GiB RSS limit, a 512 MiB free-disk reserve, and the exact shot cap. Current disk space comfortably exceeds the uncompressed array upper estimate of about 1.15 GB. Full Stage 5 sampler throughput was not benchmarked, so completion within the two-hour cap is not guaranteed; the runner checkpoints by root and stops at its enforced limit.

## Independent-test boundary and preservation

- Stage 5 shots generated in this task: 0.
- Sealed historical test outcomes opened or sampled: No.
- Stage 4C or historical Stage 5 results modified: No.
- Website worktree modified: No.
- Earlier failed secondary-inference audits and the blocked initial v1 pretest freeze remain preserved. A hash check confirmed all 45 v1 source hashes were intact; that runner stopped only because the freeze status label did not match its required status. The correction to an inaccurate sentence in the v1 blocking note is recorded in PRETEST_FREEZE_V1_REVIEW_ADDENDUM.md.

## Required next action

Stage 5 sampling requires the user's separate explicit authorization of the frozen v2 experiment. Do not invoke the runner with both --run and --authorize-stage5-sampling until that authorization is given.
