# Stage 5 n=1,210 readiness decision

## NO-GO for sampling readiness

The n=1,210 primary Endpoint B design passes the previously frozen finite-envelope type-I and confidence-bound coverage requirements. The 1.5× formal power gate passes at −0.0003, and every requested 2× sensitivity family—including the previously missing zero-inflated 2× condition—was simulated at both −0.0003 and −0.0004. The separate p=0 size, coverage, and reported safety-pass conditions also pass.

The complete design does **not** pass, because the previously specified four-condition Welch/Holm family is anti-conservative for the skewed and tied/asymmetric null models. Its complete-null familywise rejection rate reaches 9.3815% (right-skew lognormal 1.5×), versus the frozen 5.2% maximum. The independent replay reproduced the rejection counts.

Because the Holm family is part of the prior multiplicity plan, the primary endpoint’s successful calibration is insufficient for overall readiness. The v2 frozen protocol and the n=666 candidate remain unchanged. No 1,210-root Stage 5 runner, Stage 5 sample seed inventory, or sampling freeze is prepared. No allocation increase or inferential-method substitution is made here.

## Scope and safety

- Statistical design simulation completed; Stage 5 evaluation shots generated: **0**.
- Sealed historical test data accessed: **No**.
- Stage 4C evidence modified: **No**.
- Website worktree modified: **No**.
- Stage 5 sampling authorization: **Not granted by this work**; a new versioned design and separate authorization remain necessary.

## Blocking issue

The frozen candidate Welch/Holm procedure fails finite-envelope Type-I control under right-skew lognormal and tied/asymmetric root effects. Do not execute Stage 5 with the current full multiplicity plan. Any replacement secondary procedure must be specified and validated prospectively, without changing Endpoint B, its −0.0002 boundary, the −0.0003 planning alternative, or the allocation solely to obtain a pass. Stage 5 remains NO-GO until the multiplicity procedure is resolved and independently reviewed.

See `STATISTICAL_VALIDATION_REPORT.md`, `SECONDARY_HOLM_FINDINGS.md`, and `INDEPENDENT_AUDIT.json` / `secondary_holm/SECONDARY_HOLM_AUDIT_REPAIR_V2.json` for the detailed evidence.
