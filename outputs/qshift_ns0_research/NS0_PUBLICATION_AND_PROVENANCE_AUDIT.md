# NS-0 publication and provenance audit

## Publication record

- Branch: `qshift-ns0-research`
- Published full commit: `fef7f72c9a997c5e6d99c10b59da30dfd6de1127`
- Parent: `5c8f50d00f003f3f79a3d07e00541ad2a3378523` (Phase 3B checkpoint)
- Remote: `origin` = `https://github.com/realguy-beep/Q-SHIFT.git`
- `git ls-remote origin refs/heads/qshift-ns0-research` returned the same full SHA.
- The first push was rejected by GitHub because the unpublished commit metadata used a private Gmail address. Only the local unpublished commit metadata was replaced with the account owner's previously verified GitHub no-reply address. The tree, parent, files and commit message are unchanged. The retry was a normal non-force push. No existing remote commit was rewritten.
- The eight original NS-0 reports remain present and unmodified. No PR or merge was created. Phase 3B and other branches/worktrees were not changed.

## Historical claim trace

The claimed **21.9% reduction remains UNVERIFIED**. A tracked-history search (`git log --all -S "21.9%"` over the available NS-0 and Stage 4 evidence) found no underlying calculation or result record. No Stage 5 material or protected outcomes were accessed.

The nearest traceable result is Stage 4 development evidence in `outputs/stage4_noise_adaptive_development_v1/STAGE4_RESULTS.md`, its `PER_CONDITION_RESULTS.csv`, `PER_ROOT_RESULTS.csv`, `PAIRED_COMPARISONS.csv`, and the frozen `STAGE4_DEVELOPMENT_PROTOCOL.md` / `stage4_development_config.json`:

| Reported quantity | Numerator/denominator | Comparator and decoder | Conditions/weighting |
|---|---:|---|---|
| 22.727% reduction | `(506 − 391)/506` | Detector-profile-estimated burst-aware PyMatching vs fixed nominal `p_burst=0` PyMatching | Four equally sized nonzero conditions `p_burst={.004,.008,.012,.016}`; 70,000 paired evaluation shots total, 7 independent roots per condition |
| 19.661% reduction | `(590 − 474)/590` | Same two deployable-development arms | All five equally sized conditions including `p_burst=0`; 87,500 paired evaluation shots total, 7 roots per condition |

All arms used a distance-3 rotated Z-memory circuit, five rounds, balanced categorical gate noise `p=.003`, measurement flip `p=.003`, and synthetic simultaneous `X8 X10` events at each of five round boundaries. These are **development** outcomes, generated from the original Stim circuit and scored on shared detector/observable rows. The deployable estimator was the existing 45-feature `DetectorProfileEstimator`: 40 detector marginals plus five pair-cofiring features `(8,10),(16,18),(24,26),(32,34),(36,38)`, profiles trained at p `{0,.01,.02}` using three 2,000-shot batches per p, linear interpolation, pooled variance scaling (floor `1e-6`) and a `1e-5` probability grid. Each root-condition then used a separate 2,000-shot detector-only calibration batch to pick `p_hat`; 2,500 distinct paired evaluation shots/root-condition were scored. The report records mean nonzero `p` estimate absolute error `0.000934` and signed bias `+0.000013`. It did not provide independent confirmation. The privileged true-`p` decoder had 476/87,500 errors and is not a deployable comparator.

Analysis was paired at the root level: four-nonzero-condition equal-weight mean, stratified seven-root bootstrap interval, and root-level sign-flip test as specified by the protocol. The reported reduction percentages are descriptive ratios of aggregate/equal-cell error counts; they are not effect estimates for a separate population, independent confirmation, hardware, or proof of general adaptive-decoder benefit. The primary Stage 4 signed LER difference was `−0.00164286` (−0.164286 percentage points) on the four nonzero strata, with 95% root-cluster interval `[−0.00197143, −0.00132857]`; seven roots per stratum limit generalization.

Historical paired discordance, useful only as a planning input: on the 70,000 nonzero Stage 4 shots, the estimated decoder had 30 candidate-only and 145 fixed-only logical failures, so `q=(30+145)/70000=0.0025`. This is development-specific, not an assumed future rate.

## Other available development evidence

The 60-root Stage 2 recovery is a re-decode of saved Stage 4C development detector/observable rows, not a new experiment. Its detector-calibrated static matching minus pooled fixed estimate was `+0.00001556` equal-regime LER, bootstrap 95% CI `[−0.00004889,+0.00007667]`, sign-flip `p=.66658`; calibration arrays were not preserved, limiting independent reconstruction of the selection stage. Correlation-mode smoke/pilot counts and neural-decoder results in the original NS-0 package are likewise development diagnostics, not independent evidence.

## Integrity boundary

Publication changed metadata only, not scientific file content. This review adds only new, explicitly labeled NS-0 audit/protocol documents. No sampling, training, decoder evaluation, protected-outcome access, or seed creation occurred during this review.
