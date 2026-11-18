# Common-variance sequential profile inference under composition shift

## Hypothesis

The nominal class-specific Gaussian SPRT failed under doubled measurement noise because its score means/variances shifted. A simpler equal-variance Gaussian likelihood, using the existing nominal class means and pooled variance, may preserve profile decisions better by avoiding a class-specific variance shape that moves under composition drift.

## Frozen comparison

Use the existing LDA score feature and nominal training means; set common variance to the arithmetic mean of the two nominal score variances. Compare (a) the prior class-specific Gaussian SPRT, (b) the fixed common-variance Gaussian SPRT, and (c) fixed 25/100/500-shot LDA and likelihood decisions. Both sequential rules use threshold log(19) and a 500-shot cap. Test independent X/Z profile streams at nominal gate/measurement p=.003/.003 and withheld composition gate/measurement p=.003/.006, ratio10, d3/five rounds. Do not refit the LDA or any likelihood parameters on test data.

Preflight: 100 500-shot windows/profile/regime, seeds 2026115921–5924; require source identity, finite features and projected main under 300s. Main: 1,000 windows/profile/regime, fresh seeds 2026115931–5934. Report exact profile-error intervals, mean/median consumed shots, and matched fixed-budget baselines. Candidate advances only if common-variance SPRT's exact 95% upper error bounds are <=5% in all four profile/regime cells and its mean shot cost is below 100. This is a robustness test of a standard statistical variant, not a novelty claim or hardware evaluation.
