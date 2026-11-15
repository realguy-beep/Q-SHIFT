# Q-SHIFT research status

**Last reviewed:** 2026-11-11
**Project status:** simulation-based research prototype; no demonstrated adaptive or neural-decoder advantage over strong fixed PyMatching; no quantum-hardware integration.

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
