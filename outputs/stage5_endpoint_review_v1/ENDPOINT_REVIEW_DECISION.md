# Stage 5 endpoint review decision

**Recommendation: Endpoint B as the primary scientific claim; Stage 5 remains NO-GO for sampling pending owner approval and a prospectively revised power/resource decision.**

Endpoint A (improvement below zero) is a legitimate narrower scientific question and could be answered with the existing 100 roots/stratum under its stated variance assumptions. The 0.0002 threshold would then be a benchmark, not a pass criterion. This avoids a practical claim unsupported by the inferential target, but a statistically detectable effect could be too small to matter.

Endpoint B directly tests practical value: the one-sided upper 95% confidence bound must be below −0.0002. Under the current provisional SDs, 100 roots/stratum provide only about 46% power when the true effect is −0.0003, although about 93% at −0.0004. The 2.5M cap cannot support 80% power for a 0.0001 gap beyond the margin (estimated 256 roots/stratum, 5.76M shots). Since the Stage 4/4C variance inputs have only seven roots per condition, these are weak power assurances, not guarantees.

**Statistical method recommendation:** Welch–Satterthwaite stratified-mean inference as primary for the equal-weight mean, with a paired root-stratified bootstrap-t sensitivity interval. Preserve pairing at the root level; never bootstrap shots. Require agreement or classify as inconclusive. Do not rely on root sign-flip as the sole test because decoder arms were not randomized and sign-symmetry is not established. Keep Holm correction for the four condition-specific secondary tests and retain p=0 as a separately specified safety conjunct.

**Approval needed before sampling:** choose Endpoint A or B; if B, either approve a revised budget/root count based on an accepted target effect beyond the margin, or explicitly accept that the current budget is weak for modest practical gains. Any choice requires a new versioned freeze. No Stage 5 samples were generated, and no sealed-test data were accessed.
