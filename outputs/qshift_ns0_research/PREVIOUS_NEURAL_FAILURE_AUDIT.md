# Previous Q-SHIFT neural-decoder failure audit

This audit reads the implementations and retained development summaries; it does not rerun training or evaluation. Exact counts below are copied/reconciled from the saved audit reports, not newly simulated.

## Confirmed development outcomes

| Study | Actual method and evaluation result | What it supports |
|---|---|---|
| Early geometry CNN diagnostics | Pooled CNNs had 3,929 parameters and 5.244% mean LER versus 0.411% PyMatching; position-preserving flat CNN improved to 1.267%, but still lost by 0.856 percentage points. The displayed threshold score shared its threshold-selection partition and is optimistic. | Location pooling likely discarded useful position; representation change helped against pooled CNN, not against matching. Three roots only. |
| Five-root residual-position development | Residual CNN input was the 40 sparse detector bits plus frozen PyMatching logical prediction; target was `observable XOR PyMatching`. It made 689/150,000 errors (0.4593%) vs PM 653/150,000 (0.4353%). Candidate-only/PM-only failures 49/13; only 62/150,000 outputs differed. | Existing residual architecture copied PM most of the time and its sparse changes were net harmful. Training, calibration and threshold selection were separated from final-development scoring in this later study. |
| CNN architecture Stage 2 | On 50,000 shots/condition pooled over five roots, residual variants were equal or worse than fixed PM on nominal and synthetic burst conditions. The primary V2 candidate's burst delta was +0.000180 LER, 0/5 favorable roots, frozen gate failed. | No repeatable development gain; a small synthetic burst benefit cannot be assumed. |
| Stage 3 burst-focused residual | 344/50,000 PM failures and 344/50,000 stage-3 CNN failures on burst condition; candidate made zero prediction changes. The final evidence audit recomputed 200,000 samples in 30 partitions; status failed. | Confidence gate collapsed to identity; repeated examples of rare residual positives and a high correction threshold did not produce useful new decisions. |
| Hybrid residual sprint | 30/30 training jobs completed, but the controller failed during finalization. Independent saved-evidence audit recovered 225,000 paired final-development shots: the primary confidence-gated candidate exactly tied PM at 1,129/225,000; gate selected no corrections for all five roots. Alternate `min_ler` policies were mostly worse; all Holm p-values 1. | Strongest audit says no supported value from merely scaling the same residual idea. Preserve operational failure and null result. |

## What was and was not the failure

**Not just a geometry bug:** detector-to-coordinate mapping was audited as bijective, binary arrays and observable/XOR conventions were checked, and deterministic memorization controls showed the CNN/MLP can fit a small training set. Position-preserving CNN reduced the earlier pooled model's error substantially.

**Class imbalance is real but not a complete diagnosis:** audited residual positives were rare (about 0.6–0.8% in selected training roots); class-balanced batches reused positives 320–622 times in the burst-focused stage. Earlier weighted-BCE handling also required a logit-offset correction. These are concrete optimization/calibration risks. But later corrected training and separate score partitions still did not produce gains, so neither more data nor balancing alone is established as sufficient.

**The more direct limitation is utility/decision precision:** residual networks almost always copied an already strong decoder. When they did change predictions, harmful changes exceeded helpful ones, or a cautious threshold made zero changes. This is a failure to demonstrate generalizable incremental logical utility, not evidence that all neural decoders are futile.

**Causes still uncertain:** small root counts; distance-3/five-round Z-memory synthetic circuit; sparse rare events; training/noise distribution mismatch; model calibration; thresholds; objective alignment (BCE vs logical risk); finite-data variance; and no broad failure-mode study. Do not claim the architecture, optimizer or event representation has a single proven root cause.

## Design consequences

1. Do not promote another end-to-end CNN or residual head as the primary new direction without first demonstrating useful complementary corrections on fresh development roots.
2. Prefer an algorithmically different decoder (HAMLD or a small tensor-network reference) to test whether any static decoding headroom exists.
3. If learning is revisited, adopt local predecode plus a verified global fallback, train on independent roots and evaluate on separate roots. Log candidate-only and baseline-only failures and correction precision at the chosen gate. No threshold or model selection may use final evaluation outcomes.
4. Use root/stream clusters for inference. A large shot total on one or a few streams does not repair missing independent training/evaluation roots.

## Source trail

- `outputs/cnn_architecture_stage1_v1/CNN_ARCHITECTURE_AUDIT.md`
- `outputs/cnn_architecture_stage2_v1/CNN_STAGE2_RESULTS.md`
- `outputs/cnn_stage3_residual_gate_v1/CNN_STAGE3_RESULTS.md` and `CNN_STAGE3_INDEPENDENT_AUDIT.md`
- `outputs/neural_decoder_diagnostic/autonomous_development/experiment.py`
- `outputs/neural_decoder_diagnostic/hybrid_residual_sprint_v1/post_run_audit/FINAL_RESEARCH_REPORT_AUDITED.md`
- `outputs/neural_decoder_diagnostic/root_cause_analysis/position_preserving_cnn/POSITIONAL_CNN_REPORT.md`
