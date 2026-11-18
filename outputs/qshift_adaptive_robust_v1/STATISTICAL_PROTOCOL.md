# Statistical protocol (prospective draft; becomes binding only when frozen)

## Hypotheses (from RESEARCH_QUESTIONS.md)

- **Primary family**, overall α = 0.025, one-sided, Bonferroni-split across the two primary tests:
  - **H1a:** R_pool(Q vs S\*) > 0, at α = 0.0125.
  - **G_ADAPT:** Q < Q0 on the pooled endpoint, at α = 0.0125.
- **Target family** (the 95% goal; reported regardless of the primary result):
  - **G_AGG:** the one-sided 97.5% lower bound of R_pool is ≥ 0.95.
  - **G_EVERY:** Holm across eligible conditions at α = 0.025, H0: R_c ≤ 0.95.
- **Safety:** G_SAFE per burst-free condition. Every condition must pass; this is a conjunction, so no adjustment is needed.
- **Secondary:** per-condition contrasts and the attribution ablations (`BASELINE_FAIRNESS.md`), as descriptive 95% CIs without gating.

## Design

- **Pairing:** every arm decodes the same rows.
- **Roots:** at least 24 independent roots per condition, each with its own seed from the split namespace. Uncertainty comes from a root-cluster bootstrap (20,000 replicates, roots resampled within condition, all arms jointly). The bootstrap seed is frozen in the seed file.
- **Calibration and test separation:** calibration rows are drawn from separate seeds in each root and never decoded for evaluation.
- **Temporal conditions:** the stream is calibration blocks, then test blocks, with the change point drawn from a frozen distribution. Adaptation delay and recovery are measured on test blocks only.

## Sample size (error-count based)

- For each eligible condition, the frozen shots are N_c = ceil(30 / LER_val(S\*)).
- The pooled endpoint is additionally sized so that the projected Σ S\* failures reach ≥ 2 × `required_comparator_failures(R_val, 0.95, 0.025)` whenever R_val > 0.95. Otherwise it is sized for H1a at 80% power.
- **Hard cap:** a total wall-time budget is frozen with the preflight. If the cap binds, the protocol states that G_AGG is under-powered *before* sampling, rather than shrinking the benchmark.

## Staging (no peeking)

1. **Dev:** unrestricted development on the dev split; everything logged.
2. **Val:** each selection (S\*, decoder variant, controller thresholds, regime models) is made once on val with a pre-written rule and recorded with its val numbers.
3. **Freeze:** commit the code, seeds, selections, allocation, analysis script and preflight; record their hashes in `EVAL_FREEZE.json`. Evaluation requires `--expected-head` and a clean tree.
4. **Eval:** a single attempt with write-once jobs. A failure is reported as a failure, with no reruns or seed substitution.
5. **OOD:** run after eval, with no selection. It is reported separately.

## Verification after the run

- Run the analysis twice and confirm the outputs are byte-identical.
- Recount every total from the archives.
- Re-decode root 0 of every (condition, arm) bit-identically.
- Have a second, independently written analysis script recompute R_pool and the gates. It must be written before the eval run and frozen with it.

## Prohibitions

- No tuning on eval or OOD results. No reuse of historical frozen evaluation rows (Phase 2, robustness, Phase C, Stage E, Stage 5) for training, selection or thresholds.
- No reinterpretation of a failed gate.
- Stage S dev arrays may be used as **dev** data only, and only for floor diagnostics, as declared in `BACKGROUND_ERROR_ANALYSIS.md`.
