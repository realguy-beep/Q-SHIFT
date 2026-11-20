# Q-SHIFT research status

**Last reviewed:** 2026-11-20
**Project status:** simulation-based research prototype; no demonstrated adaptive or neural-decoder advantage over strong fixed PyMatching; no quantum-hardware integration. Correlated-noise-aware decoders (exact DEM decoding at d=3, hypergraph BP+OSD at d=5) show a pre-registered development-evidence advantage over the strongest static matcher for synthetic weight-3 burst families (at d=5, robust across two families and p = 0.002–0.004, confirmed with burst support learned from calibration data for a known and a sealed hidden burst, and 94.0% below in a burst-dominated low-p regime, short of the 95% target); none beats it at d=7 (see below).

## Adaptive and broadly robust program (2026-11-18 to 2026-11-20)

The full ledger is `outputs/qshift_adaptive_robust_v1/STATUS.md`. Everything is simulation-only at d=5 with synthetic weight-3 X-bursts, and development evidence except RE1.

- **Mismatch repair works, and RE1 confirmed it.** Re-basing the learner on a detector-estimated (p, Z-bias) model fixes the model-mismatch failure. In the frozen RE1 evaluation, R1–R5 were 59–88% below the strongest deployable matcher and matched the oracle.
- **RE1 is NOT_CONFIRMED overall.** Its sealed hidden burst (R6) was never learned, because the estimator flagged every root.
- **The estimator was rebuilt over three studies:**
  - BRE: PARTIAL;
  - BRS: NOT_SUPPORTED;
  - BRT: SUPPORTED. The threshold-free estimator E1T learned 126/128 bursts of 5–30 detectors with no in-family false bursts. It has not yet been tested on a sealed burst; that is RE2, not run.
- **AD1 is NOT_SUPPORTED.** A causal rolling-window adaptive decoder stayed within 6% of the oracle under every drift tested and never learned a wrong burst. But it gained nothing over a single early estimate under mild background drift. It did help when a burst appeared and then disappeared (117 vs 156 errors), but that was not a pre-registered tracking endpoint.
- **The 95% target is still not reached.**

## Correlated-noise decoder line V1.1–d=5 low-p regime (2026-11-15 to 2026-11-18)

Full summary, deviations and links: `outputs/qshift_correlated_decoder_synthesis_v1/REPORT.md`. All results are simulation-only development evidence (rotated Z-memory, 5 rounds, p=0.003, synthetic `CORRELATED_ERROR(q)` X-burst, q ∈ {0, 0.01, 0.02}); comparators are the strongest static matcher (correlated PyMatching, selected on development data), not nominal matching.

- d=3: exact DEM decoding is ~61% below the strongest matcher (V1.5, frozen), also with burst support learned from calibration data (V1.6b, frozen: 61.5% known burst, 52.4% sealed hidden burst).
- d=5: serial hypergraph BP+OSD (`ldpc` 2.4.1) with one static prior is 64.8% below correlated PyMatching (95% CI 61.2–68.4%), and 46% below at q=0 (frozen Phase 2, 600,048 fresh shots, GO_d5).
- d=5 robustness (frozen, 1,800,144 fresh shots, ROBUST): the gain holds for a 2-detector centre_row burst (−20.9%, 95% CI 13.3–28.0), at p=0.002 (−78.1%, 71.8–83.8) and at p=0.004 (−56.8%, 53.0–60.3), each against a re-selected correlated PyMatching. It passed the Bonferroni CI and q=0 safety in every condition.
- d=5 learned support (frozen Phase C, 1,200,096 fresh shots + 27,000 calibration, CONFIRMED): BP+OSD with a burst support learned by a null-calibrated parity-moment learner is 59.8% below true-support correlated PyMatching for the known burst (95% CI 55.8–63.7) and 44.8% below for a sealed hidden burst (40.3–49.3). Both supports were learned exactly, so the learned-support decoder matched the oracle-support decoder bit for bit. Caveats: one learning draw per condition; the learner assumes the true base noise model; the hidden burst (12,34,40) is a one-qubit neighbour of a development surrogate.
- d=5 model mismatch (Phase A development diagnostic): the Phase C learner is not robust to a wrong base model. With the true p 17% lower (Mlo) or Z-biased noise (Mz) it learned 0/24 burst pools; with p 17% higher (Mhi) it falsely accepted 24/24 burst-free pools. Phase B is on hold.
- d=5 low-p regime (frozen Stage E, 2,892,888 fresh shots, CONFIRMED): at p = 0.001 BP+OSD (true support) is 94.0% below re-selected correlated PyMatching (95% CI 92.3–95.5); at p = 0.0015, 93.1% (90.7–95.2). Pre-registered target verdict: TARGET_NOT_MET. The burst is effectively decoded (L2 errors 25/26/30 against a burst-free floor of 25); the limit is background decoding. The regime was chosen because the target is reachable there.
- d=7: BP+OSD (four configurations) and parallel belief-matching all failed pre-registered development screens (STOP); serial belief-matching untested for cost reasons.
- The owner's 95% reduction target is not reached. At p = 0.003 the background floor caps it near 65%; the closest result is 94.0% in the low-p regime.

