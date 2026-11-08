# Statistical decisions

All decisions below use the frozen Stage 5 analysis and its prespecified root-level paired estimands. The verification script in this package recomputes the inferential output from the published per-root audit records and checks it against `RESULTS.json`.

## Primary Endpoint B

- **Estimand:** Equal-weight mean across p = 0.004, 0.008, 0.012, and 0.016 of each condition's mean root-paired adaptive-minus-fixed logical-error-rate difference.
- **Practical boundary:** −0.0002 absolute LER difference. The planned alternative was −0.0003.
- **Estimate:** −0.0015459504 (SE 0.0000139649).
- **Prespecified calibrated one-sided upper bound:** −0.0015210702.
- **Prespecified central interval:** [−0.0015757962, −0.0015181269].
- **Decision:** PASS. The upper bound is below −0.0002.

The root is the inference unit: paired shot errors are reduced to a root-level difference before inference. The frozen calibrated critical value is 1.7816207022. The decision is based on the calibrated bound, not a post-hoc normal approximation.

## Zero-burst no-harm gate

At p = 0, the fixed decoder had 14,825 errors and the adaptive decoder 14,837 across 3,025,000 evaluation shots. The paired mean difference was +0.0000039669 (SE 0.0000020355); the one-sided upper bound was +0.0000074384. The frozen no-harm boundary is +0.0002. **PASS.**

## Secondary condition-level family

The four nonzero-condition one-sided tests use the prospectively repaired finite-envelope procedure and Holm step-down correction at familywise alpha 0.05. The unadjusted finite-envelope p-value was 0.00216710197 in each condition; each Holm-adjusted value was 0.00866840789. All four secondary tests reject their nulls under this procedure.

| Burst probability | Mean adaptive − fixed | Root SD | SE | Simultaneous upper bound | Holm-adjusted p |
|---:|---:|---:|---:|---:|---:|
| 0.004 | −0.0004082645 | 0.0005814313 | 0.0000167150 | −0.0003636758 | 0.0086684079 |
| 0.008 | −0.0011338843 | 0.0008811559 | 0.0000253315 | −0.0010663105 | 0.0086684079 |
| 0.012 | −0.0019471074 | 0.0010751632 | 0.0000309088 | −0.0018646557 | 0.0086684079 |
| 0.016 | −0.0026945455 | 0.0012268245 | 0.0000352687 | −0.0026004631 | 0.0086684079 |

The secondary calibration uses a finite set of six prespecified root-effect location-scale families with a DKW upper-CDF envelope and Holm correction. The guarantees are conditional on those families and the independent-root assumptions; they are not distribution-free. The Stage 5 design-validation report documents the simulation checks for size and coverage.

## Scope

No inferential decision was changed after inspecting evaluation outcomes. The archived `RUNNER_SUMMARY.json` statistics match the post-audit recomputation from the auditor's per-root results. The privileged reference is descriptive and is not part of the deployable adaptive-vs-fixed primary comparison.
