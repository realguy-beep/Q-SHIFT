# Stage 5 endpoint B statistical design validation v2

## Scope and frozen choices

This was a synthetic root-effect design simulation only. It generated no Stim shots and no Stage 5 evaluation data; sealed historical test data were not opened. The v2 frozen Stage 5 protocol was not changed. Before Monte Carlo, the candidate amendment, config, 175-stream inventory, generator, inference code, tests, and integrity checker were SHA-256 frozen in `DESIGN_VALIDATION_FREEZE.json` (`024725f3358638ad30dc8abcb51fd68aaf3096ed7b5a4df0df3464844d79034b`). The candidate procedure and all acceptance rules are in `STAGE5_STATISTICAL_DESIGN_AMENDMENT_CANDIDATE_V2.md`.

The unit is an independent root’s **paired** adaptive-minus-fixed LER difference. The estimand is the equal-weight mean of four nonzero-condition root means. The null boundary is −0.0002. p=0 is assessed separately against +0.0002. Per-condition SD inputs are the larger historical development SDs, estimated from only seven roots per condition, and are therefore provisional.

## Methods tested

The rejected Welch–Satterthwaite test was retained as a comparator. The candidate method uses the same equal-weight root mean and stratified variance estimate, but replaces its t critical value with a conservative allocation-specific cutoff calibrated as the worst one-sided studentized cutoff over a prespecified distribution envelope. The envelope covers unequal condition SDs, 1.5×/2× variability, t tails, right skew, 65% point mass/ties, and zero-symmetric-offset means. Calibration and validation used distinct seeds. Candidate one-sided cutoffs were 1.8341, 1.8252, and 1.8346 for 578, 640, and 666 roots per stratum. Central interval cutoffs were separately calibrated and asymmetric.

The candidate is **not distribution-free**. Calibration and validation support only the finite simulated envelope; a materially different root-effect distribution can invalidate coverage. A bounded Hoeffding interval for differences in [−1,1] is distribution-free but has a one-sided radius of roughly 0.048, 0.047, and 0.047 at the three allocations, respectively, so it cannot resolve the project’s 0.0002 margin.

## Error-rate and coverage validation

Each of 11 primary null scenarios at each allocation used 100,000 independent calibration and 100,000 independent validation simulations: 33 validation cells, 3.3 million null datasets, plus the separate calibration simulations. The validation criteria had been fixed in advance: type-I 95% Wilson upper endpoint ≤0.052; one-sided upper-bound coverage lower endpoint ≥0.94; central 95% coverage lower endpoint ≥0.94.

| Roots per stratum | Candidate maximum type-I | Largest 95% Wilson upper endpoint | Minimum one-sided bound coverage lower endpoint | Minimum central 95% coverage lower endpoint | Welch maximum type-I |
|---:|---:|---:|---:|---:|---:|
| 578 | 4.930% | 5.066% | 94.934% | 95.983% | 6.723% |
| 640 | 4.920% | 5.056% | 94.944% | 95.909% | 6.774% |
| 666 | 4.801% | 4.935% | 95.065% | 95.991% | 6.673% |

All candidate error-rate/coverage criteria passed for the finite prespecified envelope. The rejected Welch method remained anti-conservative under skew: its worst observed rate was about 6.7% even at 666 roots. The separate p=0 simulations also passed the same type-I and one-sided coverage rules; its maximum rejection rate was 4.925%, with a Wilson upper endpoint of 5.061%. The simulated no-harm pass probability at true p=0 effects 0 and +0.0001 was 100% in the tested p=0 scenarios; this is conditional on the assumed p=0 SD and distributions.

## Power and allocation decision

Power used independent 100,000-replicate streams per cell. The predeclared planning alternative was −0.0003 (0.0001 beyond the practical boundary); the target was a Wilson lower power bound ≥80% in every 1.5× normal, t5, right-skew, zero-inflated, and tied scenario. It failed at every allocation.

| Roots/stratum | Total unique shots | Power at −0.0003, 1.5× scenarios (range) | Lowest 95% Wilson lower bound | Power at −0.0003, 2× scenarios (range) |
|---:|---:|---:|---:|---:|
| 578 | 13,005,000 | 73.25–74.75% | 72.97% | 51.22–53.21% |
| 640 | 14,400,000 | 77.20–79.32% | 76.94% | 55.57–57.48% |
| 666 | 14,985,000 | 78.12–80.49% | 77.86% | 56.68–58.26% |

At 666 roots, the individual 1.5× powers at −0.0003 were 79.96% normal, 80.01% t5, 78.12% lognormal, 80.49% zero-inflated normal, and 79.20% tied/asymmetric; their lower Wilson bounds were 79.71%, 79.76%, 77.86%, 80.24%, and 78.95%. The smallest required lower bound is below 80%. At true −0.0004, 666-root powers were ≥96.7% across tested scenarios, but that is twice the practical margin and must not be substituted after seeing these results.

Thus no allocation from 13.005M to 14.985M shots meets the frozen power criterion. The inference procedure passed its error-rate/coverage gate, but the proposed allocation range did not pass the full design gate.

Because the primary inferential procedure passed its finite-envelope size/coverage checks, a separate review-only 666-root candidate package was prepared at `outputs/stage5_candidate_v3_n666/`: root-count-parameterized runner, independent saved-array auditor, 6,660-stream seed inventory, and source freeze. Its deterministic no-shot preflight passed. This does not reverse the NO-GO; the package is not recommended for sampling because the allocation fails the predeclared power gate and secondary Holm inference remains unvalidated.

## Independent checks and execution

The Monte Carlo completed 33 primary-null validation cells, 54 primary power cells, 12 p=0 null cells, and 24 p=0 pass-probability cells, each at 100,000 replicates. Total runtime was **789.64 s**. `independent_audit_repair_v1.py` independently recomputed all stored Wilson intervals and critical-envelope maxima, verified source and historical freeze hashes, checked six generator families using separately written distribution-generation code (250,000 values per condition/family), and passed the no-sampling checks. Five deterministic method tests passed. The initial auditor had a Student-t suffix parser bug and then a vectorized square-root bug; both failures and the corrected, separately versioned auditor are documented in `INDEPENDENT_AUDIT_REPAIR_NOTE.md`. The original frozen auditor was not edited.

The design simulation used bounded batches of 256×4×n float64 root effects. A separate maximum-batch resource probe measured **115,081,216-byte (109.75 MiB) peak working set** for the largest batch and generator temporaries; the full 790-second Monte Carlo process itself did not persist a high-water memory counter. The full Stim/PyMatching disposable benchmark was separately measured at 85,737,472-byte peak RSS, 6.478 s for 225,000 unique shots, and verified resumable after a 7-root pause. Linear engineering projections for the candidate totals are 6.24–7.19 min, about 27.7–32.0 MB compressed archives, and about 549–633 MB uncompressed evidence. These projections are not measured Stage 5 performance.

## Conclusion

**NO-GO for Stage 5 sampling.** The candidate calibrated inference method passed its simulated size and coverage criteria within the envelope, but even the largest requested allocation failed the predeclared power target for skewed and tied 1.5× scenarios; 2× variability yielded only about 57% power. Do not increase the budget or switch to a larger target effect to manufacture a pass. A new study needs a separately justified target effect, broader root-level variance evidence, and a new approved budget before its runner is frozen for sampling.
