# Development log

## Repository audit and design decisions

- Preserved all historical Phase 1–5 folders, Phase 4C Stage 2 evidence, and the submitted `final_release` documents.
- Audited the existing Phase 5 controller, nine-model bank, schedule generator, evaluation runner, tests, and result JSONs. The historical Phase 5 study accounting has known runner/report discrepancies documented in the final research report.
- Found the prior nine-grid estimator-to-three-regime conversion was not a principled mapping: grid IDs encode gate/measurement probability pairs, not three generating labels. The existing files were not edited. This package instead fits three detector profiles directly from separate development calibration samples.
- Used the Phase 4C Stage 1 pooled model (grid index 1) as strong fixed fallback and index 4 as the nominal fixed baseline. These are not retuned on evaluation outcomes.
- Required calibration-estimated utility improvement to exceed both a frozen penalty and a paired calibration uncertainty margin. This conservative gate was specified before evaluation was generated.
- Schedules change only between batches of independent simulated memory experiments; no within-circuit time drift is represented.

## Execution record

- Six unit tests passed before the experiment.
- First runner attempt completed and wrote the deterministic paired sample bundles but then stopped during summary aggregation because the reporting code referenced a superseded runtime-field name. The field was corrected; the complete study was rerun with the same frozen seeds and settings.
- Independent audit first stopped on a missing identity-baseline comparison row in the report table. The audit formatter was corrected and rerun; no scientific method or saved predictions changed.
- Final run: 60,000 calibration shots and 307,200 paired evaluation shots across 50 roots, five schedule families, ten roots each, 12 blocks/root, 512 shots/block.
- Independent decode audit: PASS; all nine stored model predictions exactly matched regenerated predictions on saved detector arrays. Aggregate and paired statistics were recomputed from NPZ evidence.
- Result: adaptive stayed at decoder 1 in all blocks (zero switches), because calibration chose decoder 1 as lowest estimated LER in all three regimes. Adaptive, regime-informed diagnostic, and pooled fixed all had 1,989 errors on the same 307,200 evaluation shots. No adaptive advantage was observed.

## Scientific interpretation

This result localizes the immediate blocker: in this noise model and decoder bank, calibration did not find useful specialization. Detector classification was usually accurate after a completed regime block (but failed under the rapid two-block/alternating schedule); better classification alone cannot help if the model bank does not offer a reliably better correction. Given this evidence, more switching complexity is not justified. A future feasibility step should first investigate physically motivated noise models that alter decoder utility, then reevaluate specialization on development data before freezing any new test.
