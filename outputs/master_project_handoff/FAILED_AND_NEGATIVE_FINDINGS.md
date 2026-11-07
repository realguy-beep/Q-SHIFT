# Failed and Negative Findings

Preserve these outcomes as part of the research record.

| Study / approach | Observation | Interpretation |
|---|---|---|
| Starter `logical_error` classifier | Conversation result reports 0.98 positive recall but 0.41 precision; a separate report says XOR correction worsened residual rate from 0.5333% to 0.7573%. | Not a validated decoder advantage. The conversation metrics lack a matching local raw artifact, and row duplication is severe. |
| Early pooled lookup | One large single-seed run looked favorable versus matching, but ten-seed follow-up had higher total lookup error counts at all six noise probabilities (e.g. .006: 413 vs 374; .008: 741 vs 663). | Early apparent gain did not replicate; do not select on one seed. |
| Adaptive threshold / validation choice | Validation-selected lookup policy totals were higher than fixed matching across tested rates in the ten-seed research study. | Adaptation policy did not beat the fixed baseline. |
| Time-varying repetition-code policy | Guarded detector adaptation tied fixed because validation rejected all lookup choices; earlier rate-only selector had 589 vs fixed 558 errors on its own stream. | Recognition alone is insufficient; switching can be harmful. |
| Phase 1 specialist lookup | Pooled/per-regime lookup generally had more residual errors than fixed matching. Report and JSON disagree on per-regime aggregates. | No demonstrated lookup advantage; raw replay needed to resolve the table discrepancy. |
| Phase 2 composition specialists | X/Z/depolarizing specialist outputs exactly matched fixed matching; measurement specialist rarely differed. Validation selected fixed in all 60 choices. | Usefulness gate failed; correctly stopped before selector implementation. |
| Phase 3A invalid v1 | Probability fractions were passed without scaling by the intended base noise level; residuals approached 50%. | Invalid experiment, excluded from scientific comparison. |
| Phase 3A apparent X specialist gain | 2,520 vs 2,528 residuals on 36k; p=.0386 unadjusted, approximately .463 after 12-way adjustment. | Exploratory pilot signal did not meet multiplicity control; same seeds were reused across v2–v4. |
| Phase 3B independent replication | X specialist 43,675 vs fixed 43,673 on 600k; paired McNemar p=.9374; seed bootstrap interval crosses zero. | No replication of the pilot advantage. Stop this specialist branch for the tested setup. |
| Phase 1 nearest-regime treatment of held-out mixtures | Held-out mixtures were assigned to familiar regimes rather than identified as unfamiliar. | No novelty detection/generalization claim is justified. |
| Phase 3 measurement-noise scope | Phase 3A pilot disabled measurement noise. | It cannot support claims for mixed data-plus-measurement behavior. |

## Preserve interpretation

“No evidence of improvement” is not proof that no adaptive decoder can ever help. It means the specified architectures, circuits, calibration procedures, and tested conditions did not produce a reproducible advantage. Retain these failures and do not remove them from future summaries.
