# Q-SHIFT research status

**Last reviewed:** 2026-11-07  
**Project status:** simulation-based research prototype; no demonstrated adaptive or neural-decoder advantage over strong fixed PyMatching; no quantum-hardware integration.

## Supported findings

- Stim/PyMatching simulation, a local dashboard, detector-only calibration experiments, a small neural training pipeline, and multiple reproducibility/audit tools have been implemented.
- Early lookup and regime-switching methods did not beat fixed matching reliably. Specialist decoders often matched the fixed decoder or were rejected by validation; an early positive-looking result failed independent replication or multiplicity controls.
- Phase 4A's distance-3, five-round Z-memory study reported measurement-heavy test errors of 1,118 for fixed nominal PyMatching versus 940 for detector-calibrated matching in 600,000 paired shots. Its data-heavy result slightly favored fixed matching and its nominal result tied. Phase 4B reported 1,165 versus 1,008 errors in the corresponding measurement-heavy comparison, with 99 candidate-only and 256 fixed-only failures. The independent evidence audit classified Phase 4B **PASS WITH DEVIATION** because fresh templates were generated despite the frozen plan specifying reuse; saved test predictions were re-decoded, but calibration samples were unavailable for a full calibration-provenance audit.
- In Phase 4C Stage 2, independently re-decoded saved checkpoints covered 1,800,000 held-out shots across three regimes. Calibrated and pooled-fixed errors were respectively 8,459/8,382 (data-heavy), 2,996/2,949 (nominal), and 980/1,076 (measurement-heavy). The frozen equal-regime primary difference was calibrated minus pooled-fixed **+0.00001556**, with the reported sign-flip test **p=0.6666**. Calibration samples were not saved, so those selections could not be refit independently. This is not evidence of an overall adaptive gain.
- The first small structured CNN/MLP study showed all-negative collapse or a copy-the-matcher residual model. A later position-preserving CNN diagnostic improved substantially over the original pooled CNN and matched the balanced MLP in a three-root development comparison, but all neural candidates remained worse than PyMatching. The study was exploratory, used small development roots and validation-selected thresholds, and did not open an independent test set.
- The 750K autonomous development controller records `completed` (50/50 jobs, five roots, independent-test access 0). Its run manifest has 376 matching entries and one documented post-manifest stdout change; do not treat process status alone as a scientific analysis. The 1.665M hybrid residual sprint remains recorded `failed`; its finalization order bug is documented and was repaired only in a separate future-run module. Its status must not be changed.
- The current Phase 3A preflight added a synthetic spatial common-cause X-burst to neighboring data qubits. The deterministic preflight and tests passed, but only small diagnostic samples were used. The matching correlation on/off toggle made identical predictions on the 256-shot smoke sample; no performance advantage was established. Phase 3B production sampling is unexecuted.

## Limitations and unresolved evidence

- The experiments span different circuits, noise models, calibration rules and selection procedures; they are not one pooled benchmark.
- Some historical reports required correction or have documented discrepancies. Consult each audit before quoting a result.
- Phase 4C calibration arrays and fitting records are absent. Phase 4B template provenance deviates from the written plan. The 750K status does not substitute for a full independent scientific audit.
- Development results and validation-selected thresholds do not establish generalization. The later neural work does not justify a superiority claim.
- The current correlated burst is a synthetic proxy, not hardware-calibrated crosstalk. The categorical `PAULI_CHANNEL_2` to DEM path uses `approximate_disjoint_errors=True`; graph matching may not represent higher-order mechanisms exactly.
- No real quantum hardware, live device telemetry, or hardware control has been integrated.

## Recommended next step

Do not scale the current adaptive/CNN approach or start a Phase 3B production run from this setup task. First freeze a narrow, development-only protocol for testing whether the selected graphlike burst event's explicit DEM edge helps relative to burst-blind matching, with paired samples and independent roots. Keep the existing correlated preflight as plumbing evidence only and retain all no-go outcomes.
