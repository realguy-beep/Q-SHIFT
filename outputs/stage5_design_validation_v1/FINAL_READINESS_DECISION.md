# Final Stage 5 design-validation decision

## Decision

**NO-GO for Stage 5 sampling.** Endpoint B remains the appropriate scientific endpoint if Q-SHIFT intends to claim practical benefit, but the candidate statistical procedure and 256-root allocation are not ready for authorization.

## Why

1. The proposed Welch–Satterthwaite primary test had an estimated 7.57% false-positive rate at the practical null boundary under the prespecified right-skew root-effect scenario (10,000 simulations; 95% Monte Carlo interval 7.07–8.10%). Its one-sided upper-bound coverage was 92.43%. The ordinary paired bootstrap-t sensitivity had only 1,000 outer/399 inner resamples and did not establish adequate coverage; its skew-case Monte Carlo intervals were wide.
2. 256 roots/condition gives about 80% power at true Δ=−0.0003 only under the nominal development SDs. At 1.5× root SD, estimated power is about 51%; at 2× it is 34%. The inputs are estimated from seven roots/cell.
3. 256 roots/condition entails 5.76M unique shots and exceeds the frozen v2 cap of 2.5M. Its runner and auditor are fixed to 100 roots/condition and must be versioned anew.
4. The full Stim/PyMatching pipeline and independent dynamic audit work on a 225k-shot disposable benchmark; resource use is promising. This resolves engineering feasibility at pilot scale, not statistical validity or decoder performance.

## Exact conditions before reconsideration

- Freeze a new inferential design before any Stage 5 sampling. It must target the mean root-level paired LER difference under Endpoint B, control type-I error at Δ=−0.0002 under plausible skew/zero-inflated/tied root effects, and demonstrate interval coverage with Monte Carlo precision sufficient to distinguish meaningful failure from simulation noise.
- Replace subjective “Welch/bootstrap agreement” with an exact mathematical pass rule. A sensitivity procedure must not be selected after seeing which gives the favorable outcome.
- Predeclare a target alternative beyond the boundary (e.g. −0.0003) and account for at least 1.5×/2× variance sensitivity. Under current approximations, 80% power at −0.0003 requires 256 roots at nominal SD, 575 at 1.5×, and 1,023 at 2×; associated totals are 5.76M, 12.94M, and 23.02M shots.
- Approve an updated shot/time/storage budget and build a new root-count-parameterized runner, seed inventory, and independent auditor; retain v2 unchanged.
- Collision-screen new Stage 5 seeds against all recoverable historical seeds, run no-shot checks, freeze hashes, then obtain explicit sampling authorization.

Until all conditions are met, do not run Stage 5. No Stage 5 evaluation shots were generated; sealed test data remain unopened. Stage 4C evidence and the Stage 5 v2 freeze are unchanged.

## Proposed quantitative authorization checks (newly proposed; not frozen)

For the next design review, predeclare and run at least 100,000 outer Monte Carlo experiments per null scenario, with 95% Wilson Monte Carlo intervals. Require: (a) one-sided primary type-I error upper Wilson endpoint ≤0.052 in every prespecified root-effect null scenario; (b) one-sided upper-bound coverage lower Wilson endpoint ≥0.94; and (c) central 95% interval coverage lower Wilson endpoint ≥0.94. Apply the same type-I/one-sided coverage rule to the p=0 no-harm boundary. These tolerances are proposed for owner/statistician approval before the next simulation freeze; they are not an edit to v2.

Also require the lower 95% Monte Carlo bound on primary power to reach at least 80% at the owner-selected target alternative under a 1.5× root-SD scenario. Under current normal-theory planning, a target Δ=−0.0003 (0.0001 beyond the practical margin) needs about 575 roots/stratum and 12.94M shots; a target Δ=−0.0004 needs about 144 roots/stratum and 3.24M shots. These are planning values to be revalidated under the selected inferential procedure. A budget below the resulting allocation is not a confirmatory GO.