## Core software integration v1 (engineering-only; 2026-11-12)

- Added a typed decoder/observable interface and PyMatching adapter. The dashboard compatibility path preserves the Phase 2B model's existing correlation-enabled construction and decode behavior; no noise-model or result interpretation changed.
- Tightened dashboard configuration, existing seed-plan input checks, and simulator input checks; added contextual sampler failures, a collision-screened domain-separated seed helper for future versioned work, and a paired development evaluator that refuses protected-test scope.
- Added a causal decoder-registry/controller hook with explicit confidence, block provenance, hysteresis/dwell, fallback, and separate estimated/configured noise metadata. It is infrastructure only and has not been used to produce performance results.
- Added a short interface note explaining that decoder output is a logical-observable prediction, not a physical correction instruction.
- Deterministic tests exercised small DEM decoding and in-memory arrays only. No Stim sampling, training, protected evaluation, Stage 5 run, or hardware action occurred.
- This milestone does not change the scientific baseline: fixed PyMatching remains the strongest established method in this repository; adaptive and neural superiority remain unproven. See outputs/core_system_upgrade_v1/ for implementation and validation limitations.

## Supported findings

- Stim/PyMatching simulation, a local dashboard, detector-only calibration experiments, a small neural training pipeline, and multiple reproducibility/audit tools have been implemented.
- Early lookup and regime-switching methods did not beat fixed matching reliably. Specialist decoders often matched the fixed decoder or were rejected by validation; an early positive-looking result failed independent replication or multiplicity controls.
- Phase 4A's distance-3, five-round Z-memory study reported measurement-heavy test errors of 1,118 for fixed nominal PyMatching versus 940 for detector-calibrated matching in 600,000 paired shots. Its data-heavy result slightly favored fixed matching and its nominal result tied. Phase 4B reported 1,165 versus 1,008 errors in the corresponding measurement-heavy comparison, with 99 candidate-only and 256 fixed-only failures. The independent evidence audit classified Phase 4B **PASS WITH DEVIATION** because fresh templates were generated despite the frozen plan specifying reuse; saved test predictions were re-decoded, but calibration samples were unavailable for a full calibration-provenance audit.
- In Phase 4C Stage 2, independently re-decoded saved checkpoints covered 1,800,000 held-out shots across three regimes. Calibrated and pooled-fixed errors were respectively 8,459/8,382 (data-heavy), 2,996/2,949 (nominal), and 980/1,076 (measurement-heavy). The frozen equal-regime primary difference was calibrated minus pooled-fixed **+0.00001556**, with the reported sign-flip test **p=0.6666**. Calibration samples were not saved, so those selections could not be refit independently. This is not evidence of an overall adaptive gain.
- The first small structured CNN/MLP study showed all-negative collapse or a copy-the-matcher residual model. A later position-preserving CNN diagnostic improved substantially over the original pooled CNN and matched the balanced MLP in a three-root development comparison, but all neural candidates remained worse than PyMatching. The study was exploratory, used small development roots and validation-selected thresholds, and did not open an independent test set.
- The 750K autonomous development controller records `completed` (50/50 jobs, five roots, independent-test access 0). Its run manifest has 376 matching entries and one documented post-manifest stdout change; do not treat process status alone as a scientific analysis. The 1.665M hybrid residual sprint remains recorded `failed`; its finalization order bug is documented and was repaired only in a separate future-run module. Its status must not be changed.
- The current Phase 3A preflight added a synthetic spatial common-cause X-burst to neighboring data qubits. The deterministic preflight and tests passed, but only small diagnostic samples were used. The matching correlation on/off toggle made identical predictions on the 256-shot smoke sample; no performance advantage was established. Phase 3B production sampling is unexecuted.

