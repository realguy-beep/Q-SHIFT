# Evidence matrix

“Verified” means a saved audit or independent prediction rescoring supports the claim; it does not imply external validity. “Exploratory” identifies development/feasibility evidence. “Reported” means the result is in a run report without equivalent raw-array reconstruction.

| Claim | Evidence | Status | Supports | Does not support |
|---|---|---|---|---|
| Legacy classifier generalized to new syndromes | 61 unique detector vectors among 150,000 CSV rows; no shot IDs | Weak design | Dataset duplication audit | Row-random split as independent generalization |
| Detector data identify trained noise conditions | Phase 1 reports 94.4% trained-regime window accuracy | Exploratory | Detector statistics carried information in the simulated regimes | Better LER, unseen-mixture recognition, universal identifiability |
| Lookup adaptation improves over matching | Phase 1 guarded controller made zero switches/tied fixed; rate-only version was worse | Negative, exploratory | Validation guard prevented unsupported switching | That adaptation cannot work elsewhere |
| Specialist PyMatching improves over fixed | Repetition-code study: validation chose fixed in all 60 choices; several specialists exactly matched corrections | Negative in tested conditions | No utility headroom in that model bank | Universal equivalence of matching weights |
| Regime calibration helps among nine DEM models | Phase 2A: 4,192 errors for both global and regime-selected on 600k; p=1 | Exploratory with raw-array audit | Same candidate selected for all regimes | Test-label oracle as a deployable result |
| Pauli composition requires regime-specific decoder | Phase 2B: 1.2m shots; regime-informed = global, 5,532 errors each | Negative, multi-root paired | Basis-specific fixed selections (X-memory #0, Z-memory #2) | Pauli-composition switching benefit |
| DEM approximation materially changes LER | Phase 2C RF surrogate: 2,579 vs matching 628 /120k; only 4 roots/cell | Inconclusive causally | The particular forest disagreed with and underperformed matching | That approximation did or did not cause the gap |
| X-bias specialist gain is reproducible | Phase 3A pilot was not independent across corrected versions; Phase 3B had 43,673 fixed vs 43,675 specialist /600k, p=.9374 | Independent replication negative | No replicated gain in that model and condition | No specialist can help under any model |
| Calibration improves nominal matching in measurement-heavy noise | Phase 4A 940 vs 1,118 /600k, p=5.60e-23; 19/20 root wins. Phase 4B 1,008 vs 1,165 /600k, p=3.73e-17; 20/20 wins | Replicated static effect, Phase 4B deviation | Conditional calibrated-vs-nominal result | Adaptive gain, universal improvement, no-deviation preregistration |
| Calibration beats a stronger pooled baseline | Phase 4C: 1.8m held-out, equal-regime difference +1.556e-5, 95% CI [-4.889e-5,+7.667e-5], p=.66658 | Test arrays independently rescored; calibration evidence incomplete | No evidence of a gain over pooled fixed | Full reconstruction of fitting or unqualified confirmatory status |
| Prototype adaptive system beats fixed | Audited 50-root prototype /307,200 paired: pooled 1,989, adaptive 1,989, identity 19,726 | Verified development demo, no gain | Working simulator/controller/fallback pipeline | Adaptive superiority or “no decoding” as physical QEC absence |
| Current bank contains usable dynamic headroom | Phase 5D/5E corrected development: sparse differences, inconsistent rankings, adaptive often ties pooled; hindsight policy lower | Exploratory | Potential estimation and switching limitations | Confirmatory improvement; hindsight oracle as deployable |

## Integrity, separation, and bias notes

- Phase 2A explicitly excludes earlier prototype samples from its untouched test. Phase 2A–2C and Phase 4 records document separate calibration/validation/test roles; Phase 4C Stage 2 calibration arrays are missing, limiting reconstruction.
- Phase 3A corrected v2–v4 reuse the same three raw bundles. They are versions, not replications. Phase 3B says its test roots were fresh.
- Phase 4B test predictions were independently re-decoded; it generated a fresh template bank where protocol text specified reuse. Phase 4C Stage 2 predictions were independently re-decoded, but there were prospective RNG amendments and no stored calibration samples.
- Phase 4A's three hash mismatches were explained as documentation-only by a separate integrity reaudit. Phase 2C initially omitted six derived forest seeds; a supplemental audit found no collisions.
- Phase 5 initial v1 metric labels were defective; use corrected versioned outputs only. Do not cite superseded v1 totals.
- Shot-level McNemar tests compare paired shots, but generalization inference should use independent roots/schedules. Phase 2C has only four roots/cell. Retrospective test-best rankings and per-shot oracle policies are descriptive upper bounds.
- Phase 4A/B compare with nominal fixed. Phase 4C compares with pooled development-selected fixed. These differ in baseline strength and estimand, so do not pool phase effects.

## Numbers suitable for qualified summaries

1. **Static measurement-heavy calibration:** Phase 4A: 940/600,000 vs 1,118/600,000 nominal. Phase 4B: 1,008/600,000 vs 1,165/600,000 nominal, with an explicit template-protocol deviation.
2. **Strong pooled comparator:** Phase 4C Stage 2 has no significant improvement: calibrated-minus-pooled +0.00156 percentage points; root-stratified 95% CI [-0.00489,+0.00767] percentage points; p=.66658.
3. **Adaptive prototype:** audited development run: 1,989/307,200 adaptive and pooled errors. This is not an independent test of a frozen adaptive policy.

Do not pool across phases: the circuits, conditions, baselines and selection rules differ.
