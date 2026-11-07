# Research direction ranking

## Ranking by evidence readiness

| Rank | Direction | Current evidence | Feasibility | Decision |
|---:|---|---|---|---|
| 1 | C — structured/correlation-aware decoder representation first, adaptation later | Exact small cases reveal representation sensitivity; correlation-enabled fixed matching improves pooled mean by 0.000254 LER with root-level CI below zero, but misses the prespecified -0.0002 practical CI gate and harms 2/6 strata. Full categorical inference is unscaled; no robust full-circuit advantage. | Medium-to-high engineering cost. Needs a valid scalable decoder and stronger development headroom. | Most scientifically informative *direction*, but do not authorize an experiment yet. Current evidence is insufficient to declare useful performance or novelty. |
| 2 | A — select among existing models using detector signals | Hindsight gaps exist, but the bank-wide multi-distance selection gate fails; out-of-root gates do not improve pooled fixed; Phase 4C Stage 2 is null. | Easy to run but poor scientific value without new headroom. | No-go. |
| 3 | B — online matching-weight update | Rebuild prototype works, but utility remains inconclusive, trigger false-alarm bound is not certified, and no equal-resource periodic baseline is evaluated. Online calibration/adaptation is established. | Technically feasible for small systems; careful resource matching required. | No-go under current evidence and novelty claim. |

## Next experiment selection

No new experiment is selected. Direction C is ranked first only as a research question, not as an authorization. The current Phase 2C reference is weaker than PyMatching and the exact/categorical scaling work has not produced a decoder that passes a development utility gate. A new study would be premature until a candidate structured decoder demonstrates, on development-only paired roots, non-inferior or better risk than the strongest fixed matcher and acceptable full-circuit resource use.