## Strong fixed-baseline development study (2026-11-11)

- The study in `outputs/strong_fixed_baselines_v1/` generated **3,660,000 unique shots**, including 1,500,000 paired evaluation shots across 600 roots and five synthetic burst probabilities. It compared nominal fixed PyMatching, one pooled detector-calibrated fixed matcher, a safety-constrained static choice, per-root detector-profile adaptation and a privileged true-probability reference.
- The original runner's pooled-estimator call used known generating-condition tags in the calibration partition, contrary to its frozen pooled-detector-only rule. This is a confirmed protocol deviation. The legacy estimate (`p=0.00831`) and predictions remain preserved and excluded from corrected comparisons. A separately frozen reconstruction estimated `p=0.00804` from independent templates plus pooled calibration detector rows, re-decoded the saved paired evaluation arrays, and passed independent numerical verification. The two pooled estimates produced identical predictions on these saved shots; that coincidence does not erase the deviation.
- Reconstructed errors by burst probability `[0, .004, .008, .012, .016]`, each on 300,000 paired shots:

  | Method | Error counts |
  |---|---|
  | Nominal fixed | 1,444 / 1,719 / 2,122 / 2,344 / 2,523 |
  | Pooled detector-static (`p=0.00804`) | 1,581 / 1,598 / 1,771 / 1,746 / 1,692 |
  | Safety-constrained static | 1,444 / 1,719 / 2,122 / 2,344 / 2,523 |
  | Detector-profile adaptive | 1,446 / 1,594 / 1,773 / 1,740 / 1,665 |
  | Privileged true-p reference | 1,444 / 1,596 / 1,771 / 1,740 / 1,666 |

- Safety-static selected `p=0.004` on the selection partition but reverted to `p=0` because its validation one-sided 95% root-bootstrap upper bound for zero-burst harm was `+0.00056`, above the `+0.0002` rule. Thus final safety-static equals nominal. Pooled fixed reduced errors at nonzero burst settings but had a zero-burst excess of `+0.0004567` (one-sided 95% root-bootstrap upper `+0.0005233`), above the same harm benchmark.
- The equal-weight nonzero-condition adaptive-minus-pooled-static effect was `−0.00002917` absolute LER (about `−0.00292` percentage points); the 100,000-resample stratified root-cluster descriptive 95% interval was `[−0.00005167, −0.00000750]`. This is far smaller than the `0.0002` practical-benefit benchmark. No confirmatory p-value or superiority claim is made. Adaptive's p=0 excess over nominal was `+0.00000667`, with a descriptive one-sided 95% upper bound of `+0.0000200`.
- The independent saved-array verifier checked 600 roots, 1.5 million paired evaluation shots, exact decoder predictions, aggregate counts, paired discordances, bootstrap outputs and the zero-burst bound. This work did not access Stage 5 evaluation materials. Raw shot arrays remain local and Git-ignored.

## Limitations and unresolved evidence

- The experiments span different circuits, noise models, calibration rules and selection procedures; they are not one pooled benchmark.
- Some historical reports required correction or have documented discrepancies. Consult each audit before quoting a result.
- Phase 4C calibration arrays and fitting records are absent. Phase 4B template provenance deviates from the written plan. The 750K status does not substitute for a full independent scientific audit.
- Development results and validation-selected thresholds do not establish generalization. The later neural work does not justify a superiority claim.
- The current correlated burst is a synthetic proxy, not hardware-calibrated crosstalk. The categorical `PAULI_CHANNEL_2` to DEM path uses `approximate_disjoint_errors=True`; graph matching may not represent higher-order mechanisms exactly.
- No real quantum hardware, live device telemetry, or hardware control has been integrated.
- The strong-baseline burst result is not a clean execution of its original pooled calibration procedure. Its reconstruction is transparent development evidence, but the disclosed deviation and reused sampled evaluation set limit inference. Do not present the small adaptive-versus-pooled difference as confirmatory superiority.

## Recommended next step

Do not claim the current adaptive/CNN approach is superior or launch confirmatory sampling from this development study. Any next study should prospectively correct and freeze the pooled-calibration path, retain a strong pooled fixed arm and an explicit zero-burst safety criterion, and use fresh independent roots. Keep Stage 5's historical evidence separate from this synthetic burst follow-up.
